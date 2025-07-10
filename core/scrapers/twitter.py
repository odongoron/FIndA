import os
import time
import random
import logging
import requests
import numpy as np
import imagehash

from io import BytesIO                                       # UPDATED
from PIL import Image                                        # UPDATED
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_scraper import BaseScraper
from core.face_recognition import FaceEncoder

logger = logging.getLogger(__name__)

class TwitterScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.requires_login = False
        self.base_url      = "https://twitter.com/search"
        self.face_encoder  = FaceEncoder()

    def reverse_image_search(self, image_bytes, max_results=10):
        q_embs = self.face_encoder.encode_faces(image_bytes)
        q_emb  = q_embs[0] if q_embs else None
        q_hash = imagehash.phash(Image.open(BytesIO(image_bytes)))

        url = f"{self.base_url}?q=&src=typed_query&f=user"
        self.driver.get(url)
        self._human_delay()

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-testid='UserCell']"))
            )
        except Exception as e:
            logger.error(f"Twitter cells load failed: {e}")
            return []

        cells = self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='UserCell']")[: max_results * 3]
        candidates = []

        for cell in cells:
            try:
                link    = cell.find_element(By.TAG_NAME, "a").get_attribute("href")
                img_url = cell.find_element(By.TAG_NAME, "img").get_attribute("src")

                resp = requests.get(img_url, timeout=5)                         # UPDATED
                ctype = resp.headers.get("Content-Type", "")                   # UPDATED
                if resp.status_code != 200 or not ctype.startswith("image/"):  # UPDATED
                    logger.warning(f"TW avatar HTTP {resp.status_code} or non-image {ctype}") # UPDATED
                    continue                                                   # UPDATED
                if len(resp.content) < 1000:                                   # UPDATED
                    logger.warning("TW avatar too small, skipping")           # UPDATED
                    continue                                                   # UPDATED

                try:
                    avatar = Image.open(BytesIO(resp.content)).convert("RGB")  # UPDATED
                except Exception as e:
                    logger.error(f"PIL open failed on TW avatar: {e}")       # UPDATED
                    continue                                                  # UPDATED

                if q_emb:
                    emb_list = self.face_encoder.encode_faces(resp.content)
                    if emb_list:
                        emb = emb_list[0]
                        sim = float((q_emb @ emb) /
                                    (np.linalg.norm(q_emb) * np.linalg.norm(emb)))
                    else:
                        raise ValueError("no face in avatar")
                else:
                    raise ValueError("no face in query")

            except Exception:
                try:
                    h    = imagehash.phash(avatar)
                    dist = q_hash - h
                    sim  = 1 - (dist / 64.0)
                except Exception as e:
                    logger.debug(f"TW hash fallback error: {e}")
                    continue

            candidates.append({"url": link, "similarity": sim, "source": "twitter"})

        return sorted(candidates, key=lambda x: x["similarity"], reverse=True)[:max_results]

    # name_search unchanged


    def name_search(self, name, max_results=10):
        """Name-based search on Twitter."""
        logger.debug(f"Starting Twitter name search for '{name}'")  # UPDATED
        url = f"{self.base_url}?q={name}&src=typed_query&f=user"
        self.driver.get(url)
        self._human_delay()                              # UPDATED

        # Wait for search results
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-testid='UserCell']"))
            )
        except Exception as e:
            logger.error(f"Twitter name search results did not load: {e}")  # UPDATED
            return []

        # Scroll to get more
        for _ in range(1):
            self.driver.execute_script("window.scrollBy(0,document.body.scrollHeight);")
            self._human_delay(0.5, 1.0)                   # UPDATED

        cells = self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='UserCell']")[: max_results]
        results = []
        for cell in cells:
            try:
                uname = cell.find_element(By.CSS_SELECTOR, "div[dir='ltr']").text.strip("@")
                disp  = cell.find_element(By.CSS_SELECTOR, "div[dir='auto']").text
                results.append({
                    "url": f"https://twitter.com/{uname}",
                    "username": f"@{uname}",
                    "name": disp,
                    "source": "twitter"
                })
            except Exception as e:
                logger.debug(f"TW name parse error: {e}")  # UPDATED

        return results

    def _human_delay(self, a=1.0, b=2.0):
        """Sleep a random interval to mimic human behavior."""
        time.sleep(random.uniform(a, b))                # UPDATED

