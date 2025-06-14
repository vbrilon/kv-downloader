#!/usr/bin/env python3
"""
Modular Karaoke-Version.com Automation Library
Centralizes all automation logic into reusable components
"""

import time
import os
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation.log'),
        logging.StreamHandler()
    ]
)

class KaraokeVersionLogin:
    """Handles all login-related functionality"""
    
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait
    
    def is_logged_in(self):
        """Check if user is currently logged in"""
        try:
            # Primary check: Look for "My Account" in header
            my_account_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'My Account')]")
            if my_account_elements:
                logging.info("✅ User is logged in: Found 'My Account' in header")
                return True
            
            # Secondary check: No login links present
            login_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Log in')]")
            if not login_links:
                logging.info("✅ User appears logged in: No login links found")
                return True
            
            logging.info("❌ User is not logged in")
            return False
            
        except Exception as e:
            logging.error(f"Error checking login status: {e}")
            return False
    
    def click_login_link(self):
        """Find and click the login link"""
        try:
            login_selectors = [
                "//a[contains(text(), 'Log in')]",  # Working selector
                "//a[contains(text(), 'Log In')]",
                "//a[contains(text(), 'Login')]",
                "//a[contains(text(), 'Sign In')]"
            ]
            
            for selector in login_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        logging.info(f"Clicking login link: '{element.text}'")
                        element.click()
                        time.sleep(3)
                        return True
                except:
                    continue
            
            logging.warning("No login link found")
            return False
            
        except Exception as e:
            logging.error(f"Error clicking login link: {e}")
            return False
    
    def fill_login_form(self, username, password):
        """Fill and submit the login form"""
        try:
            # Find username field
            username_selectors = [
                (By.NAME, "frm_login"),  # Working selector for Karaoke-Version.com
                (By.NAME, "email"),
                (By.NAME, "username"),
                (By.ID, "email"),
                (By.CSS_SELECTOR, "input[type='email']")
            ]
            
            username_field = None
            for selector_type, selector_value in username_selectors:
                try:
                    username_field = self.wait.until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    if username_field and username_field.is_displayed():
                        logging.info(f"Found username field: {selector_type} = '{selector_value}'")
                        break
                except:
                    continue
            
            if not username_field:
                logging.error("Could not find username field")
                return False
            
            # Find password field
            password_selectors = [
                (By.NAME, "frm_password"),  # Working selector for Karaoke-Version.com
                (By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]
            
            password_field = None
            for selector_type, selector_value in password_selectors:
                try:
                    password_field = self.driver.find_element(selector_type, selector_value)
                    if password_field and password_field.is_displayed():
                        logging.info(f"Found password field: {selector_type} = '{selector_value}'")
                        break
                except:
                    continue
            
            if not password_field:
                logging.error("Could not find password field")
                return False
            
            # Fill credentials
            logging.info("Filling in credentials...")
            username_field.clear()
            username_field.send_keys(username)
            password_field.clear()
            password_field.send_keys(password)
            
            # Find and click submit button
            submit_selectors = [
                (By.NAME, "sbm"),  # Working selector for Karaoke-Version.com
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']")
            ]
            
            submit_button = None
            for selector_type, selector_value in submit_selectors:
                try:
                    submit_button = self.driver.find_element(selector_type, selector_value)
                    if submit_button and submit_button.is_displayed():
                        logging.info(f"Found submit button: {selector_type} = '{selector_value}'")
                        break
                except:
                    continue
            
            if not submit_button:
                logging.error("Could not find submit button")
                return False
            
            # Submit form
            submit_button.click()
            logging.info("Login form submitted")
            time.sleep(5)  # Wait for login to process
            
            return True
            
        except Exception as e:
            logging.error(f"Error filling login form: {e}")
            return False
    
    def login(self, username=None, password=None):
        """Complete login process"""
        # Use config credentials if not provided
        if not username:
            username = config.USERNAME
        if not password:
            password = config.PASSWORD
        
        if not username or not password:
            logging.error("Username or password not provided")
            return False
        
        logging.info("Starting login process...")
        
        # Navigate to homepage
        self.driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # Check if already logged in
        if self.is_logged_in():
            logging.info("Already logged in - skipping login process")
            return True
        
        # Click login link
        if not self.click_login_link():
            logging.error("Could not access login page")
            return False
        
        # Fill and submit login form
        if not self.fill_login_form(username, password):
            logging.error("Could not fill login form")
            return False
        
        # Verify login success
        if self.is_logged_in():
            logging.info("✅ Login successful!")
            return True
        else:
            logging.error("❌ Login failed - verification unsuccessful")
            return False


class KaraokeVersionTracker:
    """Handles track discovery and manipulation"""
    
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait
    
    def verify_song_access(self, song_url):
        """Verify user has access to song page"""
        logging.info(f"Verifying access to: {song_url}")
        self.driver.get(song_url)
        time.sleep(3)
        
        # Check for login redirects
        current_url = self.driver.current_url
        if "login" in current_url.lower():
            logging.error("Redirected to login - authentication required")
            return False
        
        # Check for track elements
        track_elements = self.driver.find_elements(By.CSS_SELECTOR, ".track")
        if not track_elements:
            logging.warning("No track elements found - may not have access")
            return False
        
        logging.info(f"✅ Access verified - found {len(track_elements)} tracks")
        return True
    
    def discover_tracks(self, song_url):
        """Discover all available tracks for a song"""
        if not self.verify_song_access(song_url):
            return []
        
        logging.info("Discovering available tracks...")
        track_elements = self.driver.find_elements(By.CSS_SELECTOR, ".track")
        
        tracks = []
        for track_element in track_elements:
            try:
                caption_element = track_element.find_element(By.CSS_SELECTOR, ".track__caption")
                track_name = caption_element.text.strip()
                data_index = track_element.get_attribute("data-index")
                
                if track_name and data_index is not None:
                    tracks.append({
                        'name': track_name,
                        'index': data_index,
                        'element': track_element
                    })
                    logging.info(f"Found track {data_index}: '{track_name}'")
            except Exception as e:
                logging.debug(f"Error processing track element: {e}")
                continue
        
        logging.info(f"Discovered {len(tracks)} tracks")
        return tracks
    
    def solo_track(self, track_info, song_url):
        """Solo a specific track (mutes all others)"""
        track_name = track_info['name']
        track_index = track_info['index']
        
        logging.info(f"Soloing track {track_index}: {track_name}")
        
        # Navigate to song page if not already there
        if self.driver.current_url != song_url:
            self.driver.get(song_url)
            time.sleep(3)
        
        try:
            # Find the specific track element
            track_selector = f".track[data-index='{track_index}']"
            track_elements = self.driver.find_elements(By.CSS_SELECTOR, track_selector)
            
            if not track_elements:
                logging.error(f"Could not find track element with data-index='{track_index}'")
                return False
            
            track_element = track_elements[0]
            
            # Find the solo button within this track
            solo_selectors = [
                "button.track__solo",  # Primary selector discovered
                "button.track__controls.track__solo",
                ".track__solo",
                "button[class*='solo']"
            ]
            
            solo_button = None
            for selector in solo_selectors:
                try:
                    solo_button = track_element.find_element(By.CSS_SELECTOR, selector)
                    if solo_button and solo_button.is_displayed():
                        logging.info(f"Found solo button with selector: {selector}")
                        break
                except:
                    continue
            
            if not solo_button:
                logging.error(f"Could not find solo button for track {track_index}")
                return False
            
            # Click the solo button
            logging.info(f"Clicking solo button for {track_name}")
            solo_button.click()
            time.sleep(1)  # Brief pause for UI to update
            
            # Verify solo button is active (if possible)
            try:
                button_classes = solo_button.get_attribute('class') or ''
                if 'active' in button_classes.lower() or 'selected' in button_classes.lower():
                    logging.info(f"✅ Solo button appears active for {track_name}")
                else:
                    logging.info(f"Solo button clicked for {track_name} (status unknown)")
            except:
                logging.info(f"Solo button clicked for {track_name}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error soloing track {track_name}: {e}")
            return False
    
    def clear_all_solos(self, song_url):
        """Clear all solo buttons (un-mute all tracks)"""
        logging.info("Clearing all solo buttons...")
        
        try:
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                time.sleep(3)
            
            # Find all solo buttons
            solo_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.track__solo")
            
            active_solos = 0
            for button in solo_buttons:
                try:
                    button_classes = button.get_attribute('class') or ''
                    if 'active' in button_classes.lower() or 'selected' in button_classes.lower():
                        logging.info("Clicking to deactivate active solo button")
                        button.click()
                        active_solos += 1
                        time.sleep(0.5)
                except:
                    continue
            
            if active_solos > 0:
                logging.info(f"Cleared {active_solos} active solo buttons")
            else:
                logging.info("No active solo buttons found")
            
            return True
            
        except Exception as e:
            logging.error(f"Error clearing solo buttons: {e}")
            return False


class KaraokeVersionAutomator:
    """Main automation class that coordinates all functionality"""
    
    def __init__(self):
        self.setup_driver()
        self.setup_folders()
        self.login_handler = KaraokeVersionLogin(self.driver, self.wait)
        self.track_handler = KaraokeVersionTracker(self.driver, self.wait)
    
    def setup_driver(self):
        """Initialize Chrome driver"""
        chrome_options = Options()
        
        prefs = {
            "download.default_directory": os.path.abspath(config.DOWNLOAD_FOLDER),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def setup_folders(self):
        """Create necessary folders"""
        Path(config.DOWNLOAD_FOLDER).mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
    
    def login(self):
        """Login using centralized login handler"""
        return self.login_handler.login()
    
    def is_logged_in(self):
        """Check login status using centralized handler"""
        return self.login_handler.is_logged_in()
    
    def get_available_tracks(self, song_url):
        """Get tracks using centralized track handler"""
        return self.track_handler.discover_tracks(song_url)
    
    def solo_track(self, track_info, song_url):
        """Solo a specific track using centralized track handler"""
        return self.track_handler.solo_track(track_info, song_url)
    
    def clear_all_solos(self, song_url):
        """Clear all solo buttons using centralized track handler"""
        return self.track_handler.clear_all_solos(song_url)
    
    def load_songs_config(self):
        """Load songs from configuration"""
        return config.load_songs_config()
    
    def sanitize_filename(self, filename):
        """Clean filename for saving"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename
    
    def run_automation(self):
        """Run complete automation workflow"""
        try:
            # Step 1: Login
            if not self.login():
                logging.error("Login failed - cannot proceed")
                return False
            
            # Step 2: Load songs
            songs = self.load_songs_config()
            if not songs:
                logging.error("No songs configured")
                return False
            
            logging.info(f"Processing {len(songs)} songs...")
            
            # Step 3: Process each song
            for song in songs:
                logging.info(f"Processing: {song['name']}")
                
                # Verify login status
                if not self.is_logged_in():
                    logging.error("Login session expired")
                    if not self.login():
                        logging.error("Re-login failed")
                        break
                
                # Get tracks
                tracks = self.get_available_tracks(song['url'])
                if tracks:
                    logging.info(f"Found {len(tracks)} tracks for {song['name']}")
                    # TODO: Implement download logic here
                else:
                    logging.error(f"No tracks found for {song['name']}")
            
            logging.info("Automation completed")
            return True
            
        except Exception as e:
            logging.error(f"Automation failed: {e}")
            return False
        finally:
            self.driver.quit()


if __name__ == "__main__":
    automator = KaraokeVersionAutomator()
    automator.run_automation()