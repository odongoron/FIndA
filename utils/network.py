import yaml
import logging
import requests

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.proxies = self._load_proxies()
        self.current_index = 0
        
    def _load_proxies(self):
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config.get('proxies', [])
        except Exception as e:
            logger.error(f"Failed to load proxies: {str(e)}")
            return []
    
    def get_next_proxy(self):
        if not self.proxies:
            return None
            
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        # Format proxy for Selenium
        if 'username' in proxy and 'password' in proxy:
            return {
                'http': f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}",
                'https': f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
            }
        else:
            return {
                'http': f"http://{proxy['ip']}:{proxy['port']}",
                'https': f"http://{proxy['ip']}:{proxy['port']}"
            }
    
    def make_request(self, url, method='get', **kwargs):
        """Make a request using proxy rotation"""
        proxy = self.get_next_proxy()
        try:
            response = requests.request(
                method,
                url,
                proxies=proxy,
                timeout=10,
                **kwargs
            )
            return response
        except:
            # Rotate proxy and retry
            proxy = self.get_next_proxy()
            return requests.request(
                method,
                url,
                proxies=proxy,
                timeout=15,
                **kwargs
            )
