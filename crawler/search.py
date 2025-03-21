from googlesearch import search as gsearch
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import urllib.parse
import time
import random

class BingSearch:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search(self, query, num_results=10):
        results = []
        query = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={query}&count={num_results}"
        
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for result in soup.find_all('li', class_='b_algo'):
                link = result.find('a')
                if link and 'href' in link.attrs:
                    url = link['href']
                    if url.startswith('http'):
                        results.append(url)
            
            time.sleep(random.uniform(1, 2))
            return results[:num_results]
        except Exception as e:
            print(f"Error in Bing search: {str(e)}")
            return []

def google_search(query, num_results=10):
    """
    Perform Google search using googlesearch-python library
    """
    try:
        results = list(gsearch(query, num_results=num_results))
        time.sleep(random.uniform(1, 2))  # Be nice to Google
        return results
    except Exception as e:
        print(f"Error in Google search: {str(e)}")
        return []

def duckduckgo_search(query, num_results=10):
    """
    Perform DuckDuckGo search using their API
    """
    try:
        # DuckDuckGo Instant Answer API
        url = f"https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': 1,
            'no_redirect': 1,
            'skip_disambig': 1
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        results = []
        
        # Extract results from API response
        if 'Results' in data:
            results.extend(result['FirstURL'] for result in data['Results'])
        if 'RelatedTopics' in data:
            results.extend(topic['FirstURL'] for topic in data['RelatedTopics'] 
                         if 'FirstURL' in topic)
            
        return results[:num_results]
    except Exception as e:
        print(f"Error in DuckDuckGo search: {str(e)}")
        return []

def perform_search(prompt, num_seed_urls=5):
    """
    Combine and rank search results from multiple search engines.
    Returns the top num_seed_urls results based on their presence across different engines.
    """
    # Get results from each search engine
    google_results = google_search(prompt, num_seed_urls * 2)
    bing_results = BingSearch().search(prompt, num_seed_urls * 2)
    ddg_results = duckduckgo_search(prompt, num_seed_urls * 2)
    
    # Count occurrences of each URL across search engines
    url_scores = defaultdict(int)
    
    for url in google_results:
        url_scores[url] += 3  # Weight Google results slightly higher
    
    for url in bing_results:
        url_scores[url] += 2
    
    for url in ddg_results:
        url_scores[url] += 2
    
    # Sort URLs by their scores
    ranked_results = sorted(url_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Return top num_seed_urls results
    return [url for url, score in ranked_results[:num_seed_urls]]