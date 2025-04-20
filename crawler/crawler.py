# crawler.py (Updated with URLHeuristics)
"""
Core Adaptive Web Crawler implementation.
Manages the crawling process, fetching, extraction, scoring, and interaction
with the store module. Uses parallel processing for efficiency.
Includes URL-based filtering before adding to the queue.
"""
import concurrent.futures
from typing import List, Dict, Optional, Set

# Import project components
from config import config
from crawler.logger import setup_logger
from crawler.utils import is_valid_url
from crawler.search import perform_search
from crawler import extractor # Use the refactored extractor
from crawler.heuristics import ContentHeuristics, URLHeuristics
from crawler.evaluation_metrics import HarvestRatio
from crawler.store import builder, persistence, scorer # Use the new store modules

class AdaptiveWebCrawler:
    def __init__(self):
        """Initializes the crawler."""
        self.logger = setup_logger()
        # Keep ContentHeuristics for page content scoring
        self.content_heuristics = ContentHeuristics()
        # Initialize harvest ratio metric
        self.harvest_ratio_metric = HarvestRatio()

        # State managed externally, loaded/saved via persistence
        self.visited_urls: Set[str] = set()
        # self.content_hashes are managed within content_heuristics instance

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
        # Load hashes into the content_heuristics instance
        self.content_heuristics.load_hashes(loaded_hashes)
        self.logger.info(f"Loaded state: {len(self.visited_urls)} visited URLs, "
                         f"{len(self.content_heuristics.content_hashes)} content hashes, "
                         f"{len(builder.get_content_store())} items in content store.")

    def _save_crawler_state(self):
        """Saves the current crawler state."""
        self.logger.info("Saving crawler state...")
        # Save hashes from the content_heuristics instance
        persistence.save_state(self.visited_urls, self.content_heuristics.content_hashes)
        self.logger.info("Crawler state saved.")

    # Added parameters back to crawl method signature
    def crawl(self, original_prompt: str, search_prompt: str, query_prompt: str, prompt_keywords:List[str],
               urls: Optional[List[str]] = None, num_seed_urls: Optional[int] = None,
               max_depth: Optional[int] = None, base_relevance_threshold: Optional[float] = None):
        """
        Starts the crawl process with stricter batch-by-batch processing per depth.
        Uses URLHeuristics to filter URLs before adding them to the crawl queue.

        Args:
            original_prompt: The original user query.
            search_prompt: The prompt formatted for search engines.
            query_prompt: The prompt formatted for the internal store query.
            prompt_keywords: Keywords extracted from the expanded query.
            urls: Optional list of initial URLs to crawl.
            num_seed_urls: Number of URLs to fetch from search if `urls` is not provided.
            max_depth: Maximum crawl depth.
            base_relevance_threshold: Starting content relevance threshold for depth 0.
        """
        # Use provided parameters or fall back to defaults stored in self
        current_num_seed_urls = num_seed_urls if num_seed_urls is not None else self.default_num_seed_urls
        current_max_depth = max_depth if max_depth is not None else self.default_max_depth
        current_base_relevance_threshold = base_relevance_threshold if base_relevance_threshold is not None else self.default_base_relevance_threshold

        self.logger.info(f"Starting crawl for prompt: '{original_prompt}'")
        self.logger.info(f"Crawl Params: num_seed={current_num_seed_urls}, max_depth={current_max_depth}, base_relevance={current_base_relevance_threshold}")
        self.logger.info(f"Using keywords for scoring: {prompt_keywords}")

        # --- Instantiate URLHeuristics for this crawl ---
        url_heuristics = URLHeuristics(prompt_keywords)

        # --- Determine Seed URLs ---
        raw_seed_urls: List[str] = []
        if urls:
            valid_provided_urls = list(set(filter(is_valid_url, urls))) # Filter invalid URLs
            # Combine provided URLs with search results
            self.logger.info(f"Fetching {current_num_seed_urls} additional URLs from search...")
            search_results = perform_search(search_prompt, current_num_seed_urls)
            raw_seed_urls = list(set(valid_provided_urls) | set(search_results)) # Use set union for unique URLs
            self.logger.info(f"Combined provided valid URLs with search results: {len(raw_seed_urls)}")
        else:
            self.logger.info(f"No URLs provided, performing search for {current_num_seed_urls} seed URLs...")
            raw_seed_urls = perform_search(search_prompt, current_num_seed_urls)
            self.logger.info(f"Obtained seed URLs from search: {len(raw_seed_urls)}")

        if not raw_seed_urls:
            self.logger.warning("No valid seed URLs found. Stopping crawl.")
            return

        # --- Filter Seed URLs using URLHeuristics ---
        filtered_seed_urls = url_heuristics.select_best_urls(raw_seed_urls)
        self.logger.info(f"Selected {len(filtered_seed_urls)} seed URLs after URL keyword filtering.")

        if not filtered_seed_urls:
            self.logger.warning("No seed URLs passed URL keyword filtering. Stopping crawl.")
            return

        # --- Crawling Loop ---
        current_depth = 0
        # Start with the filtered seed URLs, excluding already visited ones
        urls_to_crawl_this_depth = [url for url in filtered_seed_urls if url not in self.visited_urls]
        all_discovered_urls = set(urls_to_crawl_this_depth) | self.visited_urls # Track all URLs encountered

        while current_depth <= current_max_depth and urls_to_crawl_this_depth:
            self.logger.info(f"\n--- Starting Crawl Depth {current_depth} ---")
            self.logger.info(f"URLs to process at this depth (after filtering): {len(urls_to_crawl_this_depth)}")

            # Calculate content relevance threshold for this depth
            current_depth_relevance_threshold = max(
                self.min_crawl_relevance,
                current_base_relevance_threshold - (current_depth * self.depth_relevance_step)
            )
            self.logger.info(f"Content Relevance threshold for depth {current_depth}: {current_depth_relevance_threshold:.2f}")

            discovered_links_this_depth: Set[str] = set() # Collect all links found at this depth *before* filtering
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
                            # Pass content_heuristics instance, not the class itself
                            future = executor.submit(self._process_single_url, url, prompt_keywords, current_depth, current_depth_relevance_threshold, self.content_heuristics)
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
                                # Add newly discovered, valid links to the set for this depth
                                new_raw_links_count = 0
                                for link in result_links:
                                     # Check validity only here, not visited or keyword status yet
                                    if is_valid_url(link):
                                        discovered_links_this_depth.add(link)
                                        new_raw_links_count += 1
                                if new_raw_links_count > 0:
                                    self.logger.debug(f"Discovered {new_raw_links_count} raw valid links from {url}")


                        except Exception as exc:
                            self.logger.error(f"URL {url} generated an exception during processing: {exc}", exc_info=False)
                            self.visited_urls.add(url) # Mark as visited even if failed to prevent retries

                self.logger.info(f"--- Batch {i // self.batch_size + 1} Complete (Processed {processed_count_this_batch} URLs) ---")

                # --- Check for early stopping AFTER each batch is fully processed ---
                self.logger.debug(f"Checking early stop condition after batch {i // self.batch_size + 1}.")
                # Query needs the crawler instance's content store knowledge
                query_results = self.query(query_prompt, n=self.default_num_results)

                if query_results:
                    scores = [r['weighted_score'] for r in query_results]
                    self.logger.debug(f"Checking scores for early stop: {scores} against threshold {current_depth_relevance_threshold:.2f}")
                    # Use content relevance threshold for early stopping based on query results
                    if len(query_results) >= self.default_num_results and all(r['weighted_score'] >= current_depth_relevance_threshold for r in query_results):
                        self.logger.info(f"Found {len(query_results)} relevant results meeting content threshold score: {current_depth_relevance_threshold:.2f}. Stopping crawl early.")
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
            self.logger.info(f"Discovered {len(discovered_links_this_depth)} raw unique valid URLs during this depth.")

            # --- Filter Discovered URLs for Next Depth using URLHeuristics ---
            # Filter only links that haven't been seen/queued before
            newly_discovered_links = [link for link in discovered_links_this_depth if link not in all_discovered_urls]
            self.logger.info(f"Found {len(newly_discovered_links)} potentially new unique URLs.")

            if newly_discovered_links:
                # Apply URL keyword filtering
                next_depth_urls_filtered = url_heuristics.select_best_urls(newly_discovered_links)
                self.logger.info(f"Selected {len(next_depth_urls_filtered)} URLs for next depth after URL keyword filtering.")

                # Update the set of all discovered URLs and prepare the list for the next loop iteration
                urls_to_crawl_this_depth = []
                for url in next_depth_urls_filtered:
                    if url not in all_discovered_urls: # Final check
                         urls_to_crawl_this_depth.append(url)
                         all_discovered_urls.add(url) # Add selected URLs to the global set
            else:
                 urls_to_crawl_this_depth = [] # No new links found or selected

            self.logger.info(f"Total content items in store: {len(builder.get_content_store())}")

            # At the end of each depth, log the harvest ratio for this depth
            depth_hr = self.harvest_ratio_metric.get_depth_harvest_ratio(current_depth)
            self.logger.info(f"Harvest ratio at depth {current_depth}: {depth_hr:.4f}")

            current_depth += 1

            # Periodic save state
            if current_depth % config.crawler.save_frequency == 0:
                 self._save_crawler_state()

        # --- Finalization ---
        self.logger.info(f"Crawling finished (max depth {current_max_depth} reached, stopped early, or no more URLs).")

        # At the end of crawl, log the cumulative harvest ratio
        cumulative_hr = self.harvest_ratio_metric.get_cumulative_harvest_ratio()
        self.logger.info(f"Cumulative harvest ratio: {cumulative_hr:.4f}")

        # Final save
        self._save_crawler_state() 

    def _process_single_url(self, url: str, prompt_keywords: List[str], current_depth: int, content_relevance_threshold: float, content_scorer: ContentHeuristics) -> Optional[List[str]]:
        """
        Fetches, extracts, scores content, and stores content for a single URL.
        Uses the provided ContentHeuristics instance for scoring and duplicate checks.

        Args:
            url: The URL to process.
            prompt_keywords: Keywords for scoring relevance.
            content_relevance_threshold: The minimum content heuristic score needed.
            content_scorer: The ContentHeuristics instance to use.

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

        # 3. Score Page Content Relevance (using the passed ContentHeuristics instance)
        page_score = content_scorer.calculate_page_score(extracted_data, prompt_keywords)
        extracted_data['heuristic_score'] = page_score # Add score to data
        self.logger.info(f"Content heuristic score for {url}: {page_score:.3f}")

        # Record this page in harvest ratio metrics
        self.harvest_ratio_metric.record_page(
            depth=current_depth,  # You need to pass this from the crawl method
            page_score=page_score,
            depth_threshold=content_relevance_threshold,
            is_processed=True
        )

        # 4. Check if content should be processed (Duplicate Check & Basic Quality - using the passed instance)
        # Pass the cleaned main content text for hashing
        should_process = content_scorer.should_process_content(extracted_data['main_content'], url)

        if page_score >= content_relevance_threshold and should_process:
            # 5. Add to Content Store (via builder)
            builder.add_content(extracted_data)
            self.logger.debug(f"Added content from {url} to store.")
            # Return the links discovered on this relevant page
            return extracted_data.get('links', [])
        else:
            if page_score < content_relevance_threshold:
                 self.logger.info(f"Skipping store for {url}: Content score {page_score:.3f} below threshold {content_relevance_threshold:.2f}")
            if not should_process:
                 # Reason logged within should_process_content (duplicate or empty)
                 pass
            # Even if not stored, return links if the page was reachable (helps exploration)
            # Crucial: Return links even if content score is low, so URL heuristics can filter them later
            return extracted_data.get('links', [])

    def query(self, prompt: str, n: Optional[int] = None) -> List[Dict]:
        """
        Queries the crawled content store using TF-IDF similarity.

        Args:
            prompt: The query string.
            n: Number of results to return. Uses default if None.

        Returns:
            List of relevant documents (dictionaries) with metadata and scores.
        """
        num_results_to_get = n if n is not None else self.default_num_results

        self.logger.info(f"Querying content store for: '{prompt}' (top {num_results_to_get} results)")

        # Use the store builder to get the current store
        current_content_store = builder.get_content_store()
        if len(current_content_store) == 0:
            self.logger.warning("Query attempted on empty content store.")
            return []

        # Use the weighted scorer
        results = scorer.calculate_score(query=prompt, k=num_results_to_get, weight_heuristic=config.store.heuristic_score_weight, weight_cosine=config.store.cosine_similarity_score_weight)

        # Format results
        formatted_results = []
        for res in results:
            formatted = {
                'content': res.get('main_content', ''),
                'source': res.get('url', 'N/A'),
                'title': res.get('title', 'N/A'),
                'domain': res.get('domain', 'N/A'),
                'heuristic_score': res.get('heuristic_score', 0.0),
                'cosine_similarity_score': res.get('cosine_similarity_score', 0.0),
                'weighted_score': res.get('weighted_score', 0.0),
                'publish_date': res.get('publish_date', 'N/A'),
                'content_length': res.get('content_length', 0)
                }
            formatted_results.append(formatted)

        self.logger.info(f"Query returned {len(formatted_results)} results.")
        if formatted_results:
            self.logger.debug(f"Top result score: \n(Heuristic): {formatted_results[0]['heuristic_score']:.4f}\n(Cosine): {formatted_results[0]['cosine_similarity_score']:.4f}\n(Weighted): {formatted_results[0]['weighted_score']:.4f}")

        return formatted_results