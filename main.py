from crawler import crawler
from crawler.config import seed_urls, max_pages
from fastapi import FastAPI
from api.router import api_router
import uvicorn

# Run the server with:
# uvicorn main:app --reload

if __name__ == "__main__":

    app = FastAPI()

    # Include the common API router with a global prefix, for example, /api
    app.include_router(api_router, prefix="/api")

    uvicorn.run(app, host="0.0.0.0", port=3000)

    # crawler = crawler.AdaptiveWebCrawler(seed_urls, max_pages=max_pages)
    # crawler.crawl()
    # crawler.create_vector_store()
    
    # # Example query
    # results = crawler.query("Break statement in NodeJS.")
    # for result in results:
    #     print(f"Source: {result['source']}")
    #     print(f"Score: {result['score']}")
    #     print(f"Content: {result['content']}...")
    #     print("-" * 80)