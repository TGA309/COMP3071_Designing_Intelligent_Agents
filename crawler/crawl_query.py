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
    n: Optional[int] = None,
    num_seed_urls: Optional[int] = None,
    max_depth: Optional[int] = None,
    force_crawl: bool = False,
    relevance_threshold: Optional[float] = None,
    use_llm_response: bool = False
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
    # Initialize tracking variables
    original_prompt = prompt
    crawler = None
    results = []
    from_cache = False
    llm_response = None
    error_messages = []
    process_status = "success"  # Will be downgraded if errors occur
    
    # Initialize evaluation metrics
    evaluation_metrics = EvaluationMetrics()

    logger.info(f"Received crawl request for prompt: '{prompt}'")
    if urls: logger.info(f"Provided URLs: {urls}")
    if force_crawl: logger.info("`force_crawl` flag is set, will crawl regardless of cache.")
    
    # Start timing measurement
    try:
        evaluation_metrics.start_timer()
    except Exception as e:
        logger.error(f"Failed to start timer: {e}", exc_info=True)
        error_messages.append(f"Timer error: {str(e)}")
    
    # 1. INITIALIZATION PHASE
    try:
        # Query expansion
        query_expanded_list = query_expansion(prompt)
        search_prompt = format_keywords_for_search(query_expanded_list)
        prompt_keywords = extract_keywords(query_expanded_list)
        query_prompt = strip_and_join_with_spaces(prompt_keywords)
        
        # Configuration setup
        num_results_final = n if n is not None else config.api.crawl.num_results
        num_seed_urls_final = num_seed_urls if num_seed_urls is not None else config.api.crawl.num_seed_urls
        max_depth_final = max_depth if max_depth is not None else config.api.crawl.max_depth
        base_relevance_threshold_final = relevance_threshold if relevance_threshold is not None else config.api.crawl.relevance_threshold
        
        logger.debug(f"Original prompt: {original_prompt}")
        logger.debug(f"Query Expanded List: {query_expanded_list}")
        logger.debug(f"Search Prompt: {search_prompt}")
        logger.debug(f"Query Prompt: {query_prompt}")
        logger.debug(f"Prompt Keywords: {prompt_keywords}")
    except Exception as e:
        logger.error(f"Initialization error: {e}", exc_info=True)
        error_messages.append(f"Initialization error: {str(e)}")
        process_status = "error"
        # Early return if we can't even initialize
        return {
            "status": "error",
            "prompt": original_prompt,
            "error": f"Failed during initialization: {str(e)}",
            "results": [],
            "metadata": {"initialization_failed": True},
            "llm_response": "N/A",
            "evaluation_metrics": _get_partial_metrics(evaluation_metrics)
        }
    
    # 2. CRAWLER INITIALIZATION
    try:
        crawler = AdaptiveWebCrawler()
    except Exception as e:
        logger.error(f"Failed to initialize crawler: {e}", exc_info=True)
        error_messages.append(f"Crawler initialization error: {str(e)}")
        process_status = "error"
        # Early return if crawler fails to initialize
        return {
            "status": "error",
            "prompt": original_prompt,
            "error": f"Failed to initialize crawler: {str(e)}",
            "results": [],
            "metadata": {"crawler_initialization_failed": True},
            "llm_response": "N/A",
            "evaluation_metrics": _get_partial_metrics(evaluation_metrics)
        }
    
    # 3. CACHE CHECK PHASE
    cache_error = None
    try:
        if not force_crawl:
            logger.info("Checking existing store (cache) for relevant results...")
            initial_results = crawler.query(query_prompt, n=num_results_final)
            
            if initial_results and len(initial_results) >= num_results_final and all(r['weighted_score'] >= base_relevance_threshold_final for r in initial_results):
                logger.info(f"Found {len(initial_results)} sufficient results in cache.")
                results = initial_results
                crawler.harvest_ratio_metric.record_cache_access(
                    results=initial_results,
                    base_relevance_threshold=base_relevance_threshold_final
                )
                from_cache = True
            else:
                logger.info("Existing store does not contain sufficient results or threshold not met. Proceeding with crawl.")
        else:
            logger.info("`force_crawl` is True. Skipping cache check.")
    
    except Exception as e:
        logger.error(f"Cache check error: {e}", exc_info=True)
        error_messages.append(f"Cache check error: {str(e)}")
        cache_error = str(e)
        process_status = "partial_success"  # Continue despite cache error
    
    # 4. CRAWL PHASE (if not from cache)
    crawl_error = None
    if not from_cache:
        try:
            logger.info("Starting crawl process...")
            any_seed_url_crawled = crawler.crawl(
                original_prompt=original_prompt,
                search_prompt=search_prompt,
                query_prompt=query_prompt,
                prompt_keywords=prompt_keywords,
                urls=urls,
                num_seed_urls=num_seed_urls_final,
                max_depth=max_depth_final,
                base_relevance_threshold=base_relevance_threshold_final
            )

            if not any_seed_url_crawled:
                from_cache = True
            
            # Query to get results after crawling
            results = crawler.query(query_prompt, n=num_results_final)
            logger.info(f"Crawl complete, obtained {len(results)} results.")
        except Exception as e:
            logger.error(f"Crawl error: {e}", exc_info=True)
            error_messages.append(f"Crawl error: {str(e)}")
            crawl_error = str(e)
            process_status = "partial_success"
            
            # Try to get any available results despite crawl error
            try:
                emergency_results = crawler.query(query_prompt, n=num_results_final)
                if emergency_results:
                    logger.info(f"Retrieved {len(emergency_results)} results despite crawl error.")
                    results = emergency_results
            except Exception as query_e:
                logger.error(f"Failed to retrieve results after crawl error: {query_e}", exc_info=True)
    
    # Stop the timer before additional processing
    try:
        evaluation_metrics.stop_timer()
    except Exception as e:
        logger.error(f"Failed to stop timer: {e}", exc_info=True)
        error_messages.append(f"Timer error: {str(e)}")
    
    # 5. LLM RESPONSE PHASE (if requested)
    llm_error = None
    if use_llm_response and results:
        try:
            logger.info("Generating LLM response...")
            llm_response = generate_llm_response(original_prompt, results)
            logger.info("LLM response generated successfully.")
        except Exception as e:
            logger.error(f"LLM generation error: {e}", exc_info=True)
            error_messages.append(f"LLM error: {str(e)}")
            llm_error = str(e)
            process_status = "partial_success"
    
    # 6. METADATA COLLECTION
    try:
        final_visited_count = len(crawler.visited_urls) if crawler else 0
        final_content_count = len(builder.get_content_store())
        
        metadata = {
            "urls": {
                "visited_total": final_visited_count,
                "seed_urls_used": len(urls) if urls else num_seed_urls_final,
            },
            "content_collected_total": final_content_count,
            "from_cache": from_cache
        }
        
        # Add error information to metadata
        if cache_error:
            metadata["cache_error"] = cache_error
        if crawl_error:
            metadata["crawl_error"] = crawl_error
        if llm_error:
            metadata["llm_error"] = llm_error
    except Exception as e:
        logger.error(f"Metadata collection error: {e}", exc_info=True)
        error_messages.append(f"Metadata error: {str(e)}")
        metadata = {"metadata_collection_failed": True}
        process_status = "partial_success"
    
    # 7. EVALUATION PHASE
    evaluation_results = {}
    try:
        if crawler and results:
            evaluation_results = evaluation_metrics.evaluate(
                original_prompt=original_prompt,
                crawled_results=results,
                llm_response=llm_response if llm_response else None,
                harvest_ratio_metrics=crawler.harvest_ratio_metric.get_metrics()
            )
        else:
            # Limited evaluation without full results
            evaluation_results = _get_partial_metrics(evaluation_metrics)
    except Exception as e:
        logger.error(f"Evaluation error: {e}", exc_info=True)
        error_messages.append(f"Evaluation error: {str(e)}")
        evaluation_results = _get_partial_metrics(evaluation_metrics)
        process_status = "partial_success"
    
    # 8. PREPARE FINAL RESPONSE
    response = {
        "status": process_status,
        "prompt": original_prompt,
        "results": results,
        "metadata": metadata,
        "llm_response": llm_response if llm_response else "N/A",
        "evaluation_metrics": evaluation_results
    }
    
    # Add errors if any occurred
    if error_messages:
        response["error"] = error_messages
    
    logger.info(f"Request completed with status '{process_status}'. Returning {len(results)} results.")
    return response

def _get_partial_metrics(evaluation_metrics):
    """Helper function to get whatever metrics are available"""
    metrics = {}
    try:
        if evaluation_metrics:
            metrics["time_metrics"] = evaluation_metrics.time_metric.get_metrics()
    except:
        metrics["time_metrics"] = {"error": "Failed to retrieve time metrics"}
    return metrics
