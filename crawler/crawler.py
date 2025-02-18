# crawler/crawler.py

import requests
import re
from pathlib import Path
from typing import List, Dict
import datetime
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from huggingface_hub import snapshot_download
from langchain_huggingface import HuggingFaceEmbeddings

# Import our modularized components and config
from crawler.config import save_frequency, MODEL_NAME, MODEL_CACHE_DIR
from crawler.logger import setup_logger
from crawler.utils import clean_text, is_relevant_url
from crawler import extractor, store


class AdaptiveWebCrawler:
    def __init__(self, seed_urls: List[str], max_pages: int = 100):
        self.seed_urls = seed_urls
        self.max_pages = max_pages
        self.visited_urls = set()
        self.content_store = []
        self.pattern_memory = {}
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.logger = setup_logger()
        
        # Setup model caching
        MODEL_CACHE_DIR.mkdir(exist_ok=True)
        
        model_path = MODEL_CACHE_DIR / MODEL_NAME.split('/')[-1]
        if not model_path.exists():
            self.logger.info(f"Downloading model {MODEL_NAME} for first time use...")
            snapshot_download(repo_id=MODEL_NAME, local_dir=str(model_path))
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=str(model_path),
            cache_folder=str(MODEL_CACHE_DIR)
        )
        
        self.vector_store = None

    def crawl(self):
        """Main crawling logic with adaptive behavior."""
        self.visited_urls, self.vector_store = store.load_state(self.logger, self.embeddings)
        
        # Filter out already visited URLs from initial URLs
        urls_to_visit = [url for url in self.seed_urls if url not in self.visited_urls]
        if not urls_to_visit:
            urls_to_visit = self.seed_urls.copy()
        
        self.logger.info(f"Starting crawl with {len(urls_to_visit)} unvisited URLs")
        
        docs_since_last_save = 0
        
        while urls_to_visit and len(self.visited_urls) < self.max_pages:
            url = urls_to_visit.pop(0)

            if url in self.visited_urls:
                continue
                
            try:
                self.logger.info(f"Attempting to crawl: {url}")
                response = requests.get(url, timeout=10)
                self.logger.info(f"Retrieved content from {url} (status: {response.status_code})")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                content = extractor.extract_content(soup, url, self.pattern_memory, clean_text, self.logger)
                
                self.logger.info(f"Extracted {len(content['content'])} characters of content")
                self.logger.info(f"Found {len(content['code_blocks'])} code blocks")
                
                if content['content'] and self.is_technical_content(content['content']):
                    self.logger.info("Content identified as technical")
                    self.content_store.append(content)
                    extractor.update_patterns(content, self.pattern_memory)
                    docs_since_last_save += 1
                    
                    # Get new links to visit
                    new_links = extractor.get_links(soup, url, is_relevant_url)
                    self.logger.info(f"Found {len(new_links)} new links")
                    new_urls = [link for link in new_links if link not in self.visited_urls]
                    urls_to_visit.extend(new_urls)
                    self.logger.info(f"Added {len(new_urls)} new URLs to visit")
                    self.logger.info(f"Remaining URLs to crawl: {len(urls_to_visit)}")
                    
                    # Save progress periodically
                    if docs_since_last_save >= save_frequency:
                        self.vector_store = store.update_vector_store(
                            self.content_store,
                            self.vector_store,
                            self.embeddings,
                            self.logger
                        )
                        store.save_state(self.visited_urls, self.logger)
                        docs_since_last_save = 0
                        self.logger.info("Saved current progress")
                else:
                    self.logger.info("Content not identified as technical")
                    if not content['content']:
                        self.logger.info("No content was extracted")
                    else:
                        self.logger.info(f"First 200 characters of content: {content['content'][:200]}")
                
                self.visited_urls.add(url)
                
            except Exception as e:
                self.logger.error(f"Error crawling {url}: {str(e)}")
                continue
            
            # Status update after each URL
            self.logger.info(f"\nCrawling Status:")
            self.logger.info(f"URLs visited: {len(self.visited_urls)}")
            self.logger.info(f"URLs remaining: {len(urls_to_visit)}")
            self.logger.info(f"Technical content collected: {len(self.content_store)} pages\n")

        # Final save
        if docs_since_last_save > 0:
            self.vector_store = store.update_vector_store(
                self.content_store,
                self.vector_store,
                self.embeddings,
                self.logger
            )
            store.save_state(self.visited_urls, self.logger)
        
        self.logger.info(f"Crawling complete. Visited {len(self.visited_urls)} pages")
        self.logger.info(f"Collected content from {len(self.content_store)} pages")

    def is_technical_content(self, text: str) -> bool:
        """
        Determine if content is technical using multiple heuristics.
        Returns True if content meets technical criteria.
        """
        if not text or len(text.strip()) < 100:
            return False

        text_lower = text.lower()
        
        programming_keywords = {
            'function', 'class', 'method', 'variable', 'object', 'array',
            'string', 'integer', 'boolean', 'null', 'undefined', 'return',
            'import', 'export', 'const', 'let', 'var', 'async', 'await'
        }
        
        technical_terms = {
            'algorithm', 'api', 'implementation', 'interface', 'parameter',
            'documentation', 'syntax', 'compiler', 'runtime', 'debug',
            'exception', 'framework', 'library', 'module', 'package'
        }
        
        languages_and_tools = {
            'javascript', 'python', 'java', 'typescript', 'html', 'css',
            'react', 'node', 'docker', 'git', 'sql', 'mongodb', 'api'
        }

        prog_count = sum(1 for word in programming_keywords if f" {word} " in f" {text_lower} ")
        tech_count = sum(1 for word in technical_terms if f" {word} " in f" {text_lower} ")
        tool_count = sum(1 for word in languages_and_tools if f" {word} " in f" {text_lower} ")
        
        code_indicators = [
            len(re.findall(r'[\(\);{}]', text)),
            len(re.findall(r'console\.|print\(|import\s+|from\s+.*\s+import', text_lower)),
            len(re.findall(r'`[^`]+`|```[^`]+```', text)),
            len(re.findall(r'<[^>]+>', text))
        ]
        
        keyword_score = (prog_count + tech_count + tool_count) / (len(text.split()) + 1)
        code_score = sum(code_indicators) / (len(text) + 1)
        
        self.logger.debug(f"Technical content scores - Keyword: {keyword_score:.4f}, Code: {code_score:.4f}")
        
        is_technical = (
            (keyword_score > 0.01 or code_score > 0.005) and
            any([
                prog_count >= 2,
                tech_count >= 2,
                tool_count >= 1,
                sum(code_indicators) >= 3
            ])
        )
        
        if is_technical:
            self.logger.info(
                f"Content identified as technical - Found {prog_count} programming keywords, "
                f"{tech_count} technical terms, {tool_count} tool references"
            )
        
        return is_technical

    def create_vector_store(self):
        """Create the FAISS vector store from crawled content."""
        self.vector_store = store.create_vector_store(self.content_store, self.embeddings, self.logger)

    def query(self, question: str, k: int = 3) -> List[Dict]:
        """Query the vector store for relevant content."""
        if not self.vector_store:
            raise ValueError("Vector store not created. Run create_vector_store() first.")
            
        results = self.vector_store.similarity_search_with_relevance_scores(question, k=k)
        
        return [{
            'content': doc.page_content,
            'source': doc.metadata['source'],
            'domain': doc.metadata['domain'],
            'score': score
        } for doc, score in results]