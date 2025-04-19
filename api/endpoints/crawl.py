from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional

# Import crawler
from crawler.crawl_query import perform_crawl_and_query

# Import config
from config import config

router = APIRouter()

class CrawlRequest(BaseModel):
    user_prompt: str = Field(..., description="The user's query or prompt for the crawl operation")
    urls: Optional[List[str]] = Field(None, description="Optional list of URLs to crawl")
    num_results: int = Field(config.api.crawl.num_results, description="Number of results to return from the query")
    max_depth: int = Field(config.api.crawl.max_depth, description="Maximum depth for the crawl operation")
    num_seed_urls: int = Field(config.api.crawl.num_seed_urls, description="Number of seed URLs to use for crawling")
    force_crawl_flag: bool = Field(config.api.crawl.force_crawl, description="Force new crawl instead of using cached results")
    relevance_threshold: float = Field(config.api.crawl.relevance_threshold, description="Minimum relevance score for results to be considered")
    use_llm_flag: bool = Field(False, description="Whether to generate an LLM response based on the results")

@router.post("/", summary="Start a crawl operation", response_model=dict)
async def crawl_endpoint(request: CrawlRequest):
    """
    Initiates a crawl operation based on the provided parameters.
    
    - **prompt**: Mandatory user query to search relevant content
    - **urls**: Optional list of URLs to crawl
    - **num_results**: Number of results to return from the query
    - **max_depth**: Maximum depth for the crawl operation
    - **num_seed_urls**: Number of seed URLs to use for crawling
    - **force_crawl_flag**: Optional flag to force new crawl instead of using cached results
    - **relevance_threshold**: Minimum relevance score for results to be considered
    - **use_llm_flag**: Whether to generate an LLM response based on the results
    """

    # Perform crawl and query
    crawl_response = perform_crawl_and_query(
        prompt=request.user_prompt,
        urls=request.urls,
        n=request.num_results,
        max_depth=request.max_depth,
        num_seed_urls=request.num_seed_urls,
        force_crawl=request.force_crawl_flag,
        relevance_threshold=request.relevance_threshold,
        use_llm_response=request.use_llm_flag
    )

    return crawl_response