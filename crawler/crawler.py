# crawler/crawler.py

import requests
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup
from huggingface_hub import snapshot_download
from langchain_huggingface import HuggingFaceEmbeddings
import re

# Import our modularized components and config
from config import config
from crawler.logger import setup_logger
from crawler.utils import clean_text
from crawler.search import perform_search
from crawler import extractor, store
from crawler.heuristics import ContentHeuristics

class AdaptiveWebCrawler:
    def __init__(self):
        # Initially, no seed urls are set.
        self.seed_urls: List[str] = []
        self.visited_urls = set()
        self.content_store = []
        self.pattern_memory = {}
        self.logger = setup_logger()
        self.heuristics = ContentHeuristics()

        # Setup model caching
        model_path = config.model.MODEL_CACHE_DIR / config.model.MODEL_NAME.split('/')[-1]
        if not model_path.exists():
            self.logger.info(f"Downloading model {config.model.MODEL_NAME} for first time use...")
            snapshot_download(repo_id=config.model.MODEL_NAME, local_dir=str(model_path))

        self.embeddings = HuggingFaceEmbeddings(
            model_name=str(model_path),
            cache_folder=str(config.model.MODEL_CACHE_DIR)
        )
        
        self.vector_store = None
        
    def crawl(self, prompt: str, urls: Optional[List[str]] = None, strict: bool = False):
        """
        Starts the crawl process with enhanced heuristics.
        """
        # Extract keywords from prompt for heuristic matching
        prompt_keywords = self._extract_keywords(prompt)
        self.logger.info(f"Extracted keywords from prompt: {prompt_keywords}")
        
        # Load saved state (visited URLs, content hashes, and vector store) if available
        self.visited_urls, self.heuristics.content_hashes, self.vector_store = store.load_state(self.logger, self.embeddings)
        
        # Determine the seed URLs based on the provided input:
        if strict:
            # Case 3: Use only provided URLs (or if none, fall back to search results)
            self.seed_urls = urls if urls is not None else perform_search(prompt, config.crawler.TOP_N_RESULTS)
        else:
            if urls is None:
                # Case 1: Only prompt provided.
                self.seed_urls = perform_search(prompt, config.crawler.TOP_N_RESULTS)
            else:
                # Case 2: Both prompt and urls provided; combine search results with user URLs.
                search_results = perform_search(prompt, config.crawler.TOP_N_RESULTS)
                # Use a set to deduplicate.
                self.seed_urls = list(set(urls) | set(search_results))
                
        self.logger.info(f"Using {len(self.seed_urls)} seed URLs for crawling.")
        
        docs_since_last_save = 0
        url_scores = {}  # Store URL scores for prioritization
        
        # First pass: evaluate all seed URLs
        for url in self.seed_urls:
            if url in self.visited_urls:
                continue
                
            try:
                self.logger.info(f"Evaluating: {url}")
                response = requests.get(url, timeout=10)
                
                # Use response.content to let BeautifulSoup detect proper encoding
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Calculate page score using heuristics
                score, metadata = self.heuristics.calculate_page_score(soup, url, prompt_keywords)
                url_scores[url] = (score, soup, metadata)
                
                self.logger.info(f"URL {url} received score: {score:.2f}")
                
            except Exception as e:
                self.logger.error(f"Error evaluating {url}: {str(e)}")
                self.visited_urls.add(url)
        
        # Sort URLs by score for prioritized crawling
        prioritized_urls = sorted(url_scores.items(), key=lambda x: x[1][0], reverse=True)
        
        # Second pass: crawl URLs in priority order
        for url, (score, soup, metadata) in prioritized_urls:
            try:
                self.logger.info(f"Crawling prioritized URL: {url} (score: {score:.2f})")
                
                # Extract content using our extractor
                content = extractor.extract_content(soup, url, self.pattern_memory, clean_text)
                
                # Check if content should be processed
                if content['content'] and self.heuristics.should_process_content(content['content'], url):
                    # Add metadata from heuristics
                    content.update(metadata)
                    self.content_store.append(content)
                    docs_since_last_save += 1
                else:
                    self.logger.info(f"Content from {url} was filtered out (too short or duplicate)")
                
                self.visited_urls.add(url)
                
                # Save progress periodically
                if docs_since_last_save >= config.crawler.save_frequency:
                    self.vector_store = store.update_vector_store(
                        self.content_store,
                        self.vector_store,
                        self.embeddings
                    )
                    
                    store.save_state(self.visited_urls, self.heuristics.content_hashes, self.logger)
                    docs_since_last_save = 0
                    self.logger.info("Saved current progress.")
                    
            except Exception as e:
                self.logger.error(f"Error processing {url}: {str(e)}")
                self.visited_urls.add(url)
            
            # Status update after each URL
            self.logger.info(f"Crawling Status:")
            self.logger.info(f"URLs:")
            self.logger.info(f" Visited this run: {len([u for u in self.visited_urls if u in self.seed_urls])}")
            self.logger.info(f" Historical total: {len(self.visited_urls)}")
            self.logger.info(f" Seed URLs remaining: {len([u for u in self.seed_urls if u not in self.visited_urls])}")
            self.logger.info(f"Content collected: {len(self.content_store)} pages")
        
        # Final save if there are unsaved documents
        if docs_since_last_save > 0:
            self.vector_store = store.update_vector_store(
                self.content_store,
                self.vector_store,
                self.embeddings
            )
            
            store.save_state(self.visited_urls, self.heuristics.content_hashes, self.logger)
        
        # Update final logging messages
        urls_this_run = len([u for u in self.visited_urls if u in self.seed_urls])
        self.logger.info(f"Crawling complete.")
        self.logger.info(f"URLs processed:")
        self.logger.info(f" Visited this run: {urls_this_run}")
        self.logger.info(f" Historical total: {len(self.visited_urls)}")
        self.logger.info(f"Collected content from {len(self.content_store)} pages.")
    
    def create_vector_store(self):
        """Create the vector store from crawled content."""
        self.vector_store = store.create_vector_store(self.content_store, self.embeddings, self.logger)
    
    def query(self, question: str, k: int = 3, strict: bool = False) -> List[Dict]:
        """
        Query the vector store for relevant content using hybrid scoring.
        
        Args:
            question: The query string
            k: Number of results to return
            strict: Whether to restrict results to seed URLs only
            
        Returns:
            List of relevant documents with metadata and hybrid scores
        """
        if not self.vector_store:
            if not self.content_store:
                # Return empty results if no content available
                return []
            else:
                raise ValueError("Vector store not created. Run create_vector_store() first.")
        
        # Get more results than needed since we might filter some out in strict mode
        buffer_k = k * 3 if strict else k
        
        # Get FAISS vector similarity results
        faiss_results = self.vector_store.similarity_search_with_relevance_scores(question, k=buffer_k)
        
        # Get TF-IDF cosine similarity results
        tfidf_results = store.tfidf_similarity_search(self.content_store, question, k=buffer_k)
        
        # Combine results with weighted scoring (70% FAISS, 30% TF-IDF)
        combined_results = self._combine_search_results(faiss_results, tfidf_results, faiss_weight=0.7)
        
        if strict and self.seed_urls:
            # Filter results to only include those from seed URLs
            filtered_results = []
            for doc, score in combined_results:
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
            results = combined_results[:k]
        
        return [{
            'content': doc.page_content,
            'source': doc.metadata['source'],
            'domain': doc.metadata['domain'],
            'score': float(score),
            'publish_date': doc.metadata.get('publish_date'),
            'content_length': doc.metadata.get('content_length', 0)
        } for doc, score in results]
    
    def _extract_keywords(self, prompt: str) -> List[str]:
        """Extract keywords from the prompt for heuristic matching."""
        # Remove stop words and extract meaningful keywords
        stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                     'be', 'been', 'being', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 
                     'about', 'against', 'between', 'into', 'through', 'during', 'before', 
                     'after', 'above', 'below', 'from', 'up', 'down', 'of', 'off', 'over', 
                     'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 
                     'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 
                     'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 
                     'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 
                     'don', 'should', 'now'}
        
        # Tokenize and filter out stop words
        words = re.findall(r'\b\w+\b', prompt.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Add any phrases (2-3 consecutive words) that might be important
        phrases = []
        for i in range(len(words) - 1):
            phrase = words[i] + ' ' + words[i+1]
            if any(word not in stop_words for word in phrase.split()):
                phrases.append(phrase)
        
        for i in range(len(words) - 2):
            phrase = words[i] + ' ' + words[i+1] + ' ' + words[i+2]
            if any(word not in stop_words for word in phrase.split()):
                phrases.append(phrase)
        
        # Combine keywords and important phrases
        all_keywords = keywords + phrases
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = [kw for kw in all_keywords if not (kw in seen or seen.add(kw))]
        
        # Limit to most important keywords (top 10)
        return unique_keywords[:10]
    
    def _combine_search_results(self, faiss_results, tfidf_results, faiss_weight=0.7):
        """
        Combine results from FAISS and TF-IDF with weighted scoring.
        
        Args:
            faiss_results: List of (Document, score) tuples from FAISS
            tfidf_results: List of (Document, score) tuples from TF-IDF
            faiss_weight: Weight to give FAISS results (0-1)
            
        Returns:
            List of (Document, combined_score) tuples
        """
        return store.combine_search_results(faiss_results, tfidf_results, faiss_weight)