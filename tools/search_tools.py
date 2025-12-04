"""Search tools for web and image search.

This module provides the SearchTools class which interfaces with Google Custom Search
and DuckDuckGo to perform web and image searches, and fetch web page content.
"""

import os
import requests
from duckduckgo_search import DDGS
from typing import List, Dict
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

class SearchTools:
    """Provides web search, image search, and page fetching capabilities."""
    def __init__(self):
        """Initialize SearchTools with API keys."""
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        self.ddgs = None
        
        if not self.google_api_key or not self.google_cse_id:
            print("Google Search keys not found. Falling back to DuckDuckGo.")
            self.ddgs = DDGS()
        else:
            print("Google Custom Search enabled.")

    def web_search(self, query: str, max_results: int = 5) -> str:
        """General web search using Google Custom Search or DuckDuckGo.

        Args:
            query (str): The search query.
            max_results (int): Maximum number of results to return.

        Returns:
            str: Formatted search results.
        """
        if self.google_api_key and self.google_cse_id:
            return self._google_search(query, max_results)
        else:
            return self._ddg_search(query, max_results)

    def image_search(self, query: str, max_results: int = 3) -> List[str]:
        """Image search using Google Custom Search or DuckDuckGo.

        Args:
            query (str): The search query.
            max_results (int): Maximum number of results to return.

        Returns:
            List[str]: A list of image URLs.
        """
        if self.google_api_key and self.google_cse_id:
            return self._google_image_search(query, max_results)
        else:
            return self._ddg_image_search(query, max_results)

    def _google_search(self, query: str, max_results: int) -> str:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cse_id,
                "q": query,
                "num": max_results
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("items", [])
            if not results:
                return "No results found."
            
            formatted = []
            for res in results:
                formatted.append(f"Title: {res.get('title')}\nLink: {res.get('link')}\nSnippet: {res.get('snippet')}\n")
            return "\n".join(formatted)
        except Exception as e:
            print(f"Google Search failed: {e}. Falling back to DuckDuckGo.")
            if not self.ddgs:
                self.ddgs = DDGS()
            return self._ddg_search(query, max_results)

    def _google_image_search(self, query: str, max_results: int) -> List[str]:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cse_id,
                "q": query,
                "num": max_results,
                "searchType": "image"
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("items", [])
            if not results:
                return []
            
            return [res.get("link") for res in results if res.get("link")]
        except Exception as e:
            print(f"Google Image Search failed: {e}. Falling back to DuckDuckGo.")
            if not self.ddgs:
                self.ddgs = DDGS()
            return self._ddg_image_search(query, max_results)

    def _ddg_search(self, query: str, max_results: int) -> str:
        try:
            if not self.ddgs:
                 self.ddgs = DDGS()
            results = self.ddgs.text(query, max_results=max_results)
            if not results:
                return "No results found."
            
            formatted = []
            for res in results:
                formatted.append(f"Title: {res.get('title')}\nLink: {res.get('href')}\nSnippet: {res.get('body')}\n")
            return "\n".join(formatted)
        except Exception as e:
            return f"Search failed: {e}"

    def _ddg_image_search(self, query: str, max_results: int) -> List[str]:
        try:
            if not self.ddgs:
                 self.ddgs = DDGS()
            results = self.ddgs.images(query, max_results=max_results)
            if not results:
                return []
            
            return [res.get("image") for res in results if res.get("image")]
        except Exception as e:
            print(f"DuckDuckGo Image Search failed: {e}")
            return []

    async def fetch_page(self, url: str) -> str:
        """Fetches the content of a URL and returns the text using Playwright.

        Args:
            url (str): The URL to fetch.

        Returns:
            str: The text content of the page.
        """
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = await context.new_page()
                
                # Use domcontentloaded for speed, but wait a bit for dynamic content if needed
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                except Exception as e:
                    print(f"Page load timeout/error: {e}")
                    # Continue anyway, we might have partial content
                
                content = await page.content()
                await browser.close()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
                
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Limit length to avoid context overflow
            return text[:20000] 
            
        except Exception as e:
            return f"Failed to fetch page {url}: {e}"
