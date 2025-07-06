import os, time, random, logging, requests
import numpy as np
import imagehash
from io import BytesIO
from PIL import Image
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper
from core.face_recognition import FaceEncoder

logger = logging.getLogger(__name__)

class FacebookScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.requires_login = True
        self.login_url     = "https://m.facebook.com/login"
        self.search_base   = "https://m.facebook.com/search/people/?q="
        self.face_encoder  = FaceEncoder()

    def reverse_image_search(self, image_bytes, max_results=10):
        # 1) prepare query embeddings & hash
        q_embs = self.face_encoder.encode_faces(image_bytes)
        q_emb  = q_embs[0] if q_embs else None
        q_hash = imagehash.phash(Image.open(BytesIO(image_bytes)))

        # 2) ensure login
        if not self._is_logged_in() and not self._login():
            return []

        # 3) open blank people search to surface many profiles
        self.driver.get(self.search_base + quote_plus(""))
        self._human_delay()

        # 4) scroll to load cards
        for _ in range(3):
            self.driver.execute_script("window.scrollBy(0,document.body.scrollHeight);")
            self._human_delay(0.5,1.5)

        cards = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@data-testid,'browse-result-')]")[: max_results * 3]
        candidates = []

        for card in cards:
            try:
                anchor   = card.find_element(By.TAG_NAME, "a")
                profile  = anchor.get_attribute("href")
                thumb_el = card.find_element(By.TAG_NAME, "img")
                thumb_url= thumb_el.get_attribute("src")

                # download thumbnail
                resp = requests.get(thumb_url, timeout=5)
                img  = Image.open(BytesIO(resp.content)).convert("RGB")

                # compute similarity
                if q_emb:
                    emb = self.face_encoder.encode_faces(resp.content)
                    if emb:
                        emb = emb[0]
                        sim = float((q_emb @ emb) /
                                    (np.linalg.norm(q_emb)*np.linalg.norm(emb)))
                    else:
                        raise ValueError("no face in avatar")
                else:
                    raise ValueError("no face in query")

            except Exception:
                # fallback: perceptual hash
                try:
                    h    = imagehash.phash(img)
                    dist = q_hash - h
                    sim  = 1 - (dist/64)
                except Exception as e:
                    logger.debug(f"FB hash fallback error: {e}")
                    continue

            candidates.append({"url": profile, "similarity": sim, "source": "facebook"})
        
        # sort & return top-N
        return sorted(candidates, key=lambda x: x["similarity"], reverse=True)[:max_results]

    def name_search(self, name, max_results=10):
        if not self._is_logged_in() and not self._login():
            return []

        url = self.search_base + quote_plus(name)
        self.driver.get(url)
        self._human_delay()

        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='article']"))
        )
        self._human_delay(0.5,1.0)

        cards = self.driver.find_elements(By.XPATH, "//div[@role='article']")[:max_results]
        results = []
        for c in cards:
            try:
                link = c.find_element(By.TAG_NAME, "a").get_attribute("href")
                nm   = c.find_element(By.XPATH, ".//span[@dir='auto']").text
                results.append({"url": link, "name": nm, "source": "facebook"})
            except Exception as e:
                logger.debug(f"FB name card parse error: {e}")
        return results

    def _is_logged_in(self):
        self.driver.get("https://m.facebook.com")
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'/logout')]"))
            )
            return True
        except:
            return False

    def _login(self):
        for attempt in range(2):
            self.driver.get(self.login_url)
            self._human_delay()
            try:
                # dismiss cookie banner
                for txt in ("Accept All","Allow all cookies"):
                    try:
                        self.driver.find_element(By.XPATH, f"//button[text()='{txt}']").click()
                        break
                    except: pass

                email = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "email")))
                pwd   = self.driver.find_element(By.NAME, "pass")
                email.clear(); pwd.clear()
                email.send_keys(os.getenv("FACEBOOK_USER",""))
                self._human_delay(0.5,1.0)
                pwd.send_keys(os.getenv("FACEBOOK_PASS",""))
                self._human_delay(0.5,1.0)
                self.driver.find_element(By.NAME, "login").click()
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'/logout')]"))
                )
                return True
            except Exception as e:
                logger.warning(f"FB login attempt {attempt+1} failed: {e}")
                self._recreate_driver()
        logger.error("Facebook login failed after retries.")
        return False

    def _human_delay(self, a=1.0, b=2.0):
        time.sleep(random.uniform(a,b))

