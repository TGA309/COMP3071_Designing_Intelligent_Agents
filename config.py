from pathlib import Path

class LoggerConfig:
    # Logging directory
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

class ModelConfig:
    # Model and caching settings
    MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
    dimension = 768 # 768 for all-mpnet-v2
    MODEL_CACHE_DIR = Path("models")
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

class StoreConfig:
    weights = {
        'faiss': 0.7,
        'cosine': 0.3
    }

    # Directories and paths for stores
    STATE_DIR = Path("crawler/states")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    
    VECTOR_STORE_DIR = STATE_DIR / "vector_store"
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # TFIDF_VECTOR_FILE = STATE_DIR / "tfidf_vectorizer.joblib"
    # TFIDF_MATRIX_FILE = STATE_DIR / "tfidf_matrix.joblib"

    # RecursiveCharacterTextSplitter parameters
    CHUNK_SIZE = 3000
    CHUNK_OVERLAP = 50

class CrawlerConfig:
    # Save frequency for saving crawler state
    save_frequency = 5

    # Top n results
    TOP_N_RESULTS = 5

class CrawlAPI:
    # Number of vector store results
    k_vector_store = 3

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