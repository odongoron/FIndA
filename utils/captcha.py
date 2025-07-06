import cv2
import numpy as np
import pytesseract
import requests
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

class CaptchaSolver:
    def __init__(self, driver, api_keys=None):
        self.driver = driver
        self.api_keys = api_keys or {}
        
    def solve_captcha(self):
        """Main method to detect and solve CAPTCHAs"""
        try:
            if self._is_cloudflare():
                return self._bypass_cloudflare()
            elif self._is_recaptcha_v2():
                return self._solve_recaptcha_v2()
            elif self._is_image_captcha():
                return self._solve_image_captcha()
            elif self._is_hcaptcha():
                return self._solve_hcaptcha()
            return self._use_captcha_service('generic')
        except Exception as e:
            logger.error(f"CAPTCHA solving failed: {str(e)}")
            return False

    def _is_cloudflare(self):
        try:
            return "cloudflare" in self.driver.page_source.lower()
        except:
            return False

    def _bypass_cloudflare(self):
        try:
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = {runtime: {}, app: {}};
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ? 
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.frame_to_be_available_and_switch_to_it((By.ID, "cf-challenge-widget")))
                checkbox = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "challenge-stage")))
                checkbox.click()
                self.driver.switch_to.default_content()
            except:
                pass
            return True
        except Exception as e:
            logger.error(f"Cloudflare bypass failed: {str(e)}")
            return False

    def _is_recaptcha_v2(self):
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, ".g-recaptcha")
        except:
            return False

    def _solve_recaptcha_v2(self):
        try:
            self.driver.switch_to.frame(self.driver.find_element(
                By.CSS_SELECTOR, "iframe[src^='https://www.google.com/recaptcha/api2']"))
            
            audio_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-audio-button")))
            audio_btn.click()
            
            audio_src = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "audio-source"))).get_attribute("src")
            
            audio_data = self._download_audio(audio_src)
            text = self._speech_to_text(audio_data)
            
            audio_response = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "audio-response")))
            audio_response.send_keys(text)
            
            verify_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-verify-button")))
            verify_btn.click()
            
            self.driver.switch_to.default_content()
            return True
        except Exception as e:
            logger.error(f"reCAPTCHA v2 solving failed: {str(e)}")
            return False

    def _download_audio(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        return requests.get(url, headers=headers, timeout=10).content

    def _speech_to_text(self, audio_data):
        # Placeholder - implement with actual speech recognition
        return "123456"

    def _is_image_captcha(self):
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, "img.captcha-img")
        except:
            return False

    def _solve_image_captcha(self):
        try:
            captcha_img = self.driver.find_element(By.CSS_SELECTOR, "img.captcha-img")
            img_data = captcha_img.screenshot_as_png
            
            img = Image.open(BytesIO(img_data))
            img = img.convert('L')
            img = np.array(img)
            img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            
            text = pytesseract.image_to_string(img, config='--psm 8')
            cleaned_text = ''.join(e for e in text if e.isalnum())
            
            input_field = self.driver.find_element(By.CSS_SELECTOR, "input.captcha-text")
            input_field.send_keys(cleaned_text)
            
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            return True
        except Exception as e:
            logger.error(f"Image CAPTCHA solving failed: {str(e)}")
            return False

    def _is_hcaptcha(self):
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, ".h-captcha")
        except:
            return False

    def _solve_hcaptcha(self):
        return self._use_captcha_service('hcaptcha')

    def _use_captcha_service(self, captcha_type):
        try:
            api_key = self.api_keys.get('2captcha')
            if not api_key:
                logger.error("2Captcha API key not configured")
                return False
                
            site_key = self._extract_site_key(captcha_type)
            page_url = self.driver.current_url
            
            response = requests.post(
                'http://2captcha.com/in.php',
                data={
                    'key': api_key,
                    'method': 'userrecaptcha' if 'recaptcha' in captcha_type else 'hcaptcha',
                    'googlekey': site_key,
                    'pageurl': page_url,
                    'json': 1
                }
            )
            
            if response.json().get('status') != 1:
                return False
                
            request_id = response.json().get('request')
            
            for _ in range(20):
                time.sleep(5)
                result = requests.get(
                    f'http://2captcha.com/res.php?key={api_key}&action=get&id={request_id}&json=1'
                ).json()
                if result.get('status') == 1:
                    solution = result.get('request')
                    self.driver.execute_script(
                        f'document.getElementById("g-recaptcha-response").innerHTML = "{solution}";')
                    return True
            return False
        except Exception as e:
            logger.error(f"External CAPTCHA service failed: {str(e)}")
            return False

    def _extract_site_key(self, captcha_type):
        try:
            if 'recaptcha' in captcha_type:
                return self.driver.execute_script(
                    "return document.querySelector('.g-recaptcha').getAttribute('data-sitekey')")
            elif 'hcaptcha' in captcha_type:
                return self.driver.execute_script(
                    "return document.querySelector('.h-captcha').getAttribute('data-sitekey')")
            return self.driver.execute_script(
                "return document.querySelector('[data-sitekey]')?.getAttribute('data-sitekey')")
        except:
            logger.error("Failed to extract site key")
            return None
