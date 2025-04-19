# utils.py

import nltk
import os

_nltk_data_downloaded = False # Flag to ensure we only check/download once per run

def download_nltk_data_if_needed(packages: List[str] = ['punkt', 'stopwords', 'wordnet', 'omw-1.4']):
    """
    Checks if essential NLTK data packages are available and downloads them if missing.
    Should be called once, preferably near the start of your application or module import.

    Args:
        packages: A list of NLTK package IDs to check/download.
    """
    global _nltk_data_downloaded
    if _nltk_data_downloaded:
        # print("NLTK data check already performed.") # Debug print
        return

    print("Checking NLTK data dependencies...") # Inform user
    missing_packages = []
    for package in packages:
        try:
            # Check if the package resource can be found
            # Example: nltk.data.find('tokenizers/punkt') raises LookupError if not found
            if package == 'punkt':
                nltk.data.find('tokenizers/punkt')
            elif package == 'stopwords':
                nltk.data.find('corpora/stopwords')
            elif package == 'wordnet':
                nltk.data.find('corpora/wordnet')
            elif package == 'omw-1.4':
                nltk.data.find('corpora/omw-1.4')
            print(f"  - NLTK package '{package}' found.")
        except LookupError:
            print(f"  - NLTK package '{package}' not found.")
            missing_packages.append(package)
        except Exception as e:
             # Handle cases where NLTK data path might not even exist
             print(f"  - Error checking NLTK package '{package}': {e}. Attempting download.")
             if package not in missing_packages:
                missing_packages.append(package)

    if missing_packages:
        print(f"Attempting to download missing NLTK packages: {missing_packages}...")
        try:
            # Use quiet=True to minimize console output during download
            nltk.download(missing_packages, quiet=True)
            print("NLTK packages downloaded successfully.")
            # Verify again after download
            for pkg in missing_packages: nltk.data.find(...) 
        except Exception as e:
            print(f"\n{'='*20} NLTK Download Error {'='*20}")
            print(f"Failed to download NLTK data automatically: {e}")
            print("Please try running the following in a Python interpreter manually:")
            print("import nltk")
            for pkg_id in missing_packages:
                print(f"nltk.download('{pkg_id}')")
            print(f"{'='*59}\n")
            print(f"Required NLTK data could not be downloaded due to the following error: {e}.")
    else:
        print("All required NLTK data packages are available.")

    _nltk_data_downloaded = True # Mark check as performed

# Check nltk dependencies and download if needed
download_nltk_data_if_needed() 

"""
General utility functions for the crawler.
"""
import re
from typing import List, Optional, Set
from urllib.parse import urlparse
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

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

def extract_keywords(
    keyword_phrases: List[str],
    custom_stop_words: Optional[Set[str]] = None,
) -> List[str]:
    """
    Extracts unique, single-word keywords from a list of keyword phrases
    using NLTK for processing.

    Args:
        keyword_phrases: The list of keyword phrases (e.g., from Mistral AI).
        custom_stop_words: An optional set of additional words to ignore.
    Returns:
        A list of unique, single keywords suitable for heuristic matching.
    """
    if not keyword_phrases:
        return []

    # Combine all phrases into a single string for processing
    full_text = ' '.join(keyword_phrases)

    # Initialize NLTK components
    lemmatizer = WordNetLemmatizer()
    nltk_stop_words = set(stopwords.words('english'))
    if custom_stop_words:
        nltk_stop_words.update(custom_stop_words)

    # Tokenize the text
    words = word_tokenize(full_text.lower())

    # Lemmatize, remove punctuation, stop words, and short words
    keywords = set() # Use a set to automatically handle uniqueness
    for word in words:
        # Lemmatize (attempting noun and verb forms)
        lemma_n = lemmatizer.lemmatize(word, pos='n') # Try as noun
        lemma_v = lemmatizer.lemmatize(lemma_n, pos='v') # Try as verb
        
        # Basic checks: is alpha-numeric, not a stop word, length > 2
        if (lemma_v.isalnum() and 
            lemma_v not in nltk_stop_words and 
            len(lemma_v) > 2):
            keywords.add(lemma_v)

    # Convert set back to list
    final_keywords = list(keywords)

    # Return the unique keywords
    return final_keywords 

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

    # Join the quoted phrases with " OR "
    search_query = " OR ".join(quoted_keywords)

    return search_query

def format_keywords_for_store_query(keyword_list):
    cleaned_keywords = [kw.strip() for kw in keyword_list if kw.strip()]
    keyword_query_string = ' '.join(cleaned_keywords)
    return keyword_query_string