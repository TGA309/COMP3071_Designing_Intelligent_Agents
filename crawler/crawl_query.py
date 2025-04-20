# crawl_query.py (Updated with from_cache logic and store length)
"""
API endpoint function to initiate a crawl and query operation.
Uses the refactored AdaptiveWebCrawler and store modules.
Includes logic to check existing store before crawling ('from_cache').
"""
from typing import List, Dict, Optional

from crawler.crawler import AdaptiveWebCrawler
from crawler.store import builder # Import builder to get store length
from crawler.llm_processing import evaluate_responses, query_expansion,  generate_llm_response
from crawler.evaluation_metrics import EvaluationMetrics  # Import EvaluationMetrics
from crawler.logger import setup_logger
from config import config # Use config for defaults
from crawler.utils import strip_and_join_with_spaces, extract_keywords, format_keywords_for_search

logger = setup_logger()

def perform_crawl_and_query(
    prompt: str,
    urls: Optional[List[str]] = None,
    n: Optional[int] = None, # Allow overriding config default
    num_seed_urls: Optional[int] = None, # Allow overriding config default
    max_depth: Optional[int] = None, # Allow overriding config default
    force_crawl: bool = False, # Flag to force crawl even if cache is sufficient
    relevance_threshold: Optional[float] = None, # Allow overriding config default
    use_llm_response: bool = False # LLM response flag
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

    # Initialize evaluation metrics
    evaluation_metrics = EvaluationMetrics()
    
    # Start timing measurement
    evaluation_metrics.start_timer()

    # Do query expansion on prompt
    original_prompt = prompt
    query_expanded_list = query_expansion(prompt)
    search_prompt = format_keywords_for_search(query_expanded_list)
    prompt_keywords = extract_keywords(query_expanded_list)
    query_prompt = strip_and_join_with_spaces(prompt_keywords)

    logger.info(f"Original prompt: {original_prompt}")
    logger.info(f"Query Expanded List: {query_expanded_list}")
    logger.info(f"Search Prompt: {search_prompt}")
    logger.info(f"Query Prompt: {query_prompt}")
    logger.info(f"Prompt Keywords: {prompt_keywords}")
    

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
            initial_results = crawler.query(query_prompt, n=num_results_final)
            # Check if enough results meet the base relevance threshold
            if initial_results and len(initial_results) >= num_results_final and all(r['weighted_score'] >= base_relevance_threshold_final for r in initial_results):
                logger.info(f"Found {len(initial_results)} sufficient results in cache meeting threshold {base_relevance_threshold_final:.2f}. Skipping crawl.")
                results = initial_results
                
                # Record cache access in harvest ratio metric
                crawler.harvest_ratio_metric.record_cache_access(
                    results=initial_results,
                    base_relevance_threshold=base_relevance_threshold_final
                )
                
                # Set from_cache flag to True
                from_cache = True
            else:
                 logger.info("Existing store does not contain sufficient results or threshold not met. Proceeding with crawl.")
        else:
            logger.info("`force_crawl` is True. Skipping cache check.")


        # 3. Perform Crawl if not served from cache
        if not from_cache:
            logger.info("Starting crawl process...")
            crawler.crawl(
                original_prompt=original_prompt,
                search_prompt=search_prompt,
                query_prompt=query_prompt,
                prompt_keywords=prompt_keywords,
                urls=urls,
                num_seed_urls=num_seed_urls_final,
                max_depth=max_depth_final,
                base_relevance_threshold=base_relevance_threshold_final
            )
            # Query again after crawling to get the final results
            results = crawler.query(query_prompt, n=num_results_final)
            logger.info("Crawl process finished.")

        # Stop the timer before generating LLM Response and Evaluation
        evaluation_metrics.stop_timer()

        # --- Generate LLM Response (Optional) ---
        llm_response = None
        
        if use_llm_response and results:
            try:
                logger.info("Generating LLM response...")
                llm_response = generate_llm_response(original_prompt, results)
                logger.info("LLM response generated.")
            except Exception as llm_err:
                logger.error(f"Failed to generate LLM response: {llm_err}", exc_info=True)
                llm_response = f"Error generating LLM response: {llm_err}"  # Include error in response


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
        
        # Get comprehensive evaluation metrics
        evaluation_results = evaluation_metrics.evaluate(
            original_prompt=original_prompt,
            crawled_results=results,
            llm_response=llm_response if use_llm_response and llm_response else None,
            harvest_ratio_metrics=crawler.harvest_ratio_metric.get_metrics()
        )
        
        # --- Build Final Response ---
        response = {
            "status": "success",
            "results": results,
            "metadata": metadata,
            "llm_response": llm_response if (use_llm_response and llm_response) else "N/A",
            "evaluation_metrics": evaluation_results,
        }
        
        logger.info(f"Request completed successfully. Returning {len(results)} results. (Served from cache: {from_cache})")
        return response
        
    except Exception as e:
        # Stop timer even in case of error
        if 'evaluation_metrics' in locals():
            evaluation_metrics.stop_timer()
            
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
                "from_cache": False  # Assume not from cache if error occurred
            }
        }