# crawler/heuristics.py

import re
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
import hashlib

class ContentHeuristics:
    def __init__(self):
        self.content_hashes = set()
    
    def calculate_page_score(self, soup, url, prompt_keywords):
        """
        Calculate a relevance score for a page based on various heuristics.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page
            prompt_keywords: List of keywords from the user's prompt
            
        Returns:
            score: Float between 0 and 1 indicating relevance
            metadata: Dictionary with additional page metadata
        """
        score = 0
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc,
            'publish_date': None,
            'content_length': 0,
            'has_structured_content': False
        }
        
        # 1. Title relevance (0-0.2)
        title = soup.find('title')
        if title and title.text:
            title_text = title.text.lower()
            title_score = sum(1 for kw in prompt_keywords if kw.lower() in title_text) / max(1, len(prompt_keywords))
            score += title_score * 0.2
        
        # 2. Heading relevance (0-0.2)
        headings = soup.find_all(['h1', 'h2', 'h3'])
        if headings:
            heading_texts = [h.text.lower() for h in headings]
            heading_score = sum(1 for kw in prompt_keywords 
                              for h in heading_texts if kw.lower() in h) / (len(prompt_keywords) * len(headings))
            score += heading_score * 0.2
        
        # 3. Check for publish date (0-0.1)
        publish_date = self._extract_publish_date(soup)
        if publish_date:
            metadata['publish_date'] = publish_date
            # Give higher score to more recent content
            days_old = (datetime.now() - publish_date).days
            if days_old < 30:  # Published within last month
                score += 0.1
            elif days_old < 365:  # Published within last year
                score += 0.05
        
        # 4. Content length and structure (0-0.3)
        main_content = self._extract_main_content(soup)
        if main_content:
            word_count = len(main_content.split())
            metadata['content_length'] = word_count
            
            # Long-form content bonus
            if word_count > 1000:
                score += 0.15
            elif word_count > 500:
                score += 0.1
            elif word_count > 200:
                score += 0.05
            
            # Structured content bonus
            has_lists = len(soup.find_all(['ul', 'ol'])) > 0
            has_tables = len(soup.find_all('table')) > 0
            has_faq = self._has_faq_structure(soup)
            
            if has_lists or has_tables or has_faq:
                metadata['has_structured_content'] = True
                score += 0.15
        
        # 5. Ad/script density penalty (0-0.2)
        content_to_script_ratio = self._calculate_content_script_ratio(soup)
        if content_to_script_ratio > 0.8:  # More than 80% content vs scripts
            score += 0.2
        elif content_to_script_ratio > 0.5:  # More than 50% content
            score += 0.1
        
        return score, metadata
    
    def should_process_content(self, content, url):
        """
        Determine if content should be processed and added to the store.
        
        Args:
            content: Extracted text content
            url: Source URL
            
        Returns:
            bool: True if content should be processed, False otherwise
        """
        # Skip very short content
        if len(content.split()) < 200:
            return False
        
        # Check for duplicate content using hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if content_hash in self.content_hashes:
            return False
        
        # Add hash to the set
        self.content_hashes.add(content_hash)
        return True
    
    def _extract_publish_date(self, soup):
        """Extract publication date from page metadata."""
        # Try common meta tags for publication date
        for meta in soup.find_all('meta'):
            if meta.get('property') in ['article:published_time', 'og:published_time'] or \
               meta.get('name') in ['pubdate', 'publishdate', 'date']:
                try:
                    date_str = meta.get('content')
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    pass
        
        # Try looking for date in structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and 'datePublished' in data:
                    return datetime.fromisoformat(data['datePublished'].replace('Z', '+00:00'))
            except:
                pass
        
        return None
    
    def _extract_main_content(self, soup):
        """Extract the main content area of the page."""
        # Try common content containers
        for container in ['article', 'main', '[role=main]', '.content', '.post-content']:
            if container.startswith('.'):
                element = soup.find(class_=container[1:])
            elif container.startswith('['):
                attr, value = container[1:-1].split('=')
                element = soup.find(attrs={attr: value})
            else:
                element = soup.find(container)
            
            if element:
                return element.get_text(' ', strip=True)
        
        # Fallback to body
        body = soup.find('body')
        if body:
            return body.get_text(' ', strip=True)
        
        return ""
    
    def _has_faq_structure(self, soup):
        """Check if the page has FAQ-like structure."""
        # Look for FAQ schema
        for script in soup.find_all('script', type='application/ld+json'):
            if 'FAQPage' in script.text:
                return True
        
        # Look for Q&A pattern in headings followed by paragraphs
        q_patterns = [re.compile(r'^q:|^question:|^what|^how|^why|^when|^where', re.I)]
        
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            for pattern in q_patterns:
                if pattern.search(heading.text):
                    # Check if followed by paragraph
                    next_p = heading.find_next('p')
                    if next_p:
                        return True
        
        return False
    
    def _calculate_content_script_ratio(self, soup):
        """Calculate the ratio of content to scripts/ads."""
        # Remove all script, style, iframe elements
        soup_copy = BeautifulSoup(str(soup), 'html.parser')
        
        # Get original size
        original_size = len(str(soup_copy))
        
        # Remove potential ad and script elements
        for tag in soup_copy.find_all(['script', 'style', 'iframe', 'noscript']):
            tag.decompose()
        
        # Also remove common ad container classes
        for ad_class in ['ad', 'ads', 'advertisement', 'banner', 'sponsor']:
            for element in soup_copy.find_all(class_=lambda c: c and ad_class in c.lower()):
                element.decompose()
        
        # Get clean size
        clean_size = len(str(soup_copy))
        
        # Calculate ratio (avoid division by zero)
        return clean_size / original_size if original_size > 0 else 0