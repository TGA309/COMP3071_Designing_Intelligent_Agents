# utils.py (Minor change: Added URL validation)
"""
General utility functions for the crawler.
"""
import re
from typing import List, Optional, Set
from urllib.parse import urlparse

def clean_text(text: str) -> str:
    """Clean extracted text content."""
    if not isinstance(text, str):
        return ""
    # Remove excessive whitespace (including newlines replaced by spaces)
    text = re.sub(r'\s+', ' ', text)
    # Remove URLs (simple version)
    text = re.sub(r'http[s]?://\S+', '', text)
    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
    # Optional: Remove non-alphanumeric characters (except spaces, basic punctuation)
    # text = re.sub(r'[^a-zA-Z0-9\s.,!?-]', '', text)
    return text.strip()

def is_valid_url(url: str) -> bool:
    """Checks if a string is a potentially valid HTTP/HTTPS URL."""
    if not isinstance(url, str):
        return False
    try:
        result = urlparse(url)
        # Check for scheme (http/https) and netloc (domain name)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except ValueError:
        return False

def extract_keywords(prompt: str, stop_words: Optional[Set[str]] = None, top_n: int = 10) -> List[str]:
    """
    Extracts potential keywords from a prompt string.
    Simple approach: lowercase, remove punctuation, split, remove stop words.

    Args:
        prompt: The input string (e.g., user query).
        stop_words: A set of words to ignore. Uses a default set if None.
        top_n: Maximum number of keywords to return.

    Returns:
        A list of keywords.
    """
    if stop_words is None:
        # Simple default stop word list
        stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
                     'be', 'been', 'being', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
                     'about', 'if', 'of', 'it', 'you', 'me', 'my', 'he', 'she', 'they',
                     'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
                     'how', 'when', 'where', 'why', 'i', 'we', 'do', 'does', 'did',
                     'will', 'can', 'could', 'should', 'would', 'so', 'then', 'just'}

    if not isinstance(prompt, str):
        return []

    # Lowercase and remove punctuation (keep alphanumeric and spaces)
    text = re.sub(r'[^\w\s]', '', prompt.lower())
    # Split into words
    words = text.split()
    # Filter stop words and short words
    keywords = [word for word in words if word not in stop_words and len(word) > 2]

    # Simple approach: return the first N unique keywords found
    # More advanced: could use TF-IDF on the prompt itself if part of a larger context,
    # or use part-of-speech tagging to prioritize nouns/verbs.
    seen = set()
    unique_keywords = [kw for kw in keywords if not (kw in seen or seen.add(kw))]

    return unique_keywords[:top_n]