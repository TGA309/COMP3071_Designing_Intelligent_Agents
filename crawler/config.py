from pathlib import Path

# Save frequency for saving crawler state
save_frequency = 5

# Top n results
TOP_N_RESULTS = 5

# Number of vector store results
k_vector_store = 3

# Relevance threshold for responses
relevance_threshold = 0.5

# Model and caching settings
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
MODEL_CACHE_DIR = Path("models")
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

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