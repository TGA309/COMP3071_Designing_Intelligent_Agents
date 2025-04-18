# store/builder.py
"""
Functions to build and manage the in-memory content store during a crawl.
"""
from typing import List, Dict, Any
from crawler.logger import setup_logger

# In-memory store for crawled content
# Each item is a dictionary representing a processed page
_content_store: List[Dict[str, Any]] = []
logger = setup_logger()

def initialize_store(loaded_store: List[Dict[str, Any]]):
    """
    Initializes the content store, typically when loading saved state.

    Args:
        loaded_store: The content store loaded from persistence.
    """
    global _content_store
    _content_store = loaded_store
    logger.info(f"Initialized content store with {len(_content_store)} items.")

def add_content(content_item: Dict[str, Any]):
    """
    Adds a new content item (processed page data) to the store.

    Args:
        content_item: A dictionary containing extracted data for a URL.
                      Expected keys might include 'url', 'content', 'domain',
                      'publish_date', 'content_length', etc.
    """
    global _content_store
    if content_item and isinstance(content_item, dict) and 'url' in content_item:
        _content_store.append(content_item)
        # logger.debug(f"Added content for URL: {content_item['url']}") # Optional: debug logging
    else:
        logger.warning(f"Attempted to add invalid content item: {content_item}")

def get_content_store() -> List[Dict[str, Any]]:
    """
    Returns the current state of the content store.

    Returns:
        A list of dictionaries, where each dictionary is a crawled content item.
    """
    global _content_store
    return _content_store

def clear_content_store():
    """
    Clears the in-memory content store.
    """
    global _content_store
    _content_store = []
    logger.info("Content store cleared.")