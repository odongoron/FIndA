import time, random, logging, requests, numpy as np, imagehash
from io import BytesIO
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper
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
            return []

        # prepare query
        q_embs = self.face_encoder.encode_faces(image_bytes)
        q_emb  = q_embs[0] if q_embs else None
        q_hash = imagehash.phash(Image.open(BytesIO(image_bytes)))

        self.driver.get(self.base_url)
        time.sleep(random.uniform(1,2))

        # camera icon
        icon = WebDriverWait(self.driver,15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,".ZaFQO"))
        )
        icon.click(); time.sleep(1)

        # upload tab
        try:
            tab = WebDriverWait(self.driver,5).until(
                EC.element_to_be_clickable((By.XPATH,"//div[text()='Upload an image']"))
            )
            tab.click(); time.sleep(1)
        except: pass

        # file input
        inp = WebDriverWait(self.driver,10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,"input#awyMjb"))
        )
        inp.send_keys(img_path)
        time.sleep(random.uniform(2,3))

        # parse result cards
        cards = self.driver.find_elements(By.CSS_SELECTOR,".isv-r")[:max_results*3]
        candidates = []

        for c in cards:
            try:
                thumb = c.find_element(By.TAG_NAME,"img").get_attribute("src")
                page  = c.find_element(By.CSS_SELECTOR,".VFACy").get_attribute("href")
                resp  = requests.get(thumb, timeout=5)
                img   = Image.open(BytesIO(resp.content)).convert("RGB")

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
                    h    = imagehash.phash(img)
                    dist = q_hash - h
                    sim  = 1 - (dist/64)
                except Exception as e:
                    logger.debug(f"Google hash fallback error: {e}")
                    continue

            candidates.append({"image_url": thumb, "page_url": page,
                               "similarity": sim, "source": "google"})
        
        FileUtils.delete_file(img_path)
        return sorted(candidates, key=lambda x: x["similarity"], reverse=True)[:max_results]

    def name_search(self, *args, **kwargs):
        return []

