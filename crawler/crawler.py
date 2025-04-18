# crawler.py (Updated)
"""
Core Adaptive Web Crawler implementation.
Manages the crawling process, fetching, extraction, scoring, and interaction
with the store module. Uses parallel processing for efficiency.
"""
import concurrent.futures
import time
from typing import List, Dict, Optional, Set, Tuple

# Import project components
from config import config
from crawler.logger import setup_logger
from crawler.utils import is_valid_url, extract_keywords
from crawler.search import perform_search
from crawler import extractor # Use the refactored extractor
from crawler.heuristics import ContentHeuristics
from crawler.store import builder, persistence, scorer # Use the new store modules

class AdaptiveWebCrawler:
    # Removed parameters from __init__ as they are request-specific
    def __init__(self):
        """Initializes the crawler."""
        self.logger = setup_logger()
        self.heuristics = ContentHeuristics()

        # State managed externally, loaded/saved via persistence
        self.visited_urls: Set[str] = set()
        # self.content_hashes are managed within heuristics instance

        # Configuration shortcuts (used if not overridden by crawl method)
        self.default_max_depth = config.api.crawl.max_depth
        self.default_num_results = config.api.crawl.num_results
        self.default_num_seed_urls = config.api.crawl.num_seed_urls
        self.default_base_relevance_threshold = config.api.crawl.relevance_threshold

        self.min_crawl_relevance = config.crawler.minimum_relevance_threshold
        self.depth_relevance_step = config.crawler.depth_relevance_step
        self.max_workers = config.crawler.max_parallel_requests
        self.batch_size = config.crawler.batch_size

        self.logger.info("AdaptiveWebCrawler initialized.")
        # Load state immediately on initialization
        self._load_crawler_state()

    def _load_crawler_state(self):
        """Loads visited URLs and content store from persistence."""
        self.logger.info("Attempting to load previous crawler state...")
        # load_state now returns visited_urls, content_hashes
        # It also calls builder.initialize_store internally
        loaded_visited, loaded_hashes = persistence.load_state()
        self.visited_urls = loaded_visited
        self.heuristics.load_hashes(loaded_hashes) # Load hashes into heuristics instance
        self.logger.info(f"Loaded state: {len(self.visited_urls)} visited URLs, "
                         f"{len(self.heuristics.content_hashes)} content hashes, "
                         f"{len(builder.get_content_store())} items in content store.")

    def _save_crawler_state(self):
        """Saves the current crawler state."""
        self.logger.info("Saving crawler state...")
        persistence.save_state(self.visited_urls, self.heuristics.content_hashes)
        self.logger.info("Crawler state saved.")

    # Added parameters back to crawl method signature
    def crawl(self, prompt: str, urls: Optional[List[str]] = None, num_seed_urls: Optional[int] = None, max_depth: Optional[int] = None, base_relevance_threshold: Optional[float] = None):
        """
        Starts the crawl process with stricter batch-by-batch processing per depth.

        Args:
            prompt: User query/prompt.
            urls: Optional list of initial URLs to crawl.
            num_seed_urls: Number of URLs to fetch from search if `urls` is not provided. Uses default if None.
            max_depth: Override the maximum crawl depth. Uses default if None.
            base_relevance_threshold: Starting relevance threshold for depth 0. Uses default if None.
        """
        # Use provided parameters or fall back to defaults stored in self
        current_num_seed_urls = num_seed_urls if num_seed_urls is not None else self.default_num_seed_urls
        current_max_depth = max_depth if max_depth is not None else self.default_max_depth
        current_base_relevance_threshold = base_relevance_threshold if base_relevance_threshold is not None else self.default_base_relevance_threshold

        self.logger.info(f"Starting crawl for prompt: '{prompt}'")
        self.logger.info(f"Crawl Params: num_seed={current_num_seed_urls}, max_depth={current_max_depth}, base_relevance={current_base_relevance_threshold}")
        prompt_keywords = extract_keywords(prompt)
        self.logger.info(f"Using keywords for scoring: {prompt_keywords}")

        # --- Determine Seed URLs ---
        if urls:
            seed_urls = list(set(filter(is_valid_url, urls))) # Filter invalid URLs
            # Combine provided URLs with search results
            search_results = perform_search(prompt, current_num_seed_urls)
            seed_urls = list(set(seed_urls) | set(search_results)) # Use set union for unique URLs
            self.logger.info(f"Using provided valid seed URLs combined with search results: {len(seed_urls)}")
        else:
            self.logger.info(f"No URLs provided, performing search for {current_num_seed_urls} seed URLs...")
            seed_urls = perform_search(prompt, current_num_seed_urls)
            self.logger.info(f"Obtained seed URLs from search: {len(seed_urls)}")

        if not seed_urls:
            self.logger.warning("No valid seed URLs found. Stopping crawl.")
            return

        # --- Crawling Loop ---
        current_depth = 0
        urls_to_crawl_this_depth = [url for url in seed_urls if url not in self.visited_urls]
        all_discovered_urls = set(urls_to_crawl_this_depth) | self.visited_urls # Track all URLs encountered

        while current_depth <= current_max_depth and urls_to_crawl_this_depth:
            self.logger.info(f"\n--- Starting Crawl Depth {current_depth} ---")
            self.logger.info(f"URLs to process at this depth: {len(urls_to_crawl_this_depth)}")

            # Calculate relevance threshold for this depth
            current_depth_relevance_threshold = max(
                self.min_crawl_relevance,
                current_base_relevance_threshold - (current_depth * self.depth_relevance_step)
            )
            self.logger.info(f"Relevance threshold for depth {current_depth}: {current_depth_relevance_threshold:.2f}")

            next_depth_urls_discovered: Set[str] = set()
            processed_count_total_this_depth = 0
            stop_early = False # Flag to break outer loop if stopping early

            # --- Process URLs in Strict Batches ---
            for i in range(0, len(urls_to_crawl_this_depth), self.batch_size):
                batch_urls = urls_to_crawl_this_depth[i : i + self.batch_size]
                self.logger.info(f"--- Processing Batch {i // self.batch_size + 1} at Depth {current_depth} ({len(batch_urls)} URLs) ---")

                processed_count_this_batch = 0
                batch_futures = {}

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit only the URLs for the current batch
                    for url in batch_urls:
                        if url not in self.visited_urls: # Double check before submitting
                            future = executor.submit(self._process_single_url, url, prompt_keywords, current_depth_relevance_threshold)
                            batch_futures[future] = url

                    # Process completed futures for THIS BATCH ONLY
                    for future in concurrent.futures.as_completed(batch_futures):
                        url = batch_futures[future]
                        try:
                            result_links = future.result() # Returns list of discovered links or None
                            processed_count_this_batch += 1
                            processed_count_total_this_depth += 1
                            self.visited_urls.add(url) # Mark as visited *after* successful processing

                            if result_links is not None:
                                # Add newly discovered, valid, unvisited links for the next depth
                                new_links_count = 0
                                for link in result_links:
                                    if is_valid_url(link) and link not in all_discovered_urls:
                                        next_depth_urls_discovered.add(link)
                                        all_discovered_urls.add(link) # Add to global discovered set
                                        new_links_count += 1
                                if new_links_count > 0:
                                    self.logger.debug(f"Discovered {new_links_count} new URLs from {url}")

                        except Exception as exc:
                            self.logger.error(f"URL {url} generated an exception during processing: {exc}", exc_info=False)
                            self.visited_urls.add(url) # Mark as visited even if failed to prevent retries

                self.logger.info(f"--- Batch {i // self.batch_size + 1} Complete (Processed {processed_count_this_batch} URLs) ---")

                # --- Check for early stopping AFTER each batch is fully processed ---
                self.logger.debug(f"Checking early stop condition after batch {i // self.batch_size + 1}.")
                query_results = self.query(prompt, n=self.default_num_results)

                if query_results:
                    scores = [r['score'] for r in query_results]
                    self.logger.debug(f"Checking scores for early stop: {scores} against threshold {current_depth_relevance_threshold:.2f}")
                    if len(query_results) >= self.default_num_results and all(r['score'] >= current_depth_relevance_threshold for r in query_results):
                        self.logger.info(f"Found {len(query_results)} relevant results meeting threshold {current_depth_relevance_threshold:.2f}. Stopping crawl early.")
                        stop_early = True
                        break # Exit the batch loop for this depth
                else:
                    self.logger.debug("No query results found for early stop check.")

            # --- End of Batch Loop ---

            if stop_early:
                break # Exit the depth loop

            # --- Prepare for Next Depth ---
            self.logger.info(f"--- Depth {current_depth} Complete ---")
            self.logger.info(f"Processed {processed_count_total_this_depth} URLs in total for this depth.")
            self.logger.info(f"Discovered {len(next_depth_urls_discovered)} new unique URLs for next depth.")
            self.logger.info(f"Total content items in store: {len(builder.get_content_store())}")

            # Set up URLs for the next iteration
            urls_to_crawl_this_depth = list(next_depth_urls_discovered)
            current_depth += 1

            # Periodic save state (consider saving after each depth or less frequently)
            if current_depth % config.crawler.save_frequency == 0:
                 self._save_crawler_state()

        # --- Finalization ---
        self.logger.info(f"Crawling finished (max depth {current_max_depth} reached, stopped early, or no more URLs).")
        self._save_crawler_state() # Final save

    def _process_single_url(self, url: str, prompt_keywords: List[str], relevance_threshold: float) -> Optional[List[str]]:
        """
        Fetches, extracts, scores, and stores content for a single URL.

        Args:
            url: The URL to process.
            prompt_keywords: Keywords for scoring relevance.
            relevance_threshold: The minimum heuristic score needed for this depth.

        Returns:
            A list of discovered valid links from the page, or None if processing fails
            or content is deemed irrelevant/duplicate.
        """
        self.logger.debug(f"Processing URL: {url}")

        # 1. Fetch Page
        fetch_result = extractor.fetch_page(url)
        if not fetch_result:
            return None # Fetch failed
        html_content, final_url = fetch_result

        # Handle redirects: update visited_urls if redirected
        if final_url != url:
            self.logger.info(f"URL redirected: {url} -> {final_url}")
            if final_url in self.visited_urls:
                self.logger.info(f"Redirected URL {final_url} already visited. Skipping.")
                self.visited_urls.add(url) # Mark original URL as visited too
                return None
            url = final_url # Process the final URL

        # 2. Extract Content (Now uses readability)
        extracted_data = extractor.parse_and_extract(html_content, url)
        if not extracted_data:
            self.logger.debug(f"Extraction failed or no significant content for {url}")
            return None # Extraction failed or content too sparse

        # 3. Score Page Relevance (Heuristic Score - applied to readability output)
        page_score = self.heuristics.calculate_page_score(extracted_data, prompt_keywords)
        extracted_data['heuristic_score'] = page_score # Add score to data
        self.logger.info(f"Heuristic score for {url}: {page_score:.3f}")

        # 4. Check if content should be processed (Duplicate Check & Basic Quality)
        # Pass the cleaned main content text for hashing
        should_process = self.heuristics.should_process_content(extracted_data['main_content'], url)

        if page_score >= relevance_threshold and should_process:
            # 5. Add to Content Store (via builder)
            builder.add_content(extracted_data)
            self.logger.debug(f"Added content from {url} to store.")
            # Return the links discovered on this relevant page
            return extracted_data.get('links', [])
        else:
            if page_score < relevance_threshold:
                 self.logger.info(f"Skipping store for {url}: Score {page_score:.3f} below threshold {relevance_threshold:.2f}")
            if not should_process:
                 # Reason logged within should_process_content (duplicate or empty)
                 pass
            # Even if not stored, return links if the page was reachable (helps exploration)
            # Modify this if you only want links from *stored* pages
            return extracted_data.get('links', [])

    # Added parameter n back to query method
    def query(self, question: str, n: Optional[int] = None) -> List[Dict]:
        """
        Queries the crawled content store using TF-IDF similarity.

        Args:
            question: The query string.
            n: Number of results to return. Uses default if None.

        Returns:
            List of relevant documents (dictionaries) with metadata and scores.
        """
        num_results_to_get = n if n is not None else self.default_num_results

        self.logger.info(f"Querying content store for: '{question}' (top {num_results_to_get} results)")

        # Use the store builder to get the current store
        current_content_store = builder.get_content_store()
        if len(current_content_store) == 0:
            self.logger.warning("Query attempted on empty content store.")
            return []

        # Use the TF-IDF scorer
        results = scorer.tfidf_similarity_search(query=question, k=num_results_to_get)

        # Format results (scorer already adds 'score')
        # Ensure required keys are present, add defaults if missing
        formatted_results = []
        for res in results:
             formatted = {
                 'content': res.get('main_content', ''), # Already fixed to main_content
                 'source': res.get('url', 'N/A'),
                 'title': res.get('title', 'N/A'),
                 'domain': res.get('domain', 'N/A'),
                 'score': res.get('score', 0.0), # TF-IDF score
                 'publish_date': res.get('publish_date'), # Already datetime or None
                 'content_length': res.get('content_length', 0),
                 'heuristic_score': res.get('heuristic_score', 0.0) # Include heuristic score if available
             }
             formatted_results.append(formatted)

        self.logger.info(f"Query returned {len(formatted_results)} results.")
        # Log top result score for debugging
        if formatted_results:
             self.logger.debug(f"Top result score (TF-IDF): {formatted_results[0]['score']:.4f}")

        return formatted_results