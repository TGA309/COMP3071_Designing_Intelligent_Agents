# utils.py

import nltk
nltk.download('punkt') # For tokenization
nltk.download('punkt_tab')
nltk.download('stopwords') # For stop word removal
nltk.download('wordnet') # For lemmatization
nltk.download('omw-1.4') # For wordnet multilingual data

import re
from typing import List, Optional, Set
from urllib.parse import urlparse
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer, PorterStemmer
from nltk.tokenize import word_tokenize

"""
General utility functions for the crawler.
"""

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
    
def strip_and_join_with_spaces(keyword_list):
    cleaned_keywords = [kw.strip() for kw in keyword_list if kw.strip()]
    keyword_query_string = ' '.join(cleaned_keywords)
    return keyword_query_string

def extract_keywords(
    keyword_phrases: List[str],
    custom_stop_words: Optional[Set[str]] = None
) -> List[str]:
    """
    Extracts unique keywords from a list of keyword phrases
    using NLTK for processing.

    Args:
        keyword_phrases: The list of keyword phrases (e.g., from Mistral AI).
        custom_stop_words: An optional set of additional words to ignore.
    Returns:
        A list of unique keywords suitable for URL matching.
    """
    if not keyword_phrases:
        return []

    # Combine all phrases into a single string for processing
    full_text = strip_and_join_with_spaces(keyword_phrases)

    # Initialize NLTK components
    lemmatizer = WordNetLemmatizer()
    nltk_stop_words = set(stopwords.words('english'))
    if custom_stop_words:
        nltk_stop_words.update(custom_stop_words)

    # Tokenize the text
    words = word_tokenize(full_text.lower())

    # Process words with multiple techniques
    keywords = set()  # Use a set to automatically handle uniqueness
    for word in words:
        # Skip non-alphanumeric, stop words, and very short words
        if not word.isalnum() or word in nltk_stop_words or len(word) <= 2:
            continue
            
        # Add original word
        keywords.add(word)
            
        # Add lemmatized forms for all parts of speech
        for pos in ['n', 'v', 'a', 'r']:  # noun, verb, adjective, adverb
            lemma = lemmatizer.lemmatize(word, pos=pos)
            if lemma.isalnum() and len(lemma) > 2:
                keywords.add(lemma)

    # Convert set back to list
    return list(keywords)


def format_keywords_for_search(keyword_list):
    """
    Formats a list of keyword phrases into a single search engine query string.

    Args:
    keyword_list: A list of strings, where each string is a keyword phrase.

    Returns:
    A single string formatted for search engines, with phrases quoted
    and joined by " OR ", or an empty string if the input list is empty.
    """
    if not keyword_list:
        return ""

    quoted_keywords = [f'"{keyword}"' for keyword in keyword_list]

    # Join the quoted phrases with " + "
    search_query = " + ".join(quoted_keywords)

    return search_query