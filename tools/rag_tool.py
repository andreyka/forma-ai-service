import os
import asyncio
from bs4 import BeautifulSoup
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict
from playwright.async_api import async_playwright

class RAGTool:
    def __init__(self, persist_directory: str = "rag_db"):
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

    async def ingest_docs(self):
        """
        Scrapes the configured URLs using Playwright and populates the vector DB.
        """
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
                try:
                    print(f"Scraping {url}...")
                    page = await context.new_page()
                    # Use domcontentloaded to be faster and avoid timeouts on heavy pages
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Get content
                    content_html = await page.content()
                    soup = BeautifulSoup(content_html, 'html.parser')
                    
                    # Extract text from main content
                    content = soup.find('div', {'role': 'main'}) or soup.find('article') or soup.body
                    
                    if not content:
                        print(f"Could not find main content for {url}")
                        await page.close()
                        continue
                    
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

                    text = content.get_text(separator="\n")
                    
                    # Simple chunking
                    chunks = self._chunk_text(text)
                    
                    for i, chunk in enumerate(chunks):
                        all_chunks.append(chunk)
                        all_ids.append(f"doc_{doc_id_counter}_{i}")
                        all_metadatas.append({"source": url, "chunk_id": i})
                    
                    doc_id_counter += 1
                    await page.close()
                    
                except Exception as e:
                    print(f"Failed to scrape {url}: {e}")
            
            await browser.close()

        if all_chunks:
            print(f"Adding {len(all_chunks)} chunks to DB...")
            # Add in batches to avoid hitting limits
            batch_size = 100
            for i in range(0, len(all_chunks), batch_size):
                end = min(i + batch_size, len(all_chunks))
                self.collection.add(
                    documents=all_chunks[i:end],
                    ids=all_ids[i:end],
                    metadatas=all_metadatas[i:end]
                )
            print("Ingestion complete.")
        else:
            print("No content to ingest.")

    def _chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
        """
        Splits text into chunks with overlap, respecting code blocks and paragraphs.
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
        """
        Queries the vector DB for relevant context.
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
