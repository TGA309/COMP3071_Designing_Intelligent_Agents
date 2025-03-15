# crawler/crawler.py

import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from huggingface_hub import snapshot_download
from langchain_huggingface import HuggingFaceEmbeddings

# Import our modularized components and config
from crawler.config import save_frequency, MODEL_NAME, MODEL_CACHE_DIR, TOP_N_RESULTS
from crawler.logger import setup_logger
from crawler.utils import clean_text
from crawler.search import perform_search
from crawler import extractor, store


class AdaptiveWebCrawler:
    def __init__(self):
        # Initially, no seed urls are set.
        self.seed_urls: List[str] = []
        self.visited_urls = set()
        self.content_store = []
        self.pattern_memory = {}
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.logger = setup_logger()
        
        # Setup model caching
        model_path = MODEL_CACHE_DIR / MODEL_NAME.split('/')[-1]
        if not model_path.exists():
            self.logger.info(f"Downloading model {MODEL_NAME} for first time use...")
            snapshot_download(repo_id=MODEL_NAME, local_dir=str(model_path))
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=str(model_path),
            cache_folder=str(MODEL_CACHE_DIR)
        )
        
        self.vector_store = None

    def crawl(self, prompt: str, urls: Optional[List[str]] = None, strict: bool = False):
        """
        Starts the crawl process based on the following workflow:
        
        Case 1: If only a prompt is provided (no urls, strict is False):
            - Perform search queries (across multiple search engines) using the prompt.
            - Rank and select the top N results (N defined in TOP_N_RESULTS).
        
        Case 2: If a prompt and urls are provided and strict is False:
            - Perform search as in Case 1.
            - Combine the search results with the user-provided urls (deduplicated).
        
        Case 3: If a prompt, urls are provided and strict is True:
            - Only use the provided urls.
        
        After determining the seed URLs, each URL is scraped for content.
        State (visited urls) and the vector store are updated for online learning.
        """
        # Load saved state (visited URLs and vector store) if available.
        self.visited_urls, self.vector_store = store.load_state(self.logger, self.embeddings)
        
        # Determine the seed URLs based on the provided input:
        if strict:
            # Case 3: Use only provided URLs (or if none, fall back to search results)
            self.seed_urls = urls if urls is not None else perform_search(prompt, TOP_N_RESULTS)
        else:
            if urls is None:
                # Case 1: Only prompt provided.
                self.seed_urls = perform_search(prompt, TOP_N_RESULTS)
            else:
                # Case 2: Both prompt and urls provided; combine search results with user URLs.
                search_results = perform_search(prompt, TOP_N_RESULTS)
                # Use a set to deduplicate.
                self.seed_urls = list(set(urls) | set(search_results))
        
        self.logger.info(f"Using {len(self.seed_urls)} seed URLs for crawling.")
        
        docs_since_last_save = 0
        
        # Iterate over the seed URLs (no need to follow additional links)
        for url in self.seed_urls:
            if url in self.visited_urls:
                continue

            try:
                self.logger.info(f"Attempting to crawl: {url}")
                response = requests.get(url, timeout=10)
                self.logger.info(f"Retrieved content from {url} (status: {response.status_code})")
                
                # Use response.content to let BeautifulSoup detect proper encoding.
                soup = BeautifulSoup(response.content, 'html.parser')
                # Extract content using our extractor.
                content = extractor.extract_content(soup, url, self.pattern_memory, clean_text)
                
                self.logger.info(f"Extracted {len(content['content'])} characters of content from {url}")
                # Since URLs provided are assumed to be technical, no extra filtering is done.
                if content['content']:
                    self.content_store.append(content)
                    docs_since_last_save += 1
                else:
                    self.logger.info("No content was extracted.")
                
                self.visited_urls.add(url)
                
                # Save progress periodically.
                if docs_since_last_save >= save_frequency:
                    self.vector_store = store.update_vector_store(
                        self.content_store,
                        self.vector_store,
                        self.embeddings
                    )
                    store.save_state(self.visited_urls, self.logger)
                    docs_since_last_save = 0
                    self.logger.info("Saved current progress.")
            except Exception as e:
                self.logger.error(f"Error crawling {url}: {str(e)}")
                continue
            
            # Status update after each URL.
            self.logger.info(f"Crawling Status:")
            self.logger.info(f"URLs:")
            self.logger.info(f"  - Visited this run: {len([u for u in self.visited_urls if u in self.seed_urls])}")
            self.logger.info(f"  - Historical total: {len(self.visited_urls)}")
            self.logger.info(f"  - Seed URLs remaining: {len([u for u in self.seed_urls if u not in self.visited_urls])}")
            self.logger.info(f"Technical content collected: {len(self.content_store)} pages")
        
        # Final save if there are unsaved documents.
        if docs_since_last_save > 0:
            self.vector_store = store.update_vector_store(
                self.content_store,
                self.vector_store,
                self.embeddings
            )
            store.save_state(self.visited_urls, self.logger)
        
        # Update final logging messages
        urls_this_run = len([u for u in self.visited_urls if u in self.seed_urls])
        self.logger.info(f"Crawling complete.")
        self.logger.info(f"URLs processed:")
        self.logger.info(f"  - Visited this run: {urls_this_run}")
        self.logger.info(f"  - Historical total: {len(self.visited_urls)}")
        self.logger.info(f"Collected content from {len(self.content_store)} pages.")

    def create_vector_store(self):
        """Create the FAISS vector store from crawled content."""
        self.vector_store = store.create_vector_store(self.content_store, self.embeddings, self.logger)

    def query(self, question: str, k: int = 3, strict: bool = False) -> List[Dict]:
        """
        Query the vector store for relevant content.
        In strict mode, only returns results from seed URLs.
        
        Args:
            question (str): The query string
            k (int): Number of results to return
            strict (bool): Whether to restrict results to seed URLs only
            
        Returns:
            List[Dict]: List of relevant documents with metadata
        """
        if not self.vector_store:
            if not self.content_store:
                # Return empty results if no content available
                return []
            else:
                raise ValueError("Vector store not created. Run create_vector_store() first.")
        
        # Get more results than needed since we might filter some out in strict mode
        buffer_k = k * 3 if strict else k
        results = self.vector_store.similarity_search_with_relevance_scores(question, k=buffer_k)
        
        if strict and self.seed_urls:
            # Filter results to only include those from seed URLs
            filtered_results = []
            
            for doc, score in results:
                # Check if the document's source URL is in seed_urls
                if doc.metadata['source'] in self.seed_urls:
                    filtered_results.append((doc, score))
                
                # Break if we have enough results
                if len(filtered_results) >= k:
                    break
            
            # Use filtered results
            results = filtered_results[:k]
        else:
            # In non-strict mode, just take top k
            results = results[:k]
        
        return [{
            'content': doc.page_content,
            'source': doc.metadata['source'],
            'domain': doc.metadata['domain'],
            'score': score
        } for doc, score in results]