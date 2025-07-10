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
from utils.file_utils import FileUtils                        # UPDATED
from core.face_recognition import FaceEncoder

logger = logging.getLogger(__name__)

class InstagramScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.requires_login = True
        self.login_url      = "https://www.instagram.com/accounts/login/"
        self.suggest_api    = "https://www.instagram.com/explore/people/?__a=1"
        self.face_encoder   = FaceEncoder()

    def reverse_image_search(self, image_bytes, max_results=10):
        img_path = FileUtils.create_temp_file(image_bytes, suffix=".jpg")
        if not img_path:
            return []

        q_embs = self.face_encoder.encode_faces(image_bytes)
        q_emb  = q_embs[0] if q_embs else None
        q_hash = imagehash.phash(Image.open(BytesIO(image_bytes)))

        if not self._is_logged_in() and not self._login():
            FileUtils.delete_file(img_path)
            return []

        try:
            self.driver.get(self.suggest_api)
            time.sleep(random.uniform(1.0,1.5))
            pre = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            users = requests.utils.json.loads(pre.text).get("users", [])[: max_results * 3]
        except Exception as e:
            logger.error(f"IG suggest/JSON error: {e}")
            FileUtils.delete_file(img_path)
            return []

        candidates = []
        for u in users:
            try:
                info      = u["user"]
                profile   = f"https://www.instagram.com/{info['username']}/"
                thumb_url = info["profile_pic_url"]

                resp = requests.get(thumb_url, timeout=5)                     # UPDATED
                ctype = resp.headers.get("Content-Type", "")                  # UPDATED
                if resp.status_code != 200 or not ctype.startswith("image/"): # UPDATED
                    logger.warning(f"IG thumb HTTP {resp.status_code} or non-image {ctype}") # UPDATED
                    continue                                                   # UPDATED
                if len(resp.content) < 1000:                                  # UPDATED
                    logger.warning("IG thumb too small, skipping")           # UPDATED
                    continue                                                   # UPDATED

                try:
                    avatar = Image.open(BytesIO(resp.content)).convert("RGB") # UPDATED
                except Exception as e:
                    logger.error(f"PIL open failed on IG thumb: {e}")       # UPDATED
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
                except Exception as ex:
                    logger.debug(f"IG hash fallback error: {ex}")
                    continue

            candidates.append({
                "url": profile,
                "username": info["username"],
                "similarity": sim,
                "source": "instagram"
            })

        FileUtils.delete_file(img_path)                                # UPDATED
        return sorted(candidates, key=lambda x: x["similarity"], reverse=True)[:max_results]

    # name_search, _is_logged_in, _login, _human_delay unchanged


    def name_search(self, name, max_results=10):
        """Name-based search via Instagram's web API."""
        # ensure login
        if not self._is_logged_in() and not self._login():
            return []

        url = f"https://www.instagram.com/web/search/topsearch/?context=user&query={name}"
        self.driver.get(url)
        time.sleep(random.uniform(1.0, 1.5))            # UPDATED

        try:
            pre = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            data  = pre.text
            users = requests.utils.json.loads(data).get("users", [])[:max_results]
        except Exception as e:
            logger.error(f"IG name_search JSON parse failed: {e}")  # UPDATED
            return []

        results = []
        for u in users:
            results.append({
                "url": f"https://www.instagram.com/{u['user']['username']}/",
                "username": u["user"]["username"],
                "name": u["user"].get("full_name", ""),
                "source": "instagram"
            })
        return results

    def _is_logged_in(self):
        """Check Instagram login by presence of Home icon."""
        self.driver.get("https://www.instagram.com")
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "svg[aria-label='Home']"))
            )
            return True
        except:
            return False

    def _login(self):
        """Perform login with retry and screenshot on failure."""
        user = os.getenv("INSTAGRAM_USER", "")
        pwd  = os.getenv("INSTAGRAM_PASS", "")
        logger.debug(f"IG creds loaded: user='{user}', pass set={bool(pwd)}")  # UPDATED

        for attempt in range(2):
            self.driver.get(self.login_url)
            time.sleep(random.uniform(1.0, 1.5))        # UPDATED
            try:
                # dismiss cookie banner
                try:
                    btn = self.driver.find_element(
                        By.XPATH, "//button[text()='Only allow essential cookies']"
                    )
                    btn.click()
                    self._human_delay(0.5, 1.0)
                except:
                    pass

                # fill credentials
                username_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                password_field = self.driver.find_element(By.NAME, "password")
                username_field.clear(); password_field.clear()
                username_field.send_keys(user)
                time.sleep(0.5)
                password_field.send_keys(pwd)
                time.sleep(0.5)

                # submit
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

                # confirm login
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "svg[aria-label='Home']"))
                )
                return True
            except Exception as e:
                logger.warning(f"IG login attempt {attempt+1} failed: {e}")
                self.driver.save_screenshot(f"ig_login_fail_{attempt+1}.png")  # UPDATED
                self._recreate_driver()                         # UPDATED

        logger.error("Instagram login failed after all retries.")
        return False

    def _human_delay(self, a=1.0, b=2.0):
        time.sleep(random.uniform(a, b))

