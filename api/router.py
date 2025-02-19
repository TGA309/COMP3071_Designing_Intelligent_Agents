from fastapi import APIRouter
from api.endpoints.crawl import router as crawl_router

api_router = APIRouter()
# Include the crawl router with a prefix, so its endpoints become available at /crawl
api_router.include_router(crawl_router, prefix="/crawl", tags=["crawl"])