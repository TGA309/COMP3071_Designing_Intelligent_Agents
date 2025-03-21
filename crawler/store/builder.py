from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from config import config

def create_vector_store(content_store, embeddings, logger):
    """Create FAISS vector store from crawled content."""

    if config.store.VECTOR_STORE_DIR.exists() and (config.store.VECTOR_STORE_DIR / "index.faiss").exists():
        logger.info("Loading cached vector store...")
        vector_store = FAISS.load_local(str(config.store.VECTOR_STORE_DIR), embeddings, allow_dangerous_deserialization=True)
        return vector_store

    logger.info(f"Creating vector store from {len(content_store)} documents")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=config.store.CHUNK_SIZE, chunk_overlap=config.store.CHUNK_OVERLAP)
    
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
        vector_store.save_local(str(config.store.VECTOR_STORE_DIR))
    
    return vector_store

def update_vector_store(content_store, vector_store, embeddings):
    """Incrementally update the vector store with new content."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=config.store.CHUNK_SIZE, chunk_overlap=config.store.CHUNK_OVERLAP)
    
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
        
        vector_store.save_local(str(config.store.VECTOR_STORE_DIR))
    
    return vector_store