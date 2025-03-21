# crawler/crawler.py
import requests
from typing import List, Dict, Optional, Set, Tuple
from bs4 import BeautifulSoup
from huggingface_hub import snapshot_download
from langchain_huggingface import HuggingFaceEmbeddings
import re
from queue import PriorityQueue
import concurrent.futures

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
        
    def crawl(self, prompt: str, urls: Optional[List[str]] = None, strict: bool = False, num_results: int = 3, num_seed_urls: int = 5, max_depth: int = 5, base_relevance_threshold: float = 0.5):
        """
        Starts the crawl process with enhanced heuristics and depth crawling.
        
        Args:
            prompt: User query
            urls: Optional seed URLs
            strict: Whether to use only provided URLs
            num_seed_urls: Number of seed urls to get back from the search results
            max_depth: Maximum crawl depth
        """
        # Extract keywords from prompt for heuristic matching
        prompt_keywords = self._extract_keywords(prompt)
        self.logger.info(f"Extracted keywords from prompt: {prompt_keywords}")
        
        # Load saved state (visited URLs, content hashes, content_store and vector store) if available
        self.visited_urls, self.heuristics.content_hashes, self.content_store, self.vector_store = store.load_state(self.logger, self.embeddings)
        
        # Determine the seed URLs based on the provided input:
        if strict:
            # Case 3: Use only provided URLs (or if none, fall back to search results)
            self.seed_urls = urls if urls is not None else perform_search(prompt, num_seed_urls)
        else:
            if urls is None:
                # Case 1: Only prompt provided.
                self.seed_urls = perform_search(prompt, num_seed_urls)
            else:
                # Case 2: Both prompt and urls provided; combine search results with user URLs.
                search_results = perform_search(prompt, num_seed_urls)
                # Use a set to deduplicate.
                self.seed_urls = list(set(urls) | set(search_results))
                
        self.logger.info(f"Using {len(self.seed_urls)} seed URLs for crawling.")
        
        # Start with seed URLs (depth 0)
        current_depth = 0
        urls_to_crawl = self.seed_urls.copy()
        all_discovered_urls = set(urls_to_crawl)

        while current_depth <= max_depth and urls_to_crawl:
            self.logger.info(f"Starting crawl at depth {current_depth}")
            
            # Calculate relevance threshold for current depth
            relevance_threshold = max(
                config.crawler.minimum_relevance_threshold,
                base_relevance_threshold - (current_depth * config.crawler.depth_relevance_step)
            )
            self.logger.info(f"Using relevance threshold: {relevance_threshold} for depth {current_depth}")
            
            # Process URLs at current depth
            next_urls, found_relevant_results = self._process_urls_at_depth(
                urls_to_crawl, 
                prompt_keywords,
                prompt,
                relevance_threshold,
                current_depth,
                strict,
                num_results,
                config.crawler.batch_size
            )
            
            # If relevant results were found during batch processing, stop crawling
            if found_relevant_results:
                self.logger.info(f"Found relevant results during batch processing at depth {current_depth}")
                break

            # Update stores with new content
            self._update_stores()

            # Query stores and check relevance
            results = self.query(prompt, n=num_results, strict=strict)
            if results and all(r['score'] >= relevance_threshold for r in results):
                self.logger.info(f"Found relevant results at depth {current_depth}")
                break

            # Filter out already visited or discovered URLs
            next_urls = [url for url in next_urls if url not in all_discovered_urls and url not in self.visited_urls]

            # Update tracking sets
            all_discovered_urls.update(next_urls)
            urls_to_crawl = next_urls

            # Increment depth
            current_depth += 1
            
            # Status update
            self.logger.info(f"Depth {current_depth-1} complete. Found {len(next_urls)} new URLs for next depth.")
            self.logger.info(f"Total URLs discovered: {len(all_discovered_urls)}")
            self.logger.info(f"Total content collected: {len(self.content_store)} pages")
        
        # Final save
        if self.content_store:
            self.vector_store = store.update_vector_store(
                self.content_store,
                self.vector_store,
                self.embeddings
            )
            
            store.save_state(self.visited_urls, self.heuristics.content_hashes, self.content_store, self.logger)
        
        # Final logging
        urls_this_run = len([u for u in self.visited_urls if u in all_discovered_urls])
        self.logger.info(f"Crawling complete.")
        self.logger.info(f"URLs processed:")
        self.logger.info(f" Visited this run: {urls_this_run}")
        self.logger.info(f" Historical total: {len(self.visited_urls)}")
        self.logger.info(f"Collected content from {len(self.content_store)} pages.")
    

    def _update_stores(self):
        """Update vector store and content store with new content."""
        if self.content_store:
            self.vector_store = store.update_vector_store(
                self.content_store,
                self.vector_store,
                self.embeddings
            )
            store.save_state(self.visited_urls, self.heuristics.content_hashes, self.content_store, self.logger)
        self.logger.info("Updated stores with new content.")
    
    
    def _process_urls_at_depth(self, urls: List[str], prompt_keywords: List[str],
                          prompt: str, relevance_threshold: float, depth: int,
                          strict: bool = False, num_results: int = 3,
                          batch_size: int = 10) -> Tuple[List[str], bool]:
        """
        Process URLs at the current depth level in batches with parallel processing.
        
        Returns:
            Tuple of (next_urls, found_relevant_results)
        """
        next_urls = []
        found_relevant_results = False
        
        # Process URLs in batches
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i+batch_size]
            self.logger.info(f"Processing batch {i//batch_size + 1} of {(len(urls) + batch_size - 1)//batch_size}")
            
            # Skip already visited URLs
            batch_urls = [url for url in batch_urls if url not in self.visited_urls]
            
            if not batch_urls:
                continue
                
            # Parallelize URL evaluation
            url_scores = self._parallel_evaluate_urls(batch_urls, prompt_keywords)
            
            # Sort URLs by score for prioritized crawling
            prioritized_urls = sorted(url_scores.items(), key=lambda x: x[1][0], reverse=True)
            
            # Process URLs (sequentially for depth 0, in parallel for depths > 0)
            if depth == 0:
                for url, (score, soup, metadata) in prioritized_urls:
                    extracted_urls = self._process_single_url(url, score, soup, metadata)
                    next_urls.extend(extracted_urls)
            else:
                # For deeper levels, use parallel processing
                extracted_urls = self._parallel_process_urls(prioritized_urls)
                next_urls.extend(extracted_urls)
            
            # Update stores with new content after each batch
            self._update_stores()
            
            # Check if we have relevant results after processing this batch
            results = self.query(prompt, n=num_results, strict=strict)
            if results and all(r['score'] >= relevance_threshold for r in results):
                self.logger.info(f"Found relevant results after processing batch {i//batch_size + 1}")
                found_relevant_results = True
                break
        
        return next_urls, found_relevant_results


    def _parallel_evaluate_urls(self, urls: List[str], prompt_keywords: List[str]) -> Dict[str, Tuple]:
        """
        Evaluate URLs in parallel to calculate their relevance scores.
        """
        url_scores = {}
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(config.crawler.max_parallel_requests, len(urls))
        ) as executor:
            future_to_url = {
                executor.submit(self._evaluate_single_url, url, prompt_keywords): url 
                for url in urls
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        score, soup, metadata = result
                        if score >= config.crawler.url_relevance_threshold:
                            url_scores[url] = (score, soup, metadata)
                            self.logger.info(f"URL {url} received score: {score:.2f}")
                        else:
                            self.logger.info(f"URL {url} discarded due to low relevance score: {score:.2f}")
                except Exception as e:
                    self.logger.error(f"Error evaluating {url}: {str(e)}")
                    self.visited_urls.add(url)
        
        return url_scores

    def _evaluate_single_url(self, url: str, prompt_keywords: List[str]):
        """
        Evaluate a single URL to calculate its relevance score.
        """
        try:
            self.logger.info(f"Evaluating: {url}")
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Calculate page score using heuristics
            score, metadata = self.heuristics.calculate_page_score(soup, url, prompt_keywords)
            return (score, soup, metadata)
        except Exception as e:
            self.logger.error(f"Error evaluating {url}: {str(e)}")
            return None

    def _parallel_process_urls(self, prioritized_urls: List[Tuple[str, Tuple]]) -> List[str]:
        """
        Process URLs in parallel to extract content and links.
        
        Args:
            prioritized_urls: List of (url, (score, soup, metadata)) tuples
            
        Returns:
            List of new URLs discovered
        """
        all_next_urls = []
        
        # Check if there are any URLs to process
        if not prioritized_urls:
            self.logger.warning("No URLs to process in parallel (all were filtered out)")
            return all_next_urls
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(config.crawler.max_parallel_requests, len(prioritized_urls))
        ) as executor:
            future_to_url = {
                executor.submit(self._process_single_url, url, score, soup, metadata): url 
                for url, (score, soup, metadata) in prioritized_urls
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    extracted_urls = future.result()
                    all_next_urls.extend(extracted_urls)
                    self.logger.info(f"Processed URL {url}, found {len(extracted_urls)} new URLs")
                except Exception as e:
                    self.logger.error(f"Error processing {url}: {str(e)}")
                    self.visited_urls.add(url)
        
        return all_next_urls


    def _process_single_url(self, url: str, score: float, soup: BeautifulSoup,
                       metadata: Dict) -> List[str]:
        """
        Process a single URL and extract content and links.
        
        Args:
            url: URL to process
            score: Relevance score
            soup: BeautifulSoup object
            metadata: URL metadata
            
        Returns:
            List of new URLs discovered
        """
        extracted_urls = []
        
        try:
            self.logger.info(f"Processing URL: {url} (score: {score:.2f})")
            
            # Extract content using our extractor
            content = extractor.extract_content(soup, url, self.pattern_memory, clean_text)
            
            # Check if content should be processed
            if content['content'] and self.heuristics.should_process_content(content['content'], url):
                # Add metadata from heuristics
                content.update(metadata)
                self.content_store.append(content)
            else:
                self.logger.info(f"Content from {url} was filtered out (too short or duplicate)")
            
            # Extract links for next depth - do this regardless of content quality
            extracted_urls = self._extract_links(soup, url)
            
            self.visited_urls.add(url)
                
        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            self.visited_urls.add(url)
        
        return extracted_urls
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract links from a page for the next crawl depth.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        from urllib.parse import urljoin, urlparse
        
        links = []
        
        # Find all elements with 'href' attribute, not just 'a' tags
        for element in soup.find_all(href=True):
            href = element['href']
            
            # Skip empty links, anchors, javascript, mailto, etc.
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Skip URLs from different domains (optional, remove if you want to follow external links)
            base_domain = urlparse(base_url).netloc
            link_domain = urlparse(absolute_url).netloc
            
            if base_domain != link_domain:
                continue
            
            # Add URL to the list if it's not already visited
            if absolute_url not in self.visited_urls:
                links.append(absolute_url)
        
        return links

    
    def _save_progress(self):
        """Save current progress to disk."""
        self.vector_store = store.update_vector_store(
            self.content_store,
            self.vector_store,
            self.embeddings
        )
        
        store.save_state(self.visited_urls, self.heuristics.content_hashes, self.content_store, self.logger)
        self.logger.info("Saved current progress.")
    
    def create_vector_store(self):
        """Create the vector store from crawled content."""
        self.vector_store = store.create_vector_store(self.content_store, self.embeddings, self.logger)
    
    def query(self, question: str, n: int = 3, strict: bool = False) -> List[Dict]:
        """
        Query the vector store for relevant content using hybrid scoring.
        
        Args:
            question: The query string
            n: Number of results to return
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
        buffer_n = n * 3 if strict else n
        
        # Get FAISS vector similarity results
        faiss_results = self.vector_store.similarity_search_with_relevance_scores(question, k=buffer_n)
        
        # Get TF-IDF cosine similarity results
        tfidf_results = store.tfidf_similarity_search(self.content_store, question, k=buffer_n)
        
        # Combine results with weighted scoring (70% FAISS, 30% TF-IDF)
        combined_results = self._combine_search_results(faiss_results, tfidf_results, faiss_weight=config.store.weights['faiss'])
        
        if strict and self.seed_urls:
            # Filter results to only include those from seed URLs
            filtered_results = []
            for doc, score in combined_results:
                # Check if the document's source URL is in seed_urls
                if doc.metadata['source'] in self.seed_urls:
                    filtered_results.append((doc, score))
                
                # Break if we have enough results
                if len(filtered_results) >= n:
                    break
            
            # Use filtered results
            results = filtered_results[:n]
        else:
            # In non-strict mode, just take top n
            results = combined_results[:n]
        
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
    
    def _combine_search_results(self, faiss_results, tfidf_results, faiss_weight=config.store.weights['faiss']):
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