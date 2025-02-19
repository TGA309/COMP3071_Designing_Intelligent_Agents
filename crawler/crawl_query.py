from typing import List, Dict, Optional
from crawler.crawler import AdaptiveWebCrawler
from crawler import store
from langchain_huggingface import HuggingFaceEmbeddings
from crawler.config import MODEL_NAME, MODEL_CACHE_DIR
from crawler.logger import setup_logger

def perform_crawl_and_query(
    prompt: str,
    urls: Optional[List[str]] = None,
    strict: bool = False,
    k: int = 3,
    force_crawl: bool = False,
    relevance_threshold: float = 0.7  # Adjust threshold as needed
) -> Dict:
    """
    Performs a complete crawl operation and returns query results.
    First tries to query existing vector store if available and force_crawl is False.
    
    Args:
        prompt (str): The user's query/prompt
        urls (Optional[List[str]]): Optional list of URLs to crawl
        strict (bool): Whether to only use provided URLs
        k (int): Number of results to return from query
        force_crawl (bool): Whether to force a new crawl instead of using existing vector store
        relevance_threshold (float): Minimum relevance score for results to be considered good enough
        
    Returns:
        Dict containing:
        - status: Success/failure indication
        - results: List of relevant documents
        - metadata: Crawling statistics
        - from_cache: Whether results came from cached vector store
    """
    try:
        
        # Initialize embeddings for vector store
        embeddings = HuggingFaceEmbeddings(
            model_name=str(MODEL_CACHE_DIR / MODEL_NAME.split('/')[-1]),
            cache_folder=str(MODEL_CACHE_DIR)
        )

        # Try to load existing vector store if not forcing a crawl
        if not force_crawl:

            # Initialize logger
            logger = setup_logger()

            _, vector_store = store.load_state(logger, embeddings)
            
            if vector_store is not None:
                logger.info("Querying existing vector store...")
                # Query existing vector store
                results = vector_store.similarity_search_with_relevance_scores(prompt, k=k)
                
                # Format results
                formatted_results = [{
                    'content': doc.page_content,
                    'source': doc.metadata['source'],
                    'domain': doc.metadata['domain'],
                    'score': score
                } for doc, score in results]
                
                # Check if results are good enough
                if formatted_results and all(r['score'] >= relevance_threshold for r in formatted_results):
                    logger.info("Found relevant results in cached vector store")
                    return {
                        "status": "success",
                        "results": formatted_results,
                        "metadata": {
                            "urls": {
                                "visited_this_run": 0,
                                "historical_total": 0,
                                "seed_urls": 0,
                                "remaining": 0
                            },
                            "content_collected": 0,
                            "from_cache": True
                        }
                    }
                logger.info("Cached results not relevant enough, proceeding with new crawl")
        
        # If we get here, either:
        # 1. force_crawl was True
        # 2. vector store didn't exist
        # 3. or results weren't good enough
        # So we proceed with normal crawl
        
        crawler = AdaptiveWebCrawler()
        
        # Perform crawl
        crawler.crawl(
            prompt=prompt,
            urls=urls,
            strict=strict
        )
        
        # Create vector store from crawled content
        crawler.create_vector_store()
        
        # Query the vector store
        results = crawler.query(prompt, k=k)
        
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
        
        return {
            "status": "success",
            "results": results,
            "metadata": metadata
        }
        
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