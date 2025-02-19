from pathlib import Path

# Initial URLs for crawling
seed_urls = [
    "https://developer.mozilla.org/en-US/",
    "https://docs.python.org/3/"
]

# Maximum number of pages to crawl
max_pages = 100

# Save frequency for saving crawler state
save_frequency = 10

# Model and caching settings
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
MODEL_CACHE_DIR = Path("models")

# Logging directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# State directory
STATE_DIR = Path("crawler/crawler_state")
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Vector Store directory
VECTOR_STORE_DIR = Path("crawler/vector_store")
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

# RecursiveCharacterTextSplitter parameters
CHUNK_SIZE = 3000
CHUNK_OVERLAP = 50