from crawler import crawler
from crawler.config import seed_urls, max_pages

if __name__ == "__main__":
    crawler = crawler.AdaptiveWebCrawler(seed_urls, max_pages=max_pages)
    crawler.crawl()
    crawler.create_vector_store()
    
    # Example query
    results = crawler.query("How do I handle async operations in JavaScript?")
    for result in results:
        print(f"Source: {result['source']}")
        print(f"Score: {result['score']}")
        print(f"Content: {result['content']}...")
        print("-" * 80)