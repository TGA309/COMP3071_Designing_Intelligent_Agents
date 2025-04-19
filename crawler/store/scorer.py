# store/scorer.py
"""
Functions to score content relevance based on TF-IDF and cosine similarity.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any
import numpy as np

from crawler.logger import setup_logger
from .builder import get_content_store # Import from builder

logger = setup_logger()

# Initialize TF-IDF vectorizer globally or within the function as needed
# Global initialization might be slightly more efficient if called repeatedly
# with the same corpus, but requires managing its state if the corpus changes.
# Let's initialize it within the function for simplicity and to ensure it always
# fits the current content store.

def tfidf_similarity_search(query: str, k: int = 3) -> List[Dict[str, Any]]:
    """
    Performs a similarity search using TF-IDF and cosine similarity.

    Args:
        query: The search query string.
        k: The number of top results to return.

    Returns:
        A list of the top k content items (dictionaries), sorted by relevance score,
        each augmented with a 'score' key. Returns empty list if store is empty.
    """
    content_store = get_content_store()

    if not content_store:
        logger.warning("Attempted TF-IDF search on an empty content store.")
        return []

    try:
        # Extract the text content from each item in the store
        documents = [item.get('main_content', '') for item in content_store]

        # Ensure there's actual text content to process
        if not any(documents):
            logger.warning("Content store contains items but no text content found for TF-IDF (checked key 'main_content').")
            return []

        # Initialize and fit the TF-IDF vectorizer
        vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)
        tfidf_matrix = vectorizer.fit_transform(documents)

        # Transform the query using the same vectorizer
        query_vector = vectorizer.transform([query])

        print(query_vector)

        # Calculate cosine similarity between the query and all documents
        cosine_similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()

        # Get the indices of the top k documents, sorted by similarity score
        # Ensure k is not larger than the number of documents
        num_docs = len(documents)
        actual_k = min(k, num_docs)
        if actual_k <= 0:
            return []

        # Use argpartition for efficiency if k is much smaller than num_docs,
        # otherwise argsort is fine. Let's use argsort for simplicity here.
        # Get indices sorted by score in descending order
        top_k_indices = np.argsort(cosine_similarities)[::-1][:actual_k]

        # Create the results list
        results = []
        for i in top_k_indices:
            score = cosine_similarities[i]
            # Retrieve the original content item
            content_item = content_store[i].copy() # Use copy to avoid modifying original store
            content_item['score'] = float(score) # Add the score
            results.append(content_item)

        # Sort the final list by score (descending) - argsort might not guarantee order for same scores
        results.sort(key=lambda x: x['score'], reverse=True)

        return results

    except Exception as e:
        logger.error(f"Error during TF-IDF similarity search: {e}", exc_info=True)
        return []