import os, time, random, logging, requests, numpy as np, imagehash
from io import BytesIO
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper
from core.face_recognition import FaceEncoder

logger = logging.getLogger(__name__)

class InstagramScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.requires_login = True
        self.login_url     = "https://www.instagram.com/accounts/login/"
        self.suggest_api   = "https://www.instagram.com/explore/people/?__a=1"
        self.face_encoder  = FaceEncoder()

    def reverse_image_search(self, image_bytes, max_results=10):
        # 1) prepare query embeddings & hash
        q_embs = self.face_encoder.encode_faces(image_bytes)
        q_emb  = q_embs[0] if q_embs else None
        q_hash = imagehash.phash(Image.open(BytesIO(image_bytes)))

        # 2) ensure login
        if not self._is_logged_in() and not self._login():
            return []

        # 3) get JSON suggestions
        self.driver.get(self.suggest_api)
        pre = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        data = pre.text
        try:
            users = requests.utils.json.loads(data).get("users", [])[:max_results*3]
        except:
            logger.error("IG parse JSON suggestions")
            return []

        candidates = []
        for u in users:
            try:
                info = u["user"]
                url  = f"https://www.instagram.com/{info['username']}/"
                thumb_url = info["profile_pic_url"]
                resp = requests.get(thumb_url, timeout=5)
                img  = Image.open(BytesIO(resp.content)).convert("RGB")

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
                except Exception as ex:
                    logger.debug(f"IG hash fallback error: {ex}")
                    continue

            candidates.append({"url": url, "username": info["username"],
                               "similarity": sim, "source": "instagram"})

        return sorted(candidates, key=lambda x: x["similarity"], reverse=True)[:max_results]

    def name_search(self, name, max_results=10):
        if not self._is_logged_in() and not self._login():
            return []

        url = f"https://www.instagram.com/web/search/topsearch/?context=user&query={name}"
        self.driver.get(url)
        time.sleep(random.uniform(1,2))

        pre = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        try:
            users = requests.utils.json.loads(pre.text).get("users", [])[:max_results]
        except:
            return []

        return [
            {
                "url": f"https://www.instagram.com/{u['user']['username']}/",
                "username": u["user"]["username"],
                "name": u["user"].get("full_name",""),
                "source": "instagram"
            }
            for u in users
        ]

    def _is_logged_in(self):
        self.driver.get("https://www.instagram.com")
        try:
            WebDriverWait(self.driver,5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,"svg[aria-label='Home']"))
            )
            return True
        except:
            return False

    def _login(self):
        for attempt in range(2):
            self.driver.get(self.login_url)
            time.sleep(random.uniform(1,2))
            try:
                # cookie banner
                self.driver.find_element(By.XPATH,
                    "//button[text()='Only allow essential cookies']").click()
            except: pass

            user = WebDriverWait(self.driver,10).until(
                EC.presence_of_element_located((By.NAME,"username")))
            pwd  = self.driver.find_element(By.NAME,"password")
            user.clear(); pwd.clear()
            user.send_keys(os.getenv("INSTAGRAM_USER",""))
            time.sleep(0.5)
            pwd.send_keys(os.getenv("INSTAGRAM_PASS",""))
            time.sleep(0.5)
            self.driver.find_element(By.CSS_SELECTOR,"button[type='submit']").click()

            try:
                WebDriverWait(self.driver,10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,"svg[aria-label='Home']"))
                )
                return True
            except Exception as e:
                logger.warning(f"IG login attempt {attempt+1} failed: {e}")
                self._recreate_driver()
        logger.error("Instagram login failed after retries.")
        return False

