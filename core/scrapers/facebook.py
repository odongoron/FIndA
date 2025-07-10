import os
import time
import random
import logging
import requests
import numpy as np
import imagehash

from io import BytesIO                                       # UPDATED
from PIL import Image                                        # UPDATED
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
        self.login_url     = "https://www.facebook.com/login"
        self.search_base   = "https://m.facebook.com/search/people/?q="
        self.face_encoder  = FaceEncoder()

    def reverse_image_search(self, image_bytes, max_results=10):
        q_embs = self.face_encoder.encode_faces(image_bytes)
        q_emb  = q_embs[0] if q_embs else None
        q_hash = imagehash.phash(Image.open(BytesIO(image_bytes)))

        if not self._is_logged_in() and not self._login():
            return []

        self.driver.get(self.search_base + quote_plus(""))
        self._human_delay()
        for _ in range(3):
            self.driver.execute_script("window.scrollBy(0,document.body.scrollHeight);")
            self._human_delay(0.5,1.5)

        cards = self.driver.find_elements(
            By.XPATH,
            "//div[contains(@data-testid,'browse-result-')]"
        )[: max_results * 3]

        candidates = []
        for card in cards:
            try:
                href      = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                thumb_url = card.find_element(By.TAG_NAME, "img").get_attribute("src")

                # fetch thumbnail
                resp = requests.get(thumb_url, timeout=5)                     # UPDATED
                ctype = resp.headers.get("Content-Type", "")                  # UPDATED
                if resp.status_code != 200 or not ctype.startswith("image/"): # UPDATED
                    logger.warning(f"FB thumb HTTP {resp.status_code} or non-image {ctype}") # UPDATED
                    continue                                                   # UPDATED
                if len(resp.content) < 1000:                                  # UPDATED
                    logger.warning("FB thumb too small, skipping")            # UPDATED
                    continue                                                   # UPDATED

                # open image safely
                try:
                    avatar = Image.open(BytesIO(resp.content)).convert("RGB") # UPDATED
                except Exception as e:
                    logger.error(f"PIL open failed on FB thumb: {e}")       # UPDATED
                    continue                                                  # UPDATED

                # compute similarity via embedding
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
                # fallback: perceptual hash
                try:
                    h    = imagehash.phash(avatar)
                    dist = q_hash - h
                    sim  = 1 - (dist / 64.0)
                except Exception as e:
                    logger.debug(f"FB hash fallback error: {e}")
                    continue

            candidates.append({"url": href, "similarity": sim, "source": "facebook"})

        return sorted(candidates, key=lambda x: x["similarity"], reverse=True)[:max_results]

    # name_search, _is_logged_in, _login, _human_delay unchanged


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
        self.driver.get("https://www.facebook.com")
        try:
            # Look for the Create Post area as sign of logged-in desktop site
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@aria-label='Create Post']"))
            )
            return True
        except:
            return False

    def _login(self):
        user = os.getenv("FACEBOOK_USER", "")
        pwd  = os.getenv("FACEBOOK_PASS", "")
        logger.debug(f"FB creds loaded: user='{user}', pass set={bool(pwd)}")

        for attempt in range(2):
            self.driver.get(self.login_url)
            self._human_delay()

            try:
                # accept cookies banner if present
                try:
                    btn = self.driver.find_element(
                        By.XPATH, "//button[text()='Allow All Cookies' or text()='Accept All']")
                    btn.click()
                    self._human_delay(0.5,1.0)
                except: pass

                # wait for and fill login form
                email = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "email"))
                )
                passwd = self.driver.find_element(By.ID, "pass")
                email.clear(); passwd.clear()
                email.send_keys(user)
                self._human_delay(0.5,1.0)
                passwd.send_keys(pwd)
                self._human_delay(0.5,1.0)

                # submit credentials
                login_btn = self.driver.find_element(By.NAME, "login")
                login_btn.click()

                # confirm login by checking for Create Post area
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@aria-label='Create Post']"))
                )
                return True

            except Exception as e:
                logger.warning(f"FB login attempt {attempt+1} failed: {e}")
                # save screenshot for debug
                self.driver.save_screenshot(f"fb_login_fail_{attempt+1}.png")
                # recreate driver to reset session/cookies
                self._recreate_driver()

        logger.error("Facebook login failed after all retries.")
        return False

    def _human_delay(self, a=1.0, b=2.0):
        time.sleep(random.uniform(a, b))

