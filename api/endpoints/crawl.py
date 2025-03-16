from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional

# Import crawler
from crawler.crawl_query import perform_crawl_and_query

# Import config
from config import config

router = APIRouter()

class CrawlRequest(BaseModel):
    urls: Optional[List[str]] = None  # Optional list of URLs to crawl
    prompt: str = Field(..., alias="user_prompt")  # Accepts 'user_query'
    strict: bool = Field(False, alias="strict_flag")  # Accepts 'strict_flag'
    force_crawl: bool = Field(False, description="Force new crawl instead of using cached results")

@router.post("/", summary="Start a crawl operation", response_model=dict)
async def crawl_endpoint(request: CrawlRequest):
    """
    Initiates a crawl operation based on the provided parameters.
    
    - **urls**: Optional list of URLs to crawl
    - **prompt**: Mandatory user query to search relevant content
    - **strict**: Optional flag to force using only the provided URL(s)
    - **force_crawl**: Optional flag to force new crawl instead of using cached results
    """
    user_prompt = request.prompt
    urls = request.urls or []  # Ensure a list even if None
    strict_flag = request.strict
    force_crawl = request.force_crawl

    # Perform crawl and query
    crawl_response = perform_crawl_and_query(
        prompt=user_prompt,
        urls=urls,
        strict=strict_flag,
        k=config.api.crawl.k_vector_store,
        force_crawl=force_crawl,
        relevance_threshold=config.api.crawl.relevance_threshold
    )

    return crawl_response