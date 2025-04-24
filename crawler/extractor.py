"""
Handles fetching HTML content and extracting relevant text, code, and metadata from it.
Uses readability-lxml for robust main content extraction.
"""
import requests
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import re
import json # For parsing LD+JSON

from crawler.logger import setup_logger
from .utils import clean_text # Use clean_text from utils

logger = setup_logger()

# --- Constants for Extraction ---
# Tags often containing code blocks
CODE_SELECTORS = ['pre', 'code', '.highlight', '.syntax', '.example-code', '[class*="language-"]']


def fetch_page(url: str, timeout: int = 10) -> Optional[Tuple[str, str]]:
    """
    Fetches the HTML content of a URL.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        A tuple (content, final_url) or None if fetching fails.
        final_url accounts for redirects.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # Check content type - only process HTML
        content_type = response.headers.get('content-type', '').lower()
        if 'html' not in content_type:
            logger.warning(f"Skipping non-HTML content at {url} (type: {content_type})")
            return None

        # Use apparent_encoding for robustness, fall back to utf-8
        encoding = response.apparent_encoding or 'utf-8'
        content = response.content.decode(encoding, errors='replace')

        return content, response.url # Return final URL after redirects

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}", exc_info=True)
        return None


def parse_and_extract(html_content: str, url: str) -> Optional[Dict[str, any]]:
    """
    Parses HTML using readability-lxml to extract main content and metadata.

    Args:
        html_content: The HTML string.
        url: The original URL (used for metadata and resolving links).

    Returns:
        A dictionary containing extracted data, or None if parsing fails
        or no significant content is found.
        Keys: 'url', 'domain', 'title', 'main_content', 'code_blocks',
              'publish_date', 'links', 'content_length'
    """
    try:
        doc = Document(html_content)
        title = doc.title()
        main_content_html = doc.summary() # Get the cleaned HTML of the main content
        domain = urlparse(url).netloc

        # --- Extract Text from Main Content ---
        # Parse the cleaned HTML fragment to get text
        soup_main = BeautifulSoup(main_content_html, 'html.parser')
        main_content_text = soup_main.get_text(separator='\n', strip=True)
        main_content_text_cleaned = clean_text(main_content_text) # Further clean (remove URLs etc.)

        if not main_content_text_cleaned or len(main_content_text_cleaned.split()) < 30:
             logger.info(f"Readability found no significant main content for {url}")
             return None

        # --- Metadata Extraction ---
        soup = BeautifulSoup(html_content, 'html.parser')
        publish_date = _extract_publish_date(soup) # Extract date from original page

        # --- Code Block Extraction ---
        # Extracting from original might be better if readability removes code blocks
        code_blocks = _extract_code_blocks(soup)

        # --- Link Extraction ---
        links = _extract_links(soup, url) # Extract links relative to the original URL

        # --- Assemble Result ---
        extracted_data = {
            'url': url,
            'domain': domain,
            'title': title,
            'main_content': main_content_text_cleaned,
            'code_blocks': code_blocks,
            'publish_date': publish_date,
            'links': links,
            'content_length': len(main_content_text_cleaned.split()), # Word count of cleaned text
        }

        return extracted_data

    except Exception as e:
        logger.error(f"Error parsing or extracting content from {url} using readability: {e}", exc_info=True)
        return None


# --- Helper Functions ---
def _extract_code_blocks(soup: BeautifulSoup) -> List[str]:
    """Extracts text content from code-related tags."""
    code_blocks = []
    for selector in CODE_SELECTORS:
        try:
            if selector.startswith('.'):
                 elements = soup.find_all(class_=selector[1:])
            elif selector.startswith('['):
                 match = re.match(r'\[([\w-]+)\*="([^"]+)"\]', selector)
                 if match:
                     attr, value_part = match.groups()
                     elements = soup.find_all(lambda tag: tag.has_attr(attr) and value_part in tag[attr])
                 else:
                     elements = []
            else: # Tag name
                elements = soup.find_all(selector)

            for element in elements:
                # Get text, preserving structure within the code block
                code = element.get_text(strip=False) # Keep internal whitespace
                if code:
                    code_blocks.append(code.strip()) # Strip leading/trailing only
        except Exception as e:
            logger.warning(f"Error extracting code with selector '{selector}': {e}")

    # Return deduplicated list
    return list(dict.fromkeys(code_blocks))


def _extract_publish_date(soup: BeautifulSoup) -> Optional[datetime]:
    """Extracts publication date from various common metadata locations."""
    date_str = None
    # 1. Common meta tags
    meta_selectors = {
        'property': ['article:published_time', 'og:published_time'],
        'name': ['pubdate', 'publishdate', 'date', 'dc.date.issued', 'dcterms.created']
    }
    for attr, names in meta_selectors.items():
        for name in names:
            meta = soup.find('meta', attrs={attr: name})
            if meta and meta.get('content'):
                date_str = meta['content']
                break
        if date_str: break

    # 2. Time tag
    if not date_str:
        time_tag = soup.find('time', attrs={'datetime': True})
        if time_tag:
            date_str = time_tag['datetime']

    # 3. Schema.org (JSON-LD)
    if not date_str:
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                # Look in common places within JSON-LD
                if isinstance(data, dict):
                    potential_dates = [
                        data.get('datePublished'),
                        data.get('uploadDate'), # Youtube/VideoObject
                        data.get('@graph', [{}])[0].get('datePublished') # Sometimes nested
                    ]
                    for potential_date in potential_dates:
                        if isinstance(potential_date, str):
                            date_str = potential_date
                            break
                elif isinstance(data, list): # Handle array of objects
                     for item in data:
                         if isinstance(item, dict) and item.get('datePublished'):
                             date_str = item['datePublished']
                             break
            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                logger.debug(f"Could not parse JSON-LD for date: {e}")
            if date_str: break

    # --- Parse the date string ---
    if date_str:
        try:
            # Handle ISO format with potential 'Z' or timezone offsets
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # Ensure timezone-aware (assume UTC if naive)
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                 logger.debug(f"Assuming UTC for naive datetime: {date_str}")
                 return dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse extracted date string '{date_str}': {e}")

    return None # No date found or parsed


def _extract_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Extracts absolute links from the page, staying within the same domain."""
    links = set() # Use set for automatic deduplication
    base_domain = urlparse(base_url).netloc

    for element in soup.find_all(['a', 'link'], href=True): # Include <link> tags too
        href = element['href']

        # Basic filtering
        if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')) or len(href) > 500:
            continue

        try:
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href.strip())
            parsed_absolute = urlparse(absolute_url)

            # Check scheme and domain
            if parsed_absolute.scheme in ['http', 'https'] and parsed_absolute.netloc == base_domain:
                # Optional: Normalize URL (remove fragment)
                normalized_url = parsed_absolute._replace(fragment="").geturl()
                links.add(normalized_url)

        except ValueError:
            logger.debug(f"Could not parse or join URL: base='{base_url}', href='{href}'")
        except Exception as e:
            logger.warning(f"Error processing link '{href}' on page {base_url}: {e}")

    return list(links)