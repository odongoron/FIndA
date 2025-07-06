import yaml
import logging
from concurrent.futures import ThreadPoolExecutor
from .face_recognition import FaceEncoder
from .scrapers import get_scraper

logger = logging.getLogger(__name__)

class FindASearch:
    def __init__(self, config_path="config/targets.yaml"):
        self.targets = self.load_config(config_path)
        self.face_encoder = FaceEncoder()
        
    def load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def search_by_face(self, image_bytes):
        """Search by face image"""
        embeddings = self.face_encoder.encode_faces(image_bytes)
        if not embeddings:
            logger.warning("No faces detected in the image")
            return []
        
        return self._search_platforms("reverse_image_search", embeddings[0])
    
    def search_by_name(self, name):
        """Search by name"""
        return self._search_platforms("name_search", name)
    
    def _search_platforms(self, method, data):
        """Search across all configured platforms"""
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            targets = self.targets["image_search_targets"] if method == "reverse_image_search" else self.targets["name_search_targets"]
            
            for target in targets:
                scraper = get_scraper(target)
                if scraper:
                    futures.append(executor.submit(
                        getattr(scraper, method),
                        data,
                        10  # Results per platform
                    ))
            
            for future in futures:
                try:
                    results.extend(future.result())
                except Exception as e:
                    logger.error(f"Search failed: {str(e)}")
        
        # Sort by similarity if available
        if results and "similarity" in results[0]:
            return sorted(results, key=lambda x: x["similarity"], reverse=True)
        return results
