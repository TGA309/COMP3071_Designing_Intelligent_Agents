# config.py (Refactored)

from pathlib import Path

class LoggerConfig:
    # Logging directory
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    # Logging level (e.g., 'INFO', 'DEBUG')
    LOG_LEVEL = 'INFO'

# Removed ModelConfig as embeddings are no longer used directly by the crawler

class StoreConfig:
    # Base directory for storing crawler state
    STATE_DIR = Path("crawler_state") # Renamed for clarity
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Directory specifically for the content store pickle file
    # Can be the same as STATE_DIR if preferred
    CONTENT_STORE_DIR = STATE_DIR / "content_store"
    CONTENT_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # Heuristic Score Weightage
    heuristic_score_weight = 0.6

    # Cosine Similarity Score Weightage
    cosine_similarity_score_weight = 0.4

class CrawlerConfig:
    # How often (in terms of depth levels) to save crawler state
    save_frequency = 3 # Save more frequently perhaps

    # Relevance threshold used during crawling to decide if results are good enough to stop
    # This applies to the weighted scores from the query() method
    minimum_relevance_threshold = 0.15 # Minimum score considered relevant

    # The amount by which the target relevance threshold decreases per crawl depth
    depth_relevance_step = 0.05

    # Maximum number of parallel workers for fetching/processing URLs
    max_parallel_requests = 8 # Increased slightly

    # Number of URLs to process in each parallel batch submission (doesn't limit total parallelism)
    batch_size = 20

class CrawlAPI:
    # Default number of results to return from the query() method
    num_results = 3

    # Maximum depth for crawling
    max_depth = 3 # Reduced default max depth

    # Default number of seed URLs to fetch from search engines if none provided
    num_seed_urls = 5

    # Force crawl flag
    force_crawl = False

    # Default relevance threshold to start crawl with (for depth 0)
    relevance_threshold = 0.4

class APIConfig:
    # Encapsulates API-level defaults for the crawl operation
    crawl = CrawlAPI

class Configuration:
    logger = LoggerConfig
    store = StoreConfig
    crawler = CrawlerConfig
    api = APIConfig

# Global config object
config = Configuration()

# --- Setup Logger based on Config ---
# This ensures the logger level is set according to the config file
import logging
from crawler.logger import setup_logger # Import setup_logger

logger = setup_logger() # Gets the singleton logger instance
log_level_map = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
logger.setLevel(log_level_map.get(config.logger.LOG_LEVEL.upper(), logging.INFO))
logger.info(f"Logger level set to: {config.logger.LOG_LEVEL}")
# --- End Logger Setup ---