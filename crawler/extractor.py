# crawler/extractor.py

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def extract_content(soup, url, pattern_memory, clean_text):
    """
    Extract relevant content using learned patterns.
    Removes unwanted elements and applies domain-specific extraction rules.
    """
    # Remove unwanted elements
    for element in soup.find_all(['script', 'style', 'nav', 'footer']):
        element.decompose()
        
    domain = urlparse(url).netloc
    
    # Get or create pattern for domain
    if domain not in pattern_memory:
        pattern_memory[domain] = {
            'content_tags': [
                'article', 'main', '.content', '.documentation', 
                '.article-content', '.post-content', '.markdown-body',
                '.technical-content', '.guide-content'
            ],
            'code_blocks': ['pre', 'code', '.highlight', '.syntax', '.example-code'],
            'headers': ['h1', 'h2', 'h3']
        }
    patterns = pattern_memory[domain]
    content_blocks = []
    
    # Extract main content
    for tag in patterns['content_tags']:
        if '.' in tag:
            tag_name, class_name = tag.split('.')
            if tag_name == '':
                elements = soup.find_all(class_=class_name)
            else:
                elements = soup.find_all(tag_name, class_=class_name)
        else:
            elements = soup.find_all(tag)
            
        for element in elements:
            text = clean_text(element.get_text(separator=' '))
            if len(text) > 50: # Ignore very short blocks
                content_blocks.append(text)
    
    # Fallback to main content areas if specific areas yielded nothing
    if not content_blocks:
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        if main_content:
            text = clean_text(main_content.get_text(separator=' '))
            content_blocks.append(text)
    
    # Extract code blocks
    code_blocks = []
    for tag in patterns['code_blocks']:
        elements = soup.find_all(tag)
        for element in elements:
            code = element.get_text(strip=True)
            if code and len(code) > 10: # Ignore very short code snippets
                code_blocks.append(code)
    
    return {
        'url': url,
        'content': ' '.join(content_blocks),
        'code_blocks': code_blocks,
        'domain': domain
    }

def update_patterns(successful_content, pattern_memory):
    """Update extraction patterns based on successful extractions."""
    domain = successful_content['domain']
    
    if len(successful_content['content']) > 100:
        pattern_memory[domain]['success_count'] = pattern_memory[domain].get('success_count', 0) + 1
