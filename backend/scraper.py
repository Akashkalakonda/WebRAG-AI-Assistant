import requests
from bs4 import BeautifulSoup
import logging
import os
from serpapi import GoogleSearch
from dotenv import load_dotenv
from random import choice

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()
SERPAPI_KEY = os.getenv('SERPAPI_KEY')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
]

def search_and_scrape(query, max_pages=5):
    try:
        if not SERPAPI_KEY:
            logger.error("SERPAPI_KEY not found in .env file")
            return []

        is_current_affairs = any(keyword in query.lower() for keyword in ["current affairs", "attack", "terror", "news", "2025"])
        refined_query = f"{query} news 2025" if is_current_affairs else query
        logger.info(f"Searching SerpAPI for query: {refined_query}")
        params = {
            'q': refined_query,
            'api_key': SERPAPI_KEY,
            'engine': 'google',
            'num': max_pages,
        }
        if is_current_affairs:
            params['tbm'] = 'nws'
        results = GoogleSearch(params).get_dict()
        organic_results = results.get('news_results' if is_current_affairs else 'organic_results', [])
        logger.debug(f"Found {len(organic_results)} results")

        all_content = []
        for result in organic_results[:max_pages]:
            url = result.get('link')
            title = result.get('title', url)
            logger.info(f"Scraping URL: {url}")
            try:
                headers = {
                    'User-Agent': choice(USER_AGENTS),
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Referer': 'https://www.google.com/'
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                paragraphs = soup.find_all('p')
                content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                if len(content) > 50:
                    logger.debug(f"Scraped {len(content)} characters from {url}")
                    all_content.append({"url": url, "title": title, "content": content})
                else:
                    logger.debug(f"Skipped {url}: insufficient content")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [403, 406, 422]:
                    logger.warning(f"{e.response.status_code} for {url}, retrying with alternative headers")
                    try:
                        alt_headers = {
                            'User-Agent': choice(USER_AGENTS),
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'Referer': 'https://www.google.com/'
                        }
                        response = requests.get(url, headers=alt_headers, timeout=10, allow_redirects=True)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.text, 'html.parser')
                        paragraphs = soup.find_all('p')
                        content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                        if len(content) > 50:
                            logger.debug(f"Scraped {len(content)} characters from {url} on retry")
                            all_content.append({"url": url, "title": title, "content": content})
                        else:
                            logger.debug(f"Skipped {url} on retry: insufficient content")
                    except Exception as retry_e:
                        logger.error(f"Error scraping {url} on retry: {str(retry_e)}")
                else:
                    logger.error(f"Error scraping {url}: {str(e)}")
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")

        # Fallback to Wikipedia for current affairs if insufficient content
        if is_current_affairs and sum(len(d["content"]) for d in all_content) < 1000:
            logger.info(f"Insufficient content scraped, falling back to Wikipedia for query: {query}")
            wiki_query = f"{query} site:wikipedia.org 2025" if "attack" in query.lower() or "terror" in query.lower() else f"{query} site:wikipedia.org"
            results = GoogleSearch({
                'q': wiki_query,
                'api_key': SERPAPI_KEY,
                'engine': 'google',
                'num': 1,
            }).get_dict()
            organic_results = results.get('organic_results', [])
            if organic_results:
                url = organic_results[0].get('link')
                logger.info(f"Scraping Wikipedia URL: {url}")
                try:
                    headers = {
                        'User-Agent': choice(USER_AGENTS),
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Referer': 'https://www.google.com/'
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    paragraphs = soup.find_all('p')
                    content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                    if len(content) > 50:
                        logger.debug(f"Scraped {len(content)} characters from {url}")
                        all_content.append({"url": url, "title": "Wikipedia", "content": content})
                except Exception as e:
                    logger.error(f"Error scraping Wikipedia {url}: {str(e)}")

        logger.debug(f"Collected {len(all_content)} documents")
        return all_content
    except Exception as e:
        logger.error(f"Error in search_and_scrape: {str(e)}")
        return []
