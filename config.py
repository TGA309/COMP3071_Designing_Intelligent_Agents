from pathlib import Path

class LoggerConfig:
    # Logging directory
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

class ModelConfig:
    # Model and caching settings
    MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
    LLM_MODEL_NAME = "google/gemma-3-1b-it"
    dimension = 768 # 768 for all-mpnet-v2
    MODEL_CACHE_DIR = Path("models")
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

class StoreConfig:
    weights = {
        'faiss': 0.3
    }

    # Directories and paths for stores
    STATE_DIR = Path("crawler/states")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    
    VECTOR_STORE_DIR = STATE_DIR / "vector_store"
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    CONTENT_STORE_DIR = STATE_DIR / "content_store"
    CONTENT_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # RecursiveCharacterTextSplitter parameters
    CHUNK_SIZE = 3000
    CHUNK_OVERLAP = 50

class CrawlerConfig:
    # Save frequency for saving crawler state
    save_frequency = 5

    # Lowest amount of relevance threshold that any depth crawl can have
    minimum_relevance_threshold = 0.1

    # The amount by which the relevance threshold should be decreased each depth
    depth_relevance_step = 0.05
    
    # Minimum score for a URL to be considered 
    url_relevance_threshold = 0.3  

    # Maximum number of parallel workers we can have for depth crawling
    max_parallel_requests = 5

    # Batch size for parallel processing
    batch_size = 10

class CrawlAPI:

    # Strict flag
    strict_flag = False

    # Number of store results
    num_results = 3

    # Maximum depth for crawling
    max_depth = 5

    # Top n search results
    num_seed_urls = 5

    # Force crawl flag
    force_crawl = False

    # Relevance threshold for responses
    relevance_threshold = 0.5

class APIConfig:
    crawl = CrawlAPI

class Configuration:
    logger = LoggerConfig
    model = ModelConfig
    store = StoreConfig
    crawler = CrawlerConfig
    api = APIConfig

config = Configuration()