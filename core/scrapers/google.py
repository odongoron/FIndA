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
from utils.file_utils import FileUtils                        # UPDATED
from core.face_recognition import FaceEncoder

logger = logging.getLogger(__name__)

class GoogleImageScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url     = "https://images.google.com"
        self.face_encoder = FaceEncoder()

    def reverse_image_search(self, image_bytes, max_results=10):
        img_path = FileUtils.create_temp_file(image_bytes, suffix=".jpg")
        if not img_path:
            logger.error("Could not write temp image.")
            return []

        q_embs = self.face_encoder.encode_faces(image_bytes)
        q_emb  = q_embs[0] if q_embs else None
        q_hash = imagehash.phash(Image.open(BytesIO(image_bytes)))

        try:
            self.driver.get(self.base_url)
            time.sleep(random.uniform(1.0, 2.0))

            icon = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".ZaFQO"))
            )
            icon.click()
            time.sleep(random.uniform(0.5, 1.0))

            try:
                up_tab = WebDriverWait(self.driver,5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[text()='Upload an image']"))
                )
                up_tab.click()
                time.sleep(random.uniform(0.5,1.0))
            except:
                logger.debug("Google upload tab missing, continuing.")

            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input#awyMjb"))
            )
            file_input.send_keys(img_path)
            time.sleep(random.uniform(2.0,3.0))

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".isv-r"))
            )
            cards = self.driver.find_elements(By.CSS_SELECTOR, ".isv-r")[: max_results * 3]
            candidates = []

            for c in cards:
                try:
                    thumb_url = c.find_element(By.TAG_NAME, "img").get_attribute("src")
                    page_url  = c.find_element(By.CSS_SELECTOR, ".VFACy").get_attribute("href")

                    resp = requests.get(thumb_url, timeout=5)                       # UPDATED
                    ctype = resp.headers.get("Content-Type", "")                   # UPDATED
                    if resp.status_code != 200 or not ctype.startswith("image/"):  # UPDATED
                        logger.warning(f"Google thumb HTTP {resp.status_code} or non-image {ctype}")  # UPDATED
                        continue                                                   # UPDATED
                    if len(resp.content) < 1000:                                   # UPDATED
                        logger.warning("Google thumb too small, skipping")        # UPDATED
                        continue                                                   # UPDATED

                    try:
                        img = Image.open(BytesIO(resp.content)).convert("RGB")    # UPDATED
                    except Exception as e:
                        logger.error(f"PIL open failed on Google thumb: {e}")   # UPDATED
                        continue                                                  # UPDATED

                    if q_emb:
                        emb_list = self.face_encoder.encode_faces(resp.content)
                        if emb_list:
                            emb = emb_list[0]
                            sim = float((q_emb @ emb) /
                                        (np.linalg.norm(q_emb) * np.linalg.norm(emb)))
                        else:
                            raise ValueError("no face")
                    else:
                        raise ValueError("no face in query")

                except Exception:
                    try:
                        h    = imagehash.phash(img)
                        dist = q_hash - h
                        sim  = 1 - (dist / 64.0)
                    except Exception as e:
                        logger.debug(f"Google hash fallback error: {e}")
                        continue

                candidates.append({
                    "image_url": thumb_url,
                    "page_url" : page_url,
                    "similarity": sim,
                    "source": "google"
                })

            return sorted(candidates, key=lambda x: x["similarity"], reverse=True)[:max_results]

        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []

        finally:
            FileUtils.delete_file(img_path)

