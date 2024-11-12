import logging
import aiohttp
from aiohttp import BasicAuth
from typing import Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential
from config import Config

class BlogAPI:
    def __init__(self, site_url: str, username: str, password: str):
        self.site_url = site_url
        self.auth = BasicAuth(username, password)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
    
    @retry(stop=stop_after_attempt(Config.MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_posts(self, page: int = 1, per_page: int = 100) -> List[Dict]:
        """Fetch posts with embedded terms data."""
        # Update URL to include embedded terms and taxonomy data
        url = (f"{self.site_url}/wp-json/wp/v2/posts"  # Make sure to use the full API endpoint
               f"?page={page}&per_page={per_page}"
               f"&_embed=true"  # Request embedded data
               f"&_fields=id,date,title,content,_embedded"  # Specify fields we want
               f"&orderby=date&order=desc")  # Sort by date
        
        logging.debug(f"Fetching posts from URL: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, auth=self.auth, ssl=False) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch posts: {response.status}")
                
                posts = await response.json()
                total_posts = response.headers.get('X-WP-Total', 'unknown')
                total_pages = response.headers.get('X-WP-TotalPages', 'unknown')
                
                # Add debug logging for taxonomy data
                if posts and isinstance(posts, list) and len(posts) > 0:
                    sample_post = posts[0]
                    logging.debug(f"Sample post embedded data: {sample_post.get('_embedded', {}).keys()}")
                    logging.debug(f"Sample taxonomy data: {sample_post.get('_embedded', {}).get('wp:term', [])}")
                
                logging.info(f"Total posts: {total_posts}, Total pages: {total_pages}")
                return posts