# store/persistence.py
"""
Functions to save and load the crawler's state.
This includes visited URLs, content hashes, and the content store itself.
"""
import pickle
from pathlib import Path
from typing import Set, List, Dict, Tuple, Any
import os

from config import config
from crawler.logger import setup_logger
from .builder import initialize_store, get_content_store # Import from builder

logger = setup_logger()

# Define file paths for saving state components
VISITED_URLS_FILE = config.store.STATE_DIR / "visited_urls.pkl"
CONTENT_HASHES_FILE = config.store.STATE_DIR / "content_hashes.pkl"
CONTENT_STORE_FILE = config.store.CONTENT_STORE_DIR / "content_store.pkl"

def save_state(visited_urls: Set[str], content_hashes: Set[str]):
    """
    Saves the current state of the crawler (visited URLs, content hashes, content store).

    Args:
        visited_urls: A set of URLs that have been visited.
        content_hashes: A set of hashes of content that has been processed to avoid duplicates.
    """
    try:
        # Ensure directories exist
        config.store.STATE_DIR.mkdir(parents=True, exist_ok=True)
        config.store.CONTENT_STORE_DIR.mkdir(parents=True, exist_ok=True)

        # Save visited URLs
        with open(VISITED_URLS_FILE, 'wb') as f:
            pickle.dump(visited_urls, f)
        logger.debug(f"Saved {len(visited_urls)} visited URLs to {VISITED_URLS_FILE}")

        # Save content hashes
        with open(CONTENT_HASHES_FILE, 'wb') as f:
            pickle.dump(content_hashes, f)
        logger.debug(f"Saved {len(content_hashes)} content hashes to {CONTENT_HASHES_FILE}")

        # Save content store (get it from the builder)
        content_store = get_content_store()
        with open(CONTENT_STORE_FILE, 'wb') as f:
            pickle.dump(content_store, f)
        logger.info(f"Saved {len(content_store)} content items to {CONTENT_STORE_FILE}")

    except Exception as e:
        logger.error(f"Error saving crawler state: {e}", exc_info=True)

def load_state() -> Tuple[Set[str], Set[str]]:
    """
    Loads the previously saved state of the crawler.

    If saved files don't exist, returns empty sets/lists.

    Returns:
        A tuple containing:
        - visited_urls: Set of previously visited URLs.
        - content_hashes: Set of previously processed content hashes.
    """
    visited_urls: Set[str] = set()
    content_hashes: Set[str] = set()
    loaded_content_store: List[Dict[str, Any]] = []

    try:
        # Load visited URLs
        if VISITED_URLS_FILE.exists():
            with open(VISITED_URLS_FILE, 'rb') as f:
                visited_urls = pickle.load(f)
            logger.info(f"Loaded {len(visited_urls)} visited URLs from {VISITED_URLS_FILE}")
        else:
            logger.info(f"Visited URLs file not found ({VISITED_URLS_FILE}), starting fresh.")

        # Load content hashes
        if CONTENT_HASHES_FILE.exists():
            with open(CONTENT_HASHES_FILE, 'rb') as f:
                content_hashes = pickle.load(f)
            logger.info(f"Loaded {len(content_hashes)} content hashes from {CONTENT_HASHES_FILE}")
        else:
            logger.info(f"Content hashes file not found ({CONTENT_HASHES_FILE}), starting fresh.")

        # Load content store
        if CONTENT_STORE_FILE.exists():
            with open(CONTENT_STORE_FILE, 'rb') as f:
                loaded_content_store = pickle.load(f)
            logger.info(f"Loaded {len(loaded_content_store)} content items from {CONTENT_STORE_FILE}")
            # Initialize the builder's store with loaded data
            initialize_store(loaded_content_store)
        else:
            logger.info(f"Content store file not found ({CONTENT_STORE_FILE}), starting fresh.")
            # Ensure builder's store is empty if no file found
            initialize_store([])

    except Exception as e:
        logger.error(f"Error loading crawler state: {e}. Starting with empty state.", exc_info=True)
        # Reset to empty state in case of partial load failure
        visited_urls, content_hashes = set(), set()
        initialize_store([]) # Ensure builder store is empty

    return visited_urls, content_hashes