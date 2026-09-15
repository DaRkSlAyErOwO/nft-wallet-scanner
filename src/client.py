import os
import time
import requests
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenSeaClient:
    """
    OpenSea API client.
    Handles rate limiting (HTTP 429), caching, and fetching logic.
    """
    def __init__(self, api_key: Optional[str] = None, min_delay_sec: int = 7):
        self.api_key = api_key or os.getenv("OPENSEA_API_KEY")
        self.min_delay_sec = min_delay_sec
        self.last_request_time = 0.0
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({"x-api-key": self.api_key})

    def _wait_for_rate_limit(self):
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_delay_sec:
            time.sleep(self.min_delay_sec - elapsed)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        max_retries = 6
        backoff = 2
        
        for attempt in range(max_retries):
            self._wait_for_rate_limit()
            
            try:
                # 30s timeout as requested
                response = self.session.request(method, url, timeout=30, **kwargs)
                self.last_request_time = time.time()
                
                if response.status_code in (401, 403):
                    raise RuntimeError("API key invalid or expired. Stopping batch.")
                
                if response.status_code == 429 or response.status_code >= 500:
                    retry_after = int(response.headers.get("Retry-After", backoff))
                    logger.warning(f"Rate limited or server error ({response.status_code}). Retrying in {retry_after}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_after)
                    backoff *= 2
                    continue
                    
                # Success or other client errors (404, etc.)
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request exception: {e}. Retrying... (Attempt {attempt+1}/{max_retries})")
                time.sleep(backoff)
                backoff *= 2
                
        raise Exception("Max retries exceeded for OpenSea API.")

    def get_collections(self, address: str) -> requests.Response:
        url = f"https://api.opensea.io/api/v2/account/{address}/collections?limit=50"
        return self._request("GET", url)

    def get_sales(self, address: str) -> requests.Response:
        url = f"https://api.opensea.io/api/v2/events/accounts/{address}?event_type=sale&limit=50"
        return self._request("GET", url)
