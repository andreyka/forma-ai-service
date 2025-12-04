"""RAG (Retrieval-Augmented Generation) tool for documentation.

This module provides the RAGTool class to ingest documentation from URLs,
store it in a vector database, and query it for relevant context.
"""

import os
import asyncio
from bs4 import BeautifulSoup
import chromadb
from chromadb.utils import embedding_functions
from playwright.async_api import async_playwright, BrowserContext

class RAGTool:
    """Manages documentation ingestion and retrieval."""
    def __init__(self, persist_directory: str = "rag_db"):
        """Initialize RAGTool.

        Args:
            persist_directory (str): Directory to persist the vector database.
        """
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Use a more powerful model for embeddings
        self.model_name = "all-mpnet-base-v2"
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=self.model_name)
        
        self.collection = self.client.get_or_create_collection(
            name="build123d_docs",
            embedding_function=self.embedding_fn
        )
        
        self.urls = [
            "https://build123d.readthedocs.io/en/latest/introduction.html",
            "https://build123d.readthedocs.io/en/latest/key_concepts.html",
            "https://build123d.readthedocs.io/en/latest/key_concepts_builder.html",
            "https://build123d.readthedocs.io/en/latest/key_concepts_algebra.html",
            "https://build123d.readthedocs.io/en/latest/location_arithmetic.html",
            "https://build123d.readthedocs.io/en/latest/moving_objects.html",
            "https://build123d.readthedocs.io/en/latest/introductory_examples.html",
            "https://build123d.readthedocs.io/en/latest/examples_1.html",
            "https://build123d.readthedocs.io/en/latest/tutorials.html",
            "https://build123d.readthedocs.io/en/latest/tutorial_design.html",
            "https://build123d.readthedocs.io/en/latest/tutorial_selectors.html",
            "https://build123d.readthedocs.io/en/latest/tutorial_lego.html",
            "https://build123d.readthedocs.io/en/latest/tutorial_joints.html",
            "https://build123d.readthedocs.io/en/latest/tutorial_surface_modeling.html",
            "https://build123d.readthedocs.io/en/latest/objects.html",
            "https://build123d.readthedocs.io/en/latest/operations.html",
            "https://build123d.readthedocs.io/en/latest/topology_selection.html",
            "https://build123d.readthedocs.io/en/latest/builders.html",
            "https://build123d.readthedocs.io/en/latest/build_line.html",
            "https://build123d.readthedocs.io/en/latest/build_sketch.html",
            "https://build123d.readthedocs.io/en/latest/build_part.html",
            "https://build123d.readthedocs.io/en/latest/joints.html",
            "https://build123d.readthedocs.io/en/latest/assemblies.html",
            "https://build123d.readthedocs.io/en/latest/tips.html",
            "https://build123d.readthedocs.io/en/latest/tttt.html",
            "https://build123d.readthedocs.io/en/latest/tech_drawing_tutorial.html",
            "https://build123d.readthedocs.io/en/latest/OpenSCAD.html",
        ]

    async def _process_page_content(self, content_html: str) -> str | None:
        """Parses HTML content and extracts relevant text.

        Args:
            content_html: The raw HTML content of the page.

        Returns:
            The extracted text content, or None if no main content is found.
        """
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # Extract text from main content
        content = soup.find('div', {'role': 'main'}) or soup.find('article') or soup.body
        
        if not content:
            return None
        
        # Remove navigation and other noise if possible
        for nav in content.find_all(['nav', 'aside', 'footer']):
            nav.decompose()

        # Pre-process code blocks to preserve formatting
        for code_block in content.find_all('pre'):
            # Preserve line breaks from br tags
            for br in code_block.find_all('br'):
                br.replace_with('\n')
            
            # Preserve line breaks from block elements
            for block in code_block.find_all(['div', 'p', 'li']):
                block.append('\n')
                
            code_text = code_block.get_text()
            code_block.replace_with(f"\n```python\n{code_text}\n```\n")

        return content.get_text(separator="\n")

    async def _fetch_url_content(self, context: BrowserContext, url: str) -> str | None:
        """Fetches content from a URL using Playwright.

        Args:
            context: The Playwright browser context.
            url: The URL to fetch.

        Returns:
            The extracted text content of the page, or None if fetching failed.
        """
        try:
            print(f"Scraping {url}...")
            page = await context.new_page()
            # Use domcontentloaded to be faster and avoid timeouts on heavy pages
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Get content
            content_html = await page.content()
            await page.close()
            
            return await self._process_page_content(content_html)
            
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            return None

    def _store_chunks(self, chunks: list[str], ids: list[str], metadatas: list[dict]) -> None:
        """Stores document chunks in the vector database.

        Args:
            chunks: List of text chunks.
            ids: List of unique IDs for the chunks.
            metadatas: List of metadata dictionaries for the chunks.
        """
        if not chunks:
            print("No content to ingest.")
            return

        print(f"Adding {len(chunks)} chunks to DB...")
        # Add in batches to avoid hitting limits
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            end = min(i + batch_size, len(chunks))
            self.collection.add(
                documents=chunks[i:end],
                ids=ids[i:end],
                metadatas=metadatas[i:end]
            )
        print("Ingestion complete.")

    async def ingest_docs(self) -> None:
        """Scrapes the configured URLs using Playwright and populates the vector DB."""
        if self.collection.count() > 0:
            print("RAG DB already populated. Skipping ingestion.")
            return

        print("Ingesting documentation with Playwright...")
        all_chunks = []
        all_ids = []
        all_metadatas = []
        
        doc_id_counter = 0
        
        print("Starting Playwright...")
        async with async_playwright() as p:
            print("Launching browser...")
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            print("Browser launched. Creating context...")
            context = await browser.new_context()
            
            for url in self.urls:
                text = await self._fetch_url_content(context, url)
                
                if not text:
                    print(f"Could not find main content for {url}")
                    continue
                
                # Simple chunking
                chunks = self._chunk_text(text)
                
                for i, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    all_ids.append(f"doc_{doc_id_counter}_{i}")
                    all_metadatas.append({"source": url, "chunk_id": i})
                
                doc_id_counter += 1
            
            await browser.close()

        self._store_chunks(all_chunks, all_ids, all_metadatas)

    def _chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
        """Splits text into chunks with overlap, respecting code blocks and paragraphs.

        Args:
            text: The text to chunk.
            chunk_size: The maximum size of each chunk.
            overlap: The number of characters to overlap between chunks.

        Returns:
            A list of text chunks.
        """
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            
            if end >= text_len:
                chunks.append(text[start:])
                break
            
            # Try to find a good split point backwards from 'end'
            # We want to split at a natural boundary
            
            split_point = -1
            search_limit = max(start, end - overlap)
            
            # 1. Split after a code block (```\n)
            code_block_end = text.rfind("```\n", search_limit, end)
            if code_block_end != -1:
                split_point = code_block_end + 4
            
            # 2. Split at double newline
            if split_point == -1:
                double_newline = text.rfind("\n\n", search_limit, end)
                if double_newline != -1:
                    split_point = double_newline + 2
            
            # 3. Split at single newline
            if split_point == -1:
                newline = text.rfind("\n", search_limit, end)
                if newline != -1:
                    split_point = newline + 1
            
            # 4. Fallback: hard split
            if split_point == -1:
                split_point = end
            
            chunks.append(text[start:split_point])
            start = split_point
            
        return chunks

    def query(self, query_text: str, n_results: int = 2) -> str:
        """Queries the vector DB for relevant context.

        Args:
            query_text: The query string.
            n_results: The number of results to return.

        Returns:
            A string containing the concatenated context from relevant documents.
        """
        try:
            print(f"RAG Tool: Querying for '{query_text}'")
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            if not results['documents'] or not results['documents'][0]:
                print("RAG Tool: No results found.")
                return "No relevant documentation found."
            
            print(f"RAG Tool: Found {len(results['documents'][0])} results.")
            for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
                print(f"RAG Result {i+1}: Source={meta.get('source', 'unknown')}, ChunkID={meta.get('chunk_id', 'unknown')}")
                print(f"RAG Content Snippet: {doc[:200]}...")

            context = "\n\n".join(results['documents'][0])
            return context
        except Exception as e:
            print(f"RAG Tool: Query failed with error: {e}")
            return f"RAG Query failed: {e}"
