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

class KaraokeVersionAutomator:
    def __init__(self):
        self.setup_driver()
        self.setup_download_folder()
        
    def setup_driver(self):
        """Initialize Chrome driver with download preferences"""
        chrome_options = Options()
        
        # Set download directory
        prefs = {
            "download.default_directory": os.path.abspath(config.DOWNLOAD_FOLDER),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Optional: Run headless
        # chrome_options.add_argument("--headless")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def setup_download_folder(self):
        """Create download folder structure"""
        Path(config.DOWNLOAD_FOLDER).mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        
    def check_login_status(self):
        """Check if user is already logged in - UPDATED WITH WORKING DETECTION"""
        try:
            # Look for "My Account" text that indicates we're logged in (WORKING METHOD)
            my_account_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'My Account')]")
            if my_account_elements:
                logging.info("✅ Already logged in: Found 'My Account' in header")
                return True
                        
            # Fallback: Check for absence of "Log In" links
            login_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Log in')]")
            if not login_links:
                logging.info("No 'Log in' links found - appears to be logged in")
                return True
                
            logging.info("User is not logged in")
            return False
            
        except Exception as e:
            logging.error(f"Error checking login status: {e}")
            return False
    
    def login(self):
        """Login to Karaoke-Version.com with comprehensive approach"""
        if not config.USERNAME or not config.PASSWORD:
            logging.error("Username or password not configured in .env file")
            return False
            
        logging.info("Navigating to main page...")
        self.driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # Check if already logged in
        if self.check_login_status():
            logging.info("✅ Already logged in - proceeding")
            return True
            
        logging.info("Attempting to log in...")
        
        # Try to find and click "Log In" link - UPDATED WITH WORKING SELECTORS
        login_link_selectors = [
            "//a[contains(text(), 'Log in')]",  # WORKING SELECTOR (lowercase 'i')
            "//a[contains(text(), 'Log In')]",
            "//a[contains(text(), 'Login')]",
            "//a[contains(text(), 'Sign In')]"
        ]
        
        login_link_found = False
        for selector in login_link_selectors:
            try:
                element = self.driver.find_element(By.XPATH, selector)
                if element and element.is_displayed():
                    logging.info(f"Clicking login link: '{element.text}'")
                    element.click()
                    time.sleep(3)
                    login_link_found = True
                    break
            except:
                continue
                
        if not login_link_found:
            logging.warning("No login link found, proceeding to find login form")
        
        # Find username/email field - UPDATED WITH WORKING SELECTORS
        username_selectors = [
            (By.NAME, "frm_login"),  # WORKING SELECTOR for Karaoke-Version.com
            (By.NAME, "email"),
            (By.NAME, "username"),
            (By.NAME, "login"),
            (By.ID, "email"),
            (By.ID, "username"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email']")
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
            logging.error("Could not find username/email field")
            return False
        
        # Find password field - UPDATED WITH WORKING SELECTORS
        password_selectors = [
            (By.NAME, "frm_password"),  # WORKING SELECTOR for Karaoke-Version.com
            (By.NAME, "password"),
            (By.ID, "password"),
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
        username_field.send_keys(config.USERNAME)
        password_field.clear()
        password_field.send_keys(config.PASSWORD)
        
        # Find and click submit button - UPDATED WITH WORKING SELECTORS
        submit_selectors = [
            (By.NAME, "sbm"),  # WORKING SELECTOR for Karaoke-Version.com
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Log')]"),
            (By.XPATH, "//input[@value*='Log']")
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
            
        submit_button.click()
        logging.info("Login form submitted")
        
        # Wait for login to complete and verify
        time.sleep(5)
        
        # Verify login success
        login_successful = self.check_login_status()
        
        if login_successful:
            logging.info("✅ Login successful!")
        else:
            logging.error("❌ Login failed or not detected")
            
        return login_successful
        
    def load_songs_from_config(self):
        """Load songs from configuration file"""
        logging.info("Loading songs from configuration file...")
        songs = config.load_songs_config()
        
        if not songs:
            logging.warning("No songs found in configuration file")
            return []
            
        logging.info(f"Loaded {len(songs)} songs from configuration")
        return songs
        
    def verify_access_to_song(self, song_url):
        """Verify user has access to song page (requires login)"""
        logging.info(f"Verifying access to song: {song_url}")
        self.driver.get(song_url)
        time.sleep(3)
        
        # Check if we're redirected to login or see login prompts
        current_url = self.driver.current_url
        page_source = self.driver.page_source.lower()
        
        # Check for login redirects or prompts
        if "login" in current_url.lower() or "signin" in current_url.lower():
            logging.error("Redirected to login page - authentication failed")
            return False
            
        if "please log in" in page_source or "sign in" in page_source:
            logging.error("Page requires login - authentication failed")
            return False
            
        # Check if we can see track elements (indicates proper access)
        track_elements = self.driver.find_elements(By.CSS_SELECTOR, ".track")
        if not track_elements:
            logging.warning("No track elements found - may not have proper access")
            return False
            
        logging.info(f"✅ Verified access to song page with {len(track_elements)} tracks")
        return True
    
    def get_available_tracks(self, song_url):
        """Discover all available tracks for a song dynamically (requires login)"""
        # Verify we have access to the song first
        if not self.verify_access_to_song(song_url):
            logging.error("Cannot access song - login required")
            return []
            
        logging.info("Discovering available tracks...")
        
        # Use discovered selectors from site inspection
        track_elements = self.driver.find_elements(By.CSS_SELECTOR, ".track")
        
        available_tracks = []
        for track_element in track_elements:
            try:
                # Get track name from .track__caption
                caption_element = track_element.find_element(By.CSS_SELECTOR, ".track__caption")
                track_name = caption_element.text.strip()
                data_index = track_element.get_attribute("data-index")
                
                if track_name and data_index is not None:
                    available_tracks.append({
                        'name': track_name,
                        'index': data_index,
                        'element': track_element
                    })
                    logging.info(f"Found track {data_index}: '{track_name}'")
            except Exception as e:
                logging.debug(f"Error processing track element: {e}")
                continue
                
        logging.info(f"Found {len(available_tracks)} available tracks")
        return available_tracks
        
    def download_track_variations(self, song_url, song_name):
        """Download all track variations for a song (requires login)"""
        logging.info(f"Processing song: {song_name}")
        
        # Verify login status before proceeding
        if not self.check_login_status():
            logging.error("User not logged in - cannot download tracks")
            return False
        
        # Create song folder using the provided name
        song_folder = Path(config.DOWNLOAD_FOLDER) / self.sanitize_filename(song_name)
        song_folder.mkdir(exist_ok=True)
        
        # Discover available tracks dynamically
        available_tracks = self.get_available_tracks(song_url)
        
        if not available_tracks:
            logging.error(f"No tracks found for {song_name} - skipping")
            return False
        
        logging.info(f"Found {len(available_tracks)} tracks to download")
        
        for track_info in available_tracks:
            try:
                track_name = track_info['name']
                track_index = track_info['index']
                logging.info(f"Processing track {track_index}: {track_name}")
                
                # Download individual track
                success = self.download_single_track(track_info, song_folder, song_url)
                if success:
                    logging.info(f"✅ Successfully downloaded {track_name}")
                else:
                    logging.error(f"❌ Failed to download {track_name}")
                
                time.sleep(config.DELAY_BETWEEN_DOWNLOADS)
            except Exception as e:
                logging.error(f"Failed to download {track_info.get('name', 'unknown')} for {song_name}: {e}")
                continue
                
        return True
                
    def select_individual_track(self, track_info, song_url):
        """Select only a specific track for isolation"""
        track_name = track_info['name']
        track_index = track_info['index']
        
        logging.info(f"Selecting track {track_index}: {track_name}")
        
        # Navigate to song page if not already there
        if self.driver.current_url != song_url:
            self.driver.get(song_url)
            time.sleep(3)
        
        # Common patterns for track controls based on web research
        track_control_patterns = [
            # Track-specific buttons/controls
            f"//div[@data-index='{track_index}']//button",
            f"//div[@data-index='{track_index}']//input[@type='checkbox']",
            f"//div[@data-index='{track_index}']//input[@type='radio']",
            f"//div[@data-index='{track_index}']//*[contains(@class, 'mute')]",
            f"//div[@data-index='{track_index}']//*[contains(@class, 'solo')]",
            f"//div[@data-index='{track_index}']//*[contains(@class, 'toggle')]",
            f"//div[@data-index='{track_index}']//*[contains(@class, 'select')]",
            
            # General track control patterns
            f".track[data-index='{track_index}'] button",
            f".track[data-index='{track_index}'] input",
            f".track[data-index='{track_index}'] .control",
            f".track[data-index='{track_index}'] .toggle",
            
            # Checkbox/radio patterns
            f"input[name='track_{track_index}']",
            f"input[data-track='{track_index}']",
            f"input[value='{track_index}']"
        ]
        
        # Try to find and interact with track controls
        control_found = False
        for pattern in track_control_patterns:
            try:
                if pattern.startswith("//"):
                    elements = self.driver.find_elements(By.XPATH, pattern)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                
                if elements:
                    logging.info(f"Found {len(elements)} controls with pattern: {pattern}")
                    
                    for element in elements:
                        try:
                            # Try to interact with the control
                            if element.is_displayed() and element.is_enabled():
                                # For checkboxes/radios, ensure it's selected
                                if element.get_attribute('type') in ['checkbox', 'radio']:
                                    if not element.is_selected():
                                        element.click()
                                        logging.info(f"Selected track control: {element.get_attribute('type')}")
                                        control_found = True
                                # For buttons, click them
                                elif element.tag_name == 'button':
                                    element.click()
                                    logging.info(f"Clicked track button: {element.text}")
                                    control_found = True
                                    
                                if control_found:
                                    break
                        except Exception as e:
                            logging.debug(f"Could not interact with control: {e}")
                            continue
                            
                    if control_found:
                        break
                        
            except Exception as e:
                logging.debug(f"Pattern {pattern} failed: {e}")
                continue
        
        if not control_found:
            logging.warning(f"No interactive controls found for track {track_index}: {track_name}")
            logging.info("Proceeding with download attempt anyway...")
        
        return True
    
    def initiate_download(self, track_info, song_folder):
        """Initiate download process for selected track"""
        track_name = track_info['name']
        
        logging.info(f"Initiating download for: {track_name}")
        
        # Common download button patterns based on web research
        download_patterns = [
            # Direct download buttons
            "//button[contains(text(), 'Download')]",
            "//a[contains(text(), 'Download')]",
            "//input[@value*='Download']",
            
            # Create/Generate buttons (common for custom backing tracks)
            "//button[contains(text(), 'Create')]",
            "//a[contains(text(), 'Create')]",
            "//button[contains(text(), 'Generate')]",
            "//a[contains(text(), 'Generate')]",
            
            # Export buttons
            "//button[contains(text(), 'Export')]",
            "//a[contains(text(), 'Export')]",
            
            # CSS selectors
            ".download-btn",
            ".download-button",
            ".create-btn",
            ".create-button",
            ".export-btn",
            "[class*='download']",
            "[class*='create']",
            "[id*='download']",
            "[id*='create']"
        ]
        
        download_initiated = False
        
        for pattern in download_patterns:
            try:
                if pattern.startswith("//"):
                    elements = self.driver.find_elements(By.XPATH, pattern)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                
                if elements:
                    logging.info(f"Found {len(elements)} download elements with pattern: {pattern}")
                    
                    for element in elements:
                        try:
                            if element.is_displayed() and element.is_enabled():
                                element_text = element.text.strip() or element.get_attribute('value') or 'button'
                                logging.info(f"Clicking download element: '{element_text}'")
                                element.click()
                                download_initiated = True
                                break
                        except Exception as e:
                            logging.debug(f"Could not click download element: {e}")
                            continue
                    
                    if download_initiated:
                        break
                        
            except Exception as e:
                logging.debug(f"Download pattern {pattern} failed: {e}")
                continue
        
        if download_initiated:
            logging.info("✅ Download initiated successfully")
            
            # Wait for download to start/complete
            logging.info("Waiting for download to process...")
            time.sleep(config.DELAY_BETWEEN_DOWNLOADS)
            
            # Check if download completed by looking for download folder
            sanitized_track_name = self.sanitize_filename(track_name)
            expected_file_patterns = [
                f"{sanitized_track_name}.mp3",
                f"{sanitized_track_name}.wav",
                f"{sanitized_track_name}.m4a",
                f"track_{track_info['index']}.mp3"
            ]
            
            # Check if any expected files appeared in download folder
            download_found = False
            for pattern in expected_file_patterns:
                potential_file = song_folder / pattern
                if potential_file.exists():
                    logging.info(f"✅ Download completed: {potential_file}")
                    download_found = True
                    break
            
            if not download_found:
                # Check default download directory for recent files
                import os
                default_downloads = Path.home() / "Downloads"
                if default_downloads.exists():
                    recent_files = sorted(
                        default_downloads.glob("*.mp3"), 
                        key=os.path.getctime, 
                        reverse=True
                    )[:3]  # Check 3 most recent MP3s
                    
                    if recent_files:
                        logging.info(f"Recent downloads found in default folder: {[f.name for f in recent_files]}")
            
            return True
        else:
            logging.error(f"❌ Could not find download button for {track_name}")
            return False
    
    def download_single_track(self, track_info, song_folder, song_url):
        """Download a specific track by selecting it and initiating download"""
        track_name = track_info['name']
        track_index = track_info['index']
        
        logging.info(f"Downloading track {track_index}: {track_name}")
        
        try:
            # Step 1: Select the specific track
            if not self.select_individual_track(track_info, song_url):
                logging.error(f"Failed to select track {track_name}")
                return False
            
            # Step 2: Initiate download
            if not self.initiate_download(track_info, song_folder):
                logging.error(f"Failed to download track {track_name}")
                return False
            
            logging.info(f"✅ Successfully processed download for {track_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error downloading track {track_name}: {e}")
            return False
        
    def sanitize_filename(self, filename):
        """Remove invalid characters from filename"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename
        
    def run(self):
        """Main automation flow - ensures login before any operations"""
        try:
            # Step 1: Ensure user is logged in
            login_successful = self.login()
            if not login_successful:
                logging.error("❌ Login failed - cannot proceed with automation")
                return False
            
            # Step 2: Load songs configuration
            songs = self.load_songs_from_config()
            if not songs:
                logging.error("No songs to process. Please check your songs.yaml configuration file.")
                return False
            
            logging.info(f"Processing {len(songs)} songs...")
            
            # Step 3: Process each song (only after login verified)
            successful_downloads = 0
            for i, song in enumerate(songs, 1):
                logging.info(f"\n--- Processing song {i}/{len(songs)}: {song['name']} ---")
                
                # Double-check login status before each song
                if not self.check_login_status():
                    logging.error("Login session expired - attempting to re-login")
                    if not self.login():
                        logging.error("Re-login failed - stopping automation")
                        break
                
                success = self.download_track_variations(song['url'], song['name'])
                if success:
                    successful_downloads += 1
                    logging.info(f"✅ Successfully processed {song['name']}")
                else:
                    logging.error(f"❌ Failed to process {song['name']}")
            
            # Step 4: Summary
            logging.info(f"\n{'='*60}")
            logging.info(f"AUTOMATION COMPLETED")
            logging.info(f"Successfully processed: {successful_downloads}/{len(songs)} songs")
            logging.info(f"{'='*60}")
            
            return successful_downloads > 0
            
        except Exception as e:
            logging.error(f"Automation failed with error: {e}")
            return False
        finally:
            self.driver.quit()

if __name__ == "__main__":
    automator = KaraokeVersionAutomator()
    automator.run()