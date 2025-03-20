# crawler/store/persistence.py
import json
import datetime
import hashlib
from langchain_community.vectorstores import FAISS
from config import config

def save_state(visited_urls, content_hashes, logger):
    """Save crawler state to disk."""
    state = {
        'visited_urls': list(visited_urls),
        'content_hashes': list(content_hashes),
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    with open(config.store.STATE_DIR / "state.json", "w") as f:
        json.dump(state, f, indent=4)
    logger.info("Crawler state saved.")

def load_state(logger, embeddings):
    """Load previously saved crawler state and vector store if available."""
    visited_urls = set()
    content_hashes = set()
    vector_store = None
    
    if config.store.STATE_DIR.exists() and (config.store.STATE_DIR / "state.json").exists():
        logger.info("Loading previous crawler state...")
        with open(config.store.STATE_DIR / "state.json", "r") as f:
            state = json.load(f)
        visited_urls = set(state['visited_urls'])
        content_hashes = set(state.get('content_hashes', []))  # Backward compatibility
        logger.info(f"Loaded state from: {state['timestamp']}")
    
    if config.store.VECTOR_STORE_DIR.exists() and (config.store.VECTOR_STORE_DIR / "index.faiss").exists():
        logger.info("Loading existing vector store...")
        vector_store = FAISS.load_local(str(config.store.VECTOR_STORE_DIR), embeddings, allow_dangerous_deserialization=True)
    
    return visited_urls, content_hashes, vector_store