import os
import logging
import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from utils.captcha import CaptchaSolver
from utils.network import ProxyManager

logger = logging.getLogger(__name__)

class BaseScraper:
    def __init__(self, api_keys=None):
        self.api_keys = api_keys or {}

        # Load global settings to check if proxies are enabled
        with open("config/targets.yaml", "r") as f:
            self.settings = yaml.safe_load(f)

        # Initialize proxy manager (reads config/proxies.yaml)
        self.proxy_manager = ProxyManager("config/proxies.yaml")

        # Create the Selenium driver
        self.driver = self._create_stealth_driver()

        # Initialize CAPTCHA solver
        self.captcha_solver = CaptchaSolver(self.driver, self.api_keys)

    def _create_stealth_driver(self):
        options = Options()

        # Stealth flags
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Set a common user‐agent
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
        options.add_argument(f"user-agent={user_agent}")

        # Proxy configuration: only if enabled in targets.yaml
        if self.settings.get("proxies", {}).get("enabled", False):
            proxy = self.proxy_manager.get_next_proxy()
            if proxy and proxy.get("http"):
                options.add_argument(f"--proxy-server={proxy['http']}")
        else:
            # Force Chrome to ignore any system or env proxies
            options.add_argument("--no-proxy-server")
            options.add_experimental_option("excludeSwitches", ["proxy-server"])

        # Build the driver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        # Additional stealth JavaScript injections
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent})
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {},
                    app: {}
                };
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (params) => (
                    params.name === 'notifications'
                        ? Promise.resolve({ state: Notification.permission })
                        : originalQuery(params)
                );
            """
        })

        return driver

    def _handle_captcha(self):
        try:
            return self.captcha_solver.solve_captcha()
        except Exception as e:
            logger.error(f"CAPTCHA handling failed: {e}")
            return False

    def _recreate_driver(self):
        """Quit and rebuild the Selenium driver (e.g. after proxy rotation)."""
        try:
            self.driver.quit()
        except Exception:
            pass
        self.driver = self._create_stealth_driver()
        self.captcha_solver = CaptchaSolver(self.driver, self.api_keys)

