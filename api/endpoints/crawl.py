from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

class CrawlRequest(BaseModel):
    urls: Optional[List[str]] = None  # Optional list of URLs to crawl
    prompt: str = Field(..., alias="user_prompt")  # Accepts 'user_query'
    strict: bool = Field(False, alias="strict_flag")  # Accepts 'strict_flag'

@router.post("/", summary="Start a crawl operation", response_model=dict)
async def crawl_endpoint(request: CrawlRequest):
    """
    Initiates a crawl operation based on the provided parameters.
    
    - **urls**: Optional list of URLs to crawl.
    - **query**: Mandatory user query to search relevant content.
    - **strict**: Optional flag to force using only the provided URL(s).
    """
    urls = request.urls or []  # Ensure a list even if None
    user_prompt = request.prompt
    strict_flag = request.strict

    # For now, simply return the received values.
    # Replace this with a call to your backend logic as needed.
    return {
        "urls": urls,
        "prompt": user_prompt,
        "strict": strict_flag
    }