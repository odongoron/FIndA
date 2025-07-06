import os, time, random, logging, requests
import numpy as np, imagehash
from io import BytesIO
from PIL import Image
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

        # open user search blank
        url = f"{self.base_url}?q=&src=typed_query&f=user"
        self.driver.get(url)
        time.sleep(random.uniform(1,2))

        # scroll to load more
        for _ in range(2):
            self.driver.execute_script("window.scrollBy(0,document.body.scrollHeight);")
            time.sleep(0.5)

        cells = self.driver.find_elements(By.CSS_SELECTOR,"div[data-testid='UserCell']")[:max_results*3]
        candidates = []

        for cell in cells:
            try:
                link = cell.find_element(By.TAG_NAME,"a").get_attribute("href")
                img  = cell.find_element(By.TAG_NAME,"img").get_attribute("src")
                resp = requests.get(img, timeout=5)
                avatar = Image.open(BytesIO(resp.content)).convert("RGB")

                if q_emb:
                    emb = self.face_encoder.encode_faces(resp.content)
                    if emb:
                        emb = emb[0]
                        sim = float((q_emb @ emb) /
                                    (np.linalg.norm(q_emb)*np.linalg.norm(emb)))
                    else:
                        raise ValueError("no face")
                else:
                    raise ValueError("no face in query")
            except Exception:
                try:
                    h    = imagehash.phash(avatar)
                    dist = q_hash - h
                    sim  = 1 - (dist/64)
                except Exception as e:
                    logger.debug(f"TW hash fallback error: {e}")
                    continue

            candidates.append({"url": link, "similarity": sim, "source": "twitter"})

        return sorted(candidates, key=lambda x: x["similarity"], reverse=True)[:max_results]

    def name_search(self, name, max_results=10):
        url = f"{self.base_url}?q={name}&src=typed_query&f=user"
        self.driver.get(url)
        time.sleep(random.uniform(1,2))

        for _ in range(2):
            self.driver.execute_script("window.scrollBy(0,document.body.scrollHeight);")
            time.sleep(0.5)

        cells = self.driver.find_elements(By.CSS_SELECTOR,"div[data-testid='UserCell']")[:max_results]
        results = []
        for cell in cells:
            try:
                uname = cell.find_element(By.CSS_SELECTOR,"div[dir='ltr']").text.strip("@")
                disp  = cell.find_element(By.CSS_SELECTOR,"div[dir='auto']").text
                results.append({
                    "url": f"https://twitter.com/{uname}",
                    "username": f"@{uname}",
                    "name": disp,
                    "source":"twitter"
                })
            except Exception as e:
                logger.debug(f"TW name parse error: {e}")
        return results

