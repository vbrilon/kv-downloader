"""Chrome browser management for karaoke automation"""

import os
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from ..configuration.config import WEBDRIVER_DEFAULT_TIMEOUT, DOWNLOAD_COMPLETION_TIMEOUT, DOWNLOAD_CHECK_INTERVAL
from ..utils.performance_profiler import profile_timing, profile_selenium
from webdriver_manager.chrome import ChromeDriverManager

try:
    from packages.configuration import DOWNLOAD_FOLDER
except ImportError:
    # Fallback for when config is not available during testing
    DOWNLOAD_FOLDER = "./downloads"


class ChromeManager:
    """Manages Chrome browser setup, configuration, and lifecycle"""
    
    def __init__(self, headless=False):
        """
        Initialize Chrome manager
        
        Args:
            headless (bool): Run browser in headless mode (True) or visible mode (False)
        """
        self.headless = headless
        self.driver = None
        self.wait = None
    
    @profile_timing("setup_driver", "browser", "method")
    def setup_driver(self):
        """Initialize Chrome driver with configuration options"""
        chrome_options = self._configure_chrome_options()
        service = self._get_chrome_service()
        
        try:
            logging.info("⏳ Starting Chrome browser...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, WEBDRIVER_DEFAULT_TIMEOUT)
            logging.info("✅ Chrome browser started successfully")
            
        except Exception as e:
            logging.error(f"❌ Failed to start Chrome browser: {e}")
            self._log_troubleshooting_tips()
            raise
    
    def _configure_chrome_options(self):
        """Configure Chrome options for automation"""
        chrome_options = Options()
        
        # Configure headless mode if requested
        if self.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            logging.info("🔇 Running in headless mode (browser hidden)")
            logging.debug("Headless Chrome arguments: --headless, --no-sandbox, --disable-dev-shm-usage, --disable-gpu")
        else:
            logging.info("👁️ Running in visible mode (browser window open)")
            logging.debug("Chrome will open visible window for debugging")
        
        # Add Chrome binary path for macOS if needed
        if os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            logging.debug("Using Chrome binary at: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        
        # Additional stability options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use persistent user data directory for session persistence
        user_data_dir = os.path.abspath("chrome_profile")
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # Allow reusing the same profile without conflicts
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor") 
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        
        logging.debug(f"Chrome user data directory: {user_data_dir}")
        
        # Initial download preferences (will be updated per song)
        prefs = {
            "download.default_directory": os.path.abspath(DOWNLOAD_FOLDER),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        logging.debug(f"Chrome download directory: {os.path.abspath(DOWNLOAD_FOLDER)}")
        logging.debug("Chrome preferences configured for automatic downloads")
        
        return chrome_options
    
    def _get_chrome_service(self):
        """Get Chrome service (local or downloaded ChromeDriver)"""
        logging.info("⏳ Setting up ChromeDriver...")
        
        # Try local ChromeDriver first (faster and more reliable)
        local_paths = [
            "/opt/homebrew/bin/chromedriver",  # Homebrew on Apple Silicon
            "/usr/local/bin/chromedriver",     # Homebrew on Intel
            str(Path.home() / ".webdriver" / "chromedriver" / "chromedriver"),
            "chromedriver"  # In PATH
        ]
        
        service = None
        for path in local_paths:
            if os.path.exists(path):
                logging.info(f"✅ Using local ChromeDriver at: {path}")
                try:
                    # Try with a specific port to avoid binding issues
                    service = Service(path, port=9515)
                except Exception as e:
                    logging.debug(f"Port 9515 failed, trying default: {e}")
                    service = Service(path)
                break
        
        # Fallback to webdriver-manager if no local version found
        if not service:
            logging.info("⏳ No local ChromeDriver found, downloading...")
            try:
                driver_path = ChromeDriverManager().install()
                try:
                    service = Service(driver_path, port=9515)
                except Exception as e:
                    logging.debug(f"Port 9515 failed, trying default: {e}")
                    service = Service(driver_path)
                logging.info("✅ ChromeDriver downloaded successfully")
            except Exception as e:
                logging.error(f"❌ ChromeDriver download failed: {e}")
                logging.error("💡 Please install ChromeDriver manually:")
                logging.error("   macOS: brew install chromedriver")
                logging.error("   Then run: xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver")
                logging.error("   Test with: python test_chrome_quick.py")
                raise Exception("ChromeDriver not available")
        
        return service
    
    def _log_troubleshooting_tips(self):
        """Log troubleshooting tips for Chrome setup issues"""
        logging.error("💡 Troubleshooting tips:")
        logging.error("   1. Make sure Chrome is installed: https://www.google.com/chrome/")
        logging.error("   2. Try updating Chrome to the latest version")  
        logging.error("   3. Run manual setup: python manual_chromedriver_setup.py")
        logging.error("   4. Install via Homebrew: brew install chromedriver")
        logging.error("   5. Check your internet connection")
    
    def setup_folders(self):
        """Create necessary folders for downloads and logs"""
        Path(DOWNLOAD_FOLDER).mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
    
    def set_download_path(self, path):
        """Update download path for current session"""
        if self.driver:
            self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': str(path)
            })
            logging.debug(f"Updated download path to: {path}")
    
    @profile_timing("wait_for_downloads_to_complete", "browser", "method")
    def wait_for_downloads_to_complete(self, download_path, timeout=DOWNLOAD_COMPLETION_TIMEOUT):
        """Wait for any active downloads to complete before quitting"""
        if not self.driver:
            return
            
        import time
        import glob
        from pathlib import Path
        
        logging.info("🔍 Checking for active downloads before closing browser...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for .crdownload files which indicate active downloads
            download_folder = Path(download_path)
            if download_folder.exists():
                crdownload_files = list(download_folder.glob("**/*.crdownload"))
                if crdownload_files:
                    logging.info(f"⏳ Waiting for {len(crdownload_files)} active downloads to complete...")
                    time.sleep(DOWNLOAD_CHECK_INTERVAL)
                    continue
            
            # No active downloads found
            logging.info("✅ No active downloads detected")
            break
        else:
            logging.warning(f"⚠️ Timeout waiting for downloads to complete after {timeout} seconds")
    
    def quit(self):
        """Safely quit the browser after waiting for downloads to complete"""
        if self.driver:
            try:
                # Wait for any active downloads to complete
                from packages.configuration import DOWNLOAD_FOLDER
                self.wait_for_downloads_to_complete(DOWNLOAD_FOLDER)
                
                logging.info("🔚 Closing Chrome browser...")
                self.driver.quit()
                logging.info("🔚 Chrome browser closed")
                
            except Exception as e:
                logging.warning(f"⚠️ Error during browser cleanup: {e}")
                # Force quit if normal quit fails
                try:
                    self.driver.quit()
                except Exception as quit_error:
                    # Suppress connection errors since browser may already be closed
                    if "connection refused" not in str(quit_error).lower():
                        logging.debug(f"Force quit error: {quit_error}")
            finally:
                self.driver = None
                self.wait = None