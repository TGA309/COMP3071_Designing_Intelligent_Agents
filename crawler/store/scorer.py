"""
Functions to score content relevance based on TF-IDF and cosine similarity.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any
import numpy as np

from crawler.logger import setup_logger
from .builder import get_content_store # Import from builder

from config import config

logger = setup_logger()

def calculate_score(query: str, k: int = 3, weight_heuristic: float = config.store.heuristic_score_weight, 
                                  weight_cosine: float = config.store.cosine_similarity_score_weight) -> List[Dict[str, Any]]:
    """
    Performs a similarity search using TF-IDF and cosine similarity with weighted scoring.

    Args:
        query: The search query string.
        k: The number of top results to return.
        weight_heuristic: Weight for the heuristic score (default: 0.5).
        weight_cosine: Weight for the cosine similarity score (default: 0.5).

    Returns:
        A list of the top k content items (dictionaries), sorted by weighted relevance score,
        each augmented with 'cosine_similarity_score', 'heuristic_score', and 'weighted_score' keys.
        Returns empty list if store is empty.
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

        # Calculate cosine similarity between the query and all documents
        cosine_similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()

        # Ensure k is not larger than the number of documents
        num_docs = len(documents)
        actual_k = min(k, num_docs)
        if actual_k <= 0:
            return []

        # Get heuristic scores from content store items or default to 0
        heuristic_scores = [item.get('heuristic_score', 0.0) for item in content_store]
        
        # Calculate weighted scores
        weighted_scores = [weight_heuristic * h + weight_cosine * c 
                          for h, c in zip(heuristic_scores, cosine_similarities)]

        # Get indices of top k items by weighted score
        top_k_indices = np.argsort(weighted_scores)[::-1][:actual_k]

        # Create the results list
        results = []
        for i in top_k_indices:
            # Retrieve the original content item
            content_item = content_store[i].copy()  # Use copy to avoid modifying original store
            
            # Add scores to the result
            content_item['cosine_similarity_score'] = float(cosine_similarities[i])
            content_item['heuristic_score'] = float(heuristic_scores[i])
            content_item['weighted_score'] = float(weighted_scores[i])
            
            results.append(content_item)

        # Sort the final list by weighted score (descending)
        results.sort(key=lambda x: x['weighted_score'], reverse=True)

        return results

    except Exception as e:
        logger.error(f"Error during TF-IDF similarity search: {e}", exc_info=True)
        return []
