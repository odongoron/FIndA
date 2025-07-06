from .facebook import FacebookScraper
from .google import GoogleImageScraper
from .instagram import InstagramScraper
from .twitter import TwitterScraper
import logging

logger = logging.getLogger(__name__)

def get_scraper(platform_name):
    scrapers = {
        "facebook": FacebookScraper,
        "google": GoogleImageScraper,
        "instagram": InstagramScraper,
        "twitter": TwitterScraper
    }
    cls = scrapers.get(platform_name.lower())
    if not cls:
        logger.warning(f"No scraper found for platform '{platform_name}'")
        return None
    return cls()

