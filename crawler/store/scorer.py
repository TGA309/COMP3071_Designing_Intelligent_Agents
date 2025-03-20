# crawler/store/scorer.py
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from langchain.schema import Document

def tfidf_similarity_search(content_store, query, k=5):
    """
    Perform TF-IDF based cosine similarity search on content store.
    
    Args:
        content_store: List of content dictionaries
        query: Query string
        k: Number of results to return
        
    Returns:
        List of (Document, score) tuples
    """
    if not content_store:
        return []
    
    # Extract content from store
    texts = [item['content'] for item in content_store]
    
    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer(stop_words='english')
    
    # Add query to the corpus to vectorize everything together
    all_texts = texts + [query]
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    # Get the query vector (last row) and content vectors
    query_vector = tfidf_matrix[-1]
    content_vectors = tfidf_matrix[:-1]
    
    # Calculate cosine similarity
    similarities = cosine_similarity(query_vector, content_vectors).flatten()
    
    # Get top k indices
    top_indices = similarities.argsort()[-k:][::-1]
    
    # Create Document objects with metadata
    results = []
    for idx in top_indices:
        doc = Document(
            page_content=content_store[idx]['content'],
            metadata={
                'source': content_store[idx]['url'],
                'domain': content_store[idx]['domain'],
                'publish_date': content_store[idx].get('publish_date'),
                'content_length': content_store[idx].get('content_length', 0),
                'has_structured_content': content_store[idx].get('has_structured_content', False)
            }
        )
        results.append((doc, float(similarities[idx])))
    
    return results

def combine_search_results(faiss_results, tfidf_results, faiss_weight=0.7):
    """
    Combine results from FAISS and TF-IDF with weighted scoring.
    
    Args:
        faiss_results: List of (Document, score) tuples from FAISS
        tfidf_results: List of (Document, score) tuples from TF-IDF
        faiss_weight: Weight to give FAISS results (0-1)
        
    Returns:
        List of (Document, combined_score) tuples
    """
    tfidf_weight = 1.0 - faiss_weight
    
    # Create dictionaries to store scores by document source
    faiss_scores = {doc.metadata['source']: score for doc, score in faiss_results}
    tfidf_scores = {doc.metadata['source']: score for doc, score in tfidf_results}
    
    # Combine all unique documents
    all_docs = {}
    for doc, _ in faiss_results + tfidf_results:
        source = doc.metadata['source']
        if source not in all_docs:
            all_docs[source] = doc
    
    # Calculate combined scores
    combined_results = []
    for source, doc in all_docs.items():
        faiss_score = faiss_scores.get(source, 0.0)
        tfidf_score = tfidf_scores.get(source, 0.0)
        combined_score = (faiss_score * faiss_weight) + (tfidf_score * tfidf_weight)
        combined_results.append((doc, combined_score))
    
    # Sort by combined score
    return sorted(combined_results, key=lambda x: x[1], reverse=True)