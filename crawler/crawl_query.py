# crawl_query.py (Updated with from_cache logic and store length)
"""
API endpoint function to initiate a crawl and query operation.
Uses the refactored AdaptiveWebCrawler and store modules.
Includes logic to check existing store before crawling ('from_cache').
"""
from typing import List, Dict, Optional

from crawler.crawler import AdaptiveWebCrawler
from crawler.store import builder # Import builder to get store length
# from crawler.llm_response import generate_llm_response # Keep commented LLM import
from crawler.logger import setup_logger
from config import config # Use config for defaults

logger = setup_logger()

def perform_crawl_and_query(
    prompt: str,
    urls: Optional[List[str]] = None,
    n: Optional[int] = None, # Allow overriding config default
    num_seed_urls: Optional[int] = None, # Allow overriding config default
    max_depth: Optional[int] = None, # Allow overriding config default
    force_crawl: bool = False, # Flag to force crawl even if cache is sufficient
    relevance_threshold: Optional[float] = None, # Allow overriding config default
    use_llm: bool = False # Keep LLM flag
) -> Dict:
    """
    Performs a crawl operation based on a prompt and optional URLs,
    then queries the resulting content store. Checks existing store first.

    Args:
        prompt (str): The user's query/prompt.
        urls (Optional[List[str]]): Optional list of URLs to start crawling.
        n (Optional[int]): Number of results to return from query. Defaults to config.
        num_seed_urls (Optional[int]): Number of seed URLs from search if `urls` is None. Defaults to config.
        max_depth (Optional[int]): Maximum crawl depth. Defaults to config.
        force_crawl (bool): If True, forces a crawl even if cached results are sufficient.
        relevance_threshold (Optional[float]): Base relevance threshold for crawl depth 0 and cache check. Defaults to config.
        use_llm (bool): Whether to generate an LLM response (LLM logic remains commented).

    Returns:
        Dict containing status, results, metadata, and optional LLM response.
    """
    logger.info(f"Received crawl request for prompt: '{prompt}'")
    if urls: logger.info(f"Provided URLs: {urls}")
    if force_crawl: logger.info("`force_crawl` flag is set, will crawl regardless of cache.")

    # Use provided parameters or fall back to config defaults
    num_results_final = n if n is not None else config.api.crawl.num_results
    num_seed_urls_final = num_seed_urls if num_seed_urls is not None else config.api.crawl.num_seed_urls
    max_depth_final = max_depth if max_depth is not None else config.api.crawl.max_depth
    base_relevance_threshold_final = relevance_threshold if relevance_threshold is not None else config.api.crawl.relevance_threshold

    results = []
    from_cache = False
    crawler = None # Initialize crawler variable

    try:
        # 1. Instantiate the crawler - it loads existing state automatically
        crawler = AdaptiveWebCrawler()

        # 2. Check cache (existing store) before crawling if force_crawl is False
        if not force_crawl:
            logger.info("Checking existing store (cache) for relevant results...")
            initial_results = crawler.query(prompt, n=num_results_final)
            # Check if enough results meet the base relevance threshold
            if initial_results and len(initial_results) >= num_results_final and all(r['score'] >= base_relevance_threshold_final for r in initial_results):
                logger.info(f"Found {len(initial_results)} sufficient results in cache meeting threshold {base_relevance_threshold_final:.2f}. Skipping crawl.")
                results = initial_results
                from_cache = True
            else:
                 logger.info("Existing store does not contain sufficient results or threshold not met. Proceeding with crawl.")
        else:
            logger.info("`force_crawl` is True. Skipping cache check.")


        # 3. Perform Crawl if not served from cache
        if not from_cache:
            logger.info("Starting crawl process...")
            crawler.crawl(
                prompt=prompt,
                urls=urls,
                num_seed_urls=num_seed_urls_final,
                max_depth=max_depth_final,
                base_relevance_threshold=base_relevance_threshold_final
            )
            # Query again after crawling to get the final results
            results = crawler.query(prompt, n=num_results_final)
            logger.info("Crawl process finished.")


        # --- Generate LLM Response (Optional) ---
        llm_response = None
        # if use_llm and results:
        #     try:
        #         logger.info("Generating LLM response...")
        #         # Assuming generate_llm_response exists and takes results + prompt
        #         # llm_response = generate_llm_response(results, prompt)
        #         logger.info("LLM response generated.")
        #     except Exception as llm_err:
        #         logger.error(f"Failed to generate LLM response: {llm_err}", exc_info=True)
        #         llm_response = f"Error generating LLM response: {llm_err}" # Include error in response


        # --- Prepare Metadata ---
        # Access final state from crawler instance and store builder
        final_visited_count = len(crawler.visited_urls) if crawler else 0
        # Get content store length directly from the builder module
        final_content_count = len(builder.get_content_store())

        metadata = {
            "urls": {
                "visited_total": final_visited_count,
                "seed_urls_used": len(urls) if urls else num_seed_urls_final,
            },
            "content_collected_total": final_content_count,
            "from_cache": from_cache # Include the cache flag
        }

        # --- Build Final Response ---
        response = {
            "status": "success",
            "results": results,
            "metadata": metadata
        }

        if llm_response:
            response["llm_response"] = llm_response

        logger.info(f"Request completed successfully. Returning {len(results)} results. (Served from cache: {from_cache})")
        return response

    except Exception as e:
        logger.error(f"Critical error in perform_crawl_and_query: {e}", exc_info=True)
        # Attempt to get some metadata even in case of error
        try:
            visited_count = len(crawler.visited_urls) if crawler else 0
            content_count = len(builder.get_content_store())
        except:
            visited_count = 0
            content_count = 0

        return {
            "status": "error",
            "error": f"An unexpected error occurred: {str(e)}",
            "results": [],
            "metadata": {
                 "urls": {"visited_total": visited_count},
                 "content_collected_total": content_count,
                 "from_cache": False # Assume not from cache if error occurred
            }
        }