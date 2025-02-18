# crawler/store.py

import json
import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from .config import STATE_DIR, VECTOR_STORE_DIR

def save_state(visited_urls, logger):
    """Save crawler state to disk."""
    state = {
        'visited_urls': list(visited_urls),
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    with open(STATE_DIR / "state.json", "w") as f:
        json.dump(state, f, indent=4)
    
    logger.info("Crawler state saved.")

def load_state(logger, embeddings):
    """Load previously saved crawler state and vector store if available."""
    visited_urls = set()
    vector_store = None
    
    if STATE_DIR.exists() and (STATE_DIR / "state.json").exists():
        logger.info("\nLoading previous crawler state...")
        with open(STATE_DIR / "state.json", "r") as f:
            state = json.load(f)
            visited_urls = set(state['visited_urls'])
            logger.info(f"Loaded state from: {state['timestamp']}")
    
    if VECTOR_STORE_DIR.exists() and (VECTOR_STORE_DIR / "index.faiss").exists():
        logger.info("\nLoading existing vector store...")
        vector_store = FAISS.load_local(str(VECTOR_STORE_DIR), embeddings, allow_dangerous_deserialization=True)
    
    return visited_urls, vector_store

def create_vector_store(content_store, embeddings, logger):
    """Create FAISS vector store from crawled content."""

    if not content_store:
        logger.error("No content has been crawled yet!")
        return

    if VECTOR_STORE_DIR.exists():
        logger.info("Loading cached vector store...")
        vector_store = FAISS.load_local(str(VECTOR_STORE_DIR), embeddings, allow_dangerous_deserialization=True)
        return vector_store

    logger.info(f"Creating vector store from {len(content_store)} documents")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    
    documents = []
    for content in content_store:
        if content['content'].strip(): # Only process non-empty content
            chunks = text_splitter.split_text(content['content'])
            for chunk in chunks:
                documents.append({
                    'content': chunk,
                    'source': content['url'],
                    'domain': content['domain']
                })
    
    if not documents:
        logger.error("No valid documents to create vector store!")
        return None

    # Create vector store
    texts = [doc['content'] for doc in documents]
    metadatas = [{'source': doc['source'], 'domain': doc['domain']} for doc in documents]
    
    logger.info(f"Creating vector store with {len(texts)} text chunks")
    
    vector_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)

    if vector_store:
        logger.info("Saving vector store for future use...")
        vector_store.save_local(str(VECTOR_STORE_DIR))
    
    return vector_store

def update_vector_store(content_store, vector_store, embeddings, logger):
    """Incrementally update the vector store with new content."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    
    # Only process content not already in vector store
    processed_urls = set()
    if vector_store is not None:
        processed_urls = {doc.metadata['source'] for doc in vector_store.docstore._dict.values()}
    
    new_documents = [doc for doc in content_store if doc['url'] not in processed_urls]
    
    if not new_documents:
        return vector_store
        
    documents = []
    for content in new_documents:
        if content['content'].strip():
            chunks = text_splitter.split_text(content['content'])
            for chunk in chunks:
                documents.append({
                    'content': chunk,
                    'source': content['url'],
                    'domain': content['domain']
                })

    if documents:
        texts = [doc['content'] for doc in documents]
        metadatas = [{'source': doc['source'], 'domain': doc['domain']} for doc in documents]
        
        if vector_store is None:
            vector_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
        else:
            vector_store.add_texts(texts, metadatas)
        
        vector_store.save_local(VECTOR_STORE_DIR)
    
    return vector_store