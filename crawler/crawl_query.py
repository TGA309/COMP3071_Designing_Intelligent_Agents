# crawler/crawl_query.py
from typing import List, Dict, Optional
from crawler.crawler import AdaptiveWebCrawler
from crawler.llm_response import generate_llm_response
from crawler.logger import setup_logger

def perform_crawl_and_query(
    prompt: str,
    urls: Optional[List[str]] = None,
    strict: bool = False,
    n: int = 3,
    num_seed_urls: int = 5,
    max_depth: int = 5,
    force_crawl: bool = False,
    relevance_threshold: float = 0.5,
    use_llm: bool = False  # New parameter
) -> Dict:
    """
    Performs a complete crawl operation and returns query results.
    First tries to query existing vector store if available and force_crawl is False.
    
    Args:
        prompt (str): The user's query/prompt
        urls (Optional[List[str]]): Optional list of URLs to crawl
        strict (bool): Whether to only use provided URLs
        n (int): Number of results to return from query
        num_seed_urls (int): Number of seed urls to get back from the search results
        max_depth (int): Maximum crawl depth
        force_crawl (bool): Whether to force a new crawl instead of using existing vector store
        relevance_threshold (float): Minimum relevance score for results to be considered good enough
        use_llm (bool): Whether to generate an LLM response based on the results
        
    Returns:
        Dict containing:
        - status: Success/failure indication
        - results: List of relevant documents
        - llm_response: (Optional) Generated response from the LLM
        - metadata: Crawling statistics
        - from_cache: Whether results came from cached vector store
    """
    # Initialize crawler
    crawler = AdaptiveWebCrawler()
    
    try:
        # Create or load vector store
        crawler.create_vector_store()
        
        # Try to load existing vector store if not forcing a crawl or if strict url scraping mode is not enabled
        if not force_crawl and not strict:
            # Initialize logger
            logger = setup_logger()
            
            # Query existing vector store with strict flag
            results = crawler.query(prompt, n=n, strict=strict)
            
            # Check if results are good enough
            if results and all(r['score'] >= relevance_threshold for r in results):
                logger.info("Found relevant results in cached vector store")
                
                # Generate LLM response if requested
                llm_response = None
                if use_llm and results:
                    llm_response = generate_llm_response(results, prompt)
                
                response = {
                    "status": "success",
                    "results": results,
                    "metadata": {
                        "urls": {
                            "visited_this_run": 0,
                            "historical_total": len(crawler.visited_urls),
                            "seed_urls": 0,
                            "remaining": 0
                        },
                        "content_collected": 0,
                        "from_cache": True
                    }
                }
                
                if llm_response:
                    response["llm_response"] = llm_response
                    
                return response
            
            if not results:
                logger.info("No content in vector store, proceeding with new crawl")
            else:
                logger.info("Cached results not relevant enough, proceeding with new crawl")
        
        # Perform crawl
        crawler.crawl(
            prompt=prompt,
            urls=urls,
            strict=strict,
            num_results=n,
            num_seed_urls=num_seed_urls,
            max_depth=max_depth,
            base_relevance_threshold=relevance_threshold
        )
        
        # Query the vector store to get results
        results = crawler.query(prompt, n=n, strict=strict)
        
        # Generate LLM response if requested
        llm_response = None
        if use_llm and results:
            llm_response = generate_llm_response(results, prompt)
        
        # Prepare metadata about the crawl
        metadata = {
            "urls": {
                "visited_this_run": len([u for u in crawler.visited_urls if u in crawler.seed_urls]),
                "historical_total": len(crawler.visited_urls),
                "seed_urls": len(crawler.seed_urls),
                "remaining": len([u for u in crawler.seed_urls if u not in crawler.visited_urls])
            },
            "content_collected": len(crawler.content_store),
            "from_cache": False
        }
        
        response = {
            "status": "success",
            "results": results,
            "metadata": metadata
        }
        
        if llm_response:
            response["llm_response"] = llm_response
            
        return response
        
    except Exception as e:
        if 'logger' in locals():
            logger.error(f"Error in perform_crawl_and_query: {str(e)}")
        
        return {
            "status": "error",
            "error": str(e),
            "metadata": {
                "urls": {
                    "visited_this_run": 0,
                    "historical_total": 0,
                    "seed_urls": 0,
                    "remaining": 0
                },
                "content_collected": 0,
                "from_cache": False
            }
        }