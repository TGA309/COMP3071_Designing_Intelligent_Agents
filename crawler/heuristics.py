# heuristics.py (Refactored)
"""
Calculates relevance scores for web pages based on extracted content and metadata.
Relies on data provided by the extractor module.
"""
import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse, unquote

from crawler.logger import setup_logger

logger = setup_logger()

class ContentHeuristics:
    def __init__(self):
        # Set of content hashes to detect duplicates across the crawl session
        self.content_hashes: Set[str] = set()

    def load_hashes(self, hashes: Set[str]):
        """Loads pre-existing content hashes (e.g., from a previous run)."""
        self.content_hashes = hashes
        logger.info(f"Loaded {len(self.content_hashes)} existing content hashes.")

    def calculate_page_score(self, extracted_data: Dict, prompt_keywords: List[str]) -> float:
        """
        Calculates a relevance score (0-1) for a page based on extracted data
        and its relation to the prompt keywords.

        Args:
            extracted_data: Dictionary returned by the extractor module.
                            Expected keys: 'title', 'main_content', 'publish_date',
                                           'content_length', 'url'.
            prompt_keywords: List of keywords derived from the user's search prompt.

        Returns:
            A float score between 0 and 1.
        """
        if not extracted_data or not prompt_keywords:
            return 0.0

        score = 0.0
        title = extracted_data.get('title', '').lower()
        content = extracted_data.get('main_content', '').lower()
        publish_date = extracted_data.get('publish_date') # datetime object or None
        content_length = extracted_data.get('content_length', 0) # word count

        # --- Heuristic Components (Weights can be tuned) ---

        # 1. Keyword Density in Title (Weight: 0.3)
        title_matches = sum(1 for kw in prompt_keywords if kw.lower() in title)
        # Normalize score based on number of keywords, prevent division by zero
        title_score = (title_matches / len(prompt_keywords)) if prompt_keywords else 0
        score += title_score * 0.3
        # logger.debug(f"URL: {extracted_data.get('url')} - Title Score: {title_score:.2f}")

        # 2. Keyword Density in Content (Weight: 0.4)
        # Consider using TF-IDF or BM25 here for better scoring, but simple density for now
        content_matches = sum(1 for kw in prompt_keywords if kw.lower() in content)
        # Normalize by content length and number of keywords to avoid bias towards long documents
        # Add epsilon to avoid division by zero for length
        density_score = (content_matches / (content_length + 1e-6)) / len(prompt_keywords) if prompt_keywords else 0
        # Apply a non-linear scaling (e.g., sqrt) to dampen extreme density values
        # Cap the contribution to avoid overly dominant content score
        content_score = min( (density_score * 1000)**0.5, 1.0) # Scaled and capped at 1.0
        score += content_score * 0.4
        # logger.debug(f"URL: {extracted_data.get('url')} - Content Score: {content_score:.2f} (Matches: {content_matches}, Length: {content_length})")


        # 3. Content Freshness (Weight: 0.15)
        if publish_date:
            # Ensure publish_date is timezone-aware for correct comparison
            if publish_date.tzinfo is None or publish_date.tzinfo.utcoffset(publish_date) is None:
                 aware_publish_date = publish_date.replace(tzinfo=timezone.utc)
            else:
                 aware_publish_date = publish_date

            now = datetime.now(timezone.utc) # Use timezone-aware current time
            days_old = (now - aware_publish_date).days

            if days_old is not None and days_old >= 0: # Check for valid date difference
                if days_old < 30:  # Published within last month
                    score += 0.15
                elif days_old < 180: # Published within last 6 months
                    score += 0.10
                elif days_old < 365: # Published within last year
                    score += 0.05
                # Older content gets no bonus score from freshness
                # logger.debug(f"URL: {extracted_data.get('url')} - Freshness Score: Added based on {days_old} days old")


        # 4. Content Length Bonus (Weight: 0.15) - Reward substantial content
        if content_length > 1500: # Very substantial
            score += 0.15
        elif content_length > 750: # Substantial
            score += 0.10
        elif content_length > 300: # Moderate
            score += 0.05
        # logger.debug(f"URL: {extracted_data.get('url')} - Length Bonus: Added based on {content_length} words")


        # --- Penalty (Example - could add more) ---
        # Simple penalty for very short titles (might indicate low quality/placeholder)
        if len(title) < 10:
            score *= 0.9 # Reduce score by 10%


        # Ensure score is within [0, 1]
        final_score = max(0.0, min(score, 1.0))
        # logger.info(f"URL: {extracted_data.get('url')} - Final Heuristic Score: {final_score:.3f}")
        return final_score


    def should_process_content(self, content_text: str, url: str) -> bool:
        """
        Determines if the extracted content is worth adding to the store,
        primarily by checking for duplicates using content hashing.

        Args:
            content_text: The main extracted text content.
            url: The source URL (for logging).

        Returns:
            True if the content is not a duplicate and meets basic criteria, False otherwise.
        """
        # Basic check: Ensure content is not empty or just whitespace
        if not content_text or content_text.isspace():
            logger.debug(f"Skipping empty content from {url}")
            return False

        # Check for duplicate content using hash
        # Use a consistent encoding like utf-8
        try:
            content_hash = hashlib.sha256(content_text.encode('utf-8', errors='replace')).hexdigest()
            if content_hash in self.content_hashes:
                logger.info(f"Skipping duplicate content detected by hash from {url}")
                return False
            else:
                # Add hash to the set for future checks *only if* we decide to process
                # We'll add it just before returning True
                pass
        except Exception as e:
            logger.error(f"Error generating content hash for {url}: {e}")
            return False # Don't process if hashing fails

        # Add other simple checks if needed (e.g., minimum meaningful word count)
        # if len(content_text.split()) < 50:
        #     logger.info(f"Skipping content from {url} due to short length (< 50 words)")
        #     return False

        # If all checks pass, add the hash and return True
        self.content_hashes.add(content_hash)
        return True
    
class URLHeuristics:
    """
    Selects URLs based on relevance to prompt keywords found within the URL string itself.
    """
    def __init__(self, prompt_keywords: List[str]):
        """
        Initializes the URL heuristics with the target keywords.

        Args:
            prompt_keywords: A list of keywords derived from the user's prompt.
        """
        self.prompt_keywords = [kw.lower() for kw in prompt_keywords]
        self.min_keyword_matches = 1 # Minimum number of keywords needed in URL to be considered
        logger.info(f"URLHeuristics initialized with keywords: {self.prompt_keywords}")

    def _url_contains_keywords(self, url: str) -> bool:
        """Checks if the decoded URL path/query contains any prompt keywords."""
        if not self.prompt_keywords:
            return True # If no keywords, don't filter based on URL

        try:
            parsed = urlparse(url)
            # Decode URL encoding (%20 -> space, etc.) and convert to lowercase
            path_query = unquote(parsed.path + '?' + parsed.query).lower()
            # Simple check: count occurrences of keywords in the path and query
            matches = sum(1 for kw in self.prompt_keywords if kw in path_query)
            return matches >= self.min_keyword_matches
        except Exception as e:
            logger.warning(f"Could not parse or check keywords in URL {url}: {e}")
            return False # Treat errors as non-matches

    def select_best_urls(self, urls: List[str]) -> List[str]:
        """
        Filters a list of URLs, returning only those likely relevant based on keywords.

        Args:
            urls: A list of URLs to filter.

        Returns:
            A list containing only the URLs deemed relevant.
        """
        if not urls:
            return []

        selected_urls = [url for url in urls if self._url_contains_keywords(url)]
        logger.info(f"URL Heuristics: Selected {len(selected_urls)} out of {len(urls)} URLs based on keywords.")
        if len(urls) > 0 and len(selected_urls) < len(urls):
             logger.debug(f"URLs filtered out by keywords: {set(urls) - set(selected_urls)}")
        return selected_urls