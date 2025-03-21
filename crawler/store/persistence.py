import json
import datetime
import pickle
from langchain_community.vectorstores import FAISS
from config import config

def save_state(visited_urls, content_hashes, content_store, logger):
    """Save crawler state to disk."""
    state = {
        'visited_urls': list(visited_urls),
        'content_hashes': list(content_hashes),
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    with open(config.store.STATE_DIR / "state.json", "w") as f:
        json.dump(state, f, indent=4)
    
    # Save content_store
    with open(config.store.CONTENT_STORE_DIR / "content_store.pkl", "wb") as f:
        pickle.dump(content_store, f)
    
    logger.info("Crawler state and content store saved.")

def load_state(logger, embeddings):
    """Load previously saved crawler state, content store, and vector store if available."""
    visited_urls = set()
    content_hashes = set()
    content_store = []
    vector_store = None
    
    if config.store.STATE_DIR.exists() and (config.store.STATE_DIR / "state.json").exists():
        logger.info("Loading previous crawler state...")
        with open(config.store.STATE_DIR / "state.json", "r") as f:
            state = json.load(f)
        visited_urls = set(state['visited_urls'])
        content_hashes = set(state.get('content_hashes', []))  # Backward compatibility
        logger.info(f"Loaded state from: {state['timestamp']}")
    
    if config.store.CONTENT_STORE_DIR.exists() and (config.store.CONTENT_STORE_DIR / "content_store.pkl").exists():
        logger.info("Loading content store...")
        with open(config.store.CONTENT_STORE_DIR / "content_store.pkl", "rb") as f:
            content_store = pickle.load(f)
    
    if config.store.VECTOR_STORE_DIR.exists() and (config.store.VECTOR_STORE_DIR / "index.faiss").exists():
        logger.info("Loading existing vector store...")
        vector_store = FAISS.load_local(str(config.store.VECTOR_STORE_DIR), embeddings, allow_dangerous_deserialization=True)
    
    return visited_urls, content_hashes, content_store, vector_store
