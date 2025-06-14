#!/usr/bin/env python3
"""
Modular Karaoke-Version.com Automation Library
Centralizes all automation logic into reusable components
"""

import time
import os
import logging
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import config

# Setup logging (will be reconfigured based on debug mode)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ProgressTracker:
    """Track and display download progress for tracks"""
    
    def __init__(self):
        self.tracks = []
        self.current_song = ""
        self.lock = threading.Lock()
        self._display_thread = None
        self._stop_display = False
    
    def start_song(self, song_name, track_list):
        """Initialize progress tracking for a new song"""
        with self.lock:
            self.current_song = song_name
            self.tracks = []
            
            for track in track_list:
                self.tracks.append({
                    'name': track['name'],
                    'index': track['index'],
                    'status': 'pending',
                    'progress': 0,
                    'file_size': 0,
                    'downloaded': 0,
                    'start_time': None,
                    'end_time': None
                })
        
        # Start display thread
        self._stop_display = False
        self._display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self._display_thread.start()
        
        self._update_display()
    
    def update_track_status(self, track_index, status, progress=None, downloaded=None, file_size=None):
        """Update status of a specific track"""
        with self.lock:
            for track in self.tracks:
                if track['index'] == str(track_index):
                    track['status'] = status
                    if progress is not None:
                        track['progress'] = min(100, max(0, progress))
                    if downloaded is not None:
                        track['downloaded'] = downloaded
                    if file_size is not None:
                        track['file_size'] = file_size
                    if status == 'downloading' and track['start_time'] is None:
                        track['start_time'] = time.time()
                    elif status in ['completed', 'failed'] and track['end_time'] is None:
                        track['end_time'] = time.time()
                    break
        
        self._update_display()
    
    def finish_song(self):
        """Complete progress tracking for current song"""
        self._stop_display = True
        if self._display_thread:
            self._display_thread.join(timeout=1)
        self._final_display()
    
    def _display_loop(self):
        """Background thread to update display periodically"""
        while not self._stop_display:
            time.sleep(0.5)  # Update every 500ms
            if not self._stop_display:
                self._update_display()
    
    def _update_display(self):
        """Update the progress display"""
        with self.lock:
            # Clear screen and show progress
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print(f"🎵 Downloading: {self.current_song}")
            print("=" * 80)
            
            completed = sum(1 for t in self.tracks if t['status'] == 'completed')
            failed = sum(1 for t in self.tracks if t['status'] == 'failed')
            total = len(self.tracks)
            
            print(f"Progress: {completed}/{total} completed, {failed} failed\n")
            
            for track in self.tracks:
                self._display_track_progress(track)
    
    def _display_track_progress(self, track):
        """Display progress for a single track"""
        name = track['name'][:30].ljust(30)  # Truncate/pad name to 30 chars
        status = track['status']
        progress = track['progress']
        
        # Status icon
        if status == 'pending':
            icon = "⏳"
            status_text = "Pending"
        elif status == 'isolating':
            icon = "🎛️"
            status_text = "Isolating"
        elif status == 'downloading':
            icon = "⬇️"
            status_text = "Downloading"
        elif status == 'processing':
            icon = "⚙️"
            status_text = "Processing"
        elif status == 'completed':
            icon = "✅"
            status_text = "Completed"
        elif status == 'failed':
            icon = "❌"
            status_text = "Failed"
        else:
            icon = "❓"
            status_text = status.title()
        
        # Progress bar
        if status == 'downloading' and progress > 0:
            bar_width = 20
            filled = int(bar_width * progress / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            progress_text = f"[{bar}] {progress:3.0f}%"
        elif status == 'completed':
            bar = "█" * 20
            progress_text = f"[{bar}] 100%"
        else:
            bar = "░" * 20
            progress_text = f"[{bar}]   - "
        
        # File size info
        if track['file_size'] > 0:
            size_mb = track['file_size'] / (1024 * 1024)
            downloaded_mb = track['downloaded'] / (1024 * 1024)
            size_text = f"{downloaded_mb:.1f}/{size_mb:.1f} MB"
        else:
            size_text = ""
        
        # Time info
        time_text = ""
        if track['start_time'] and status == 'downloading':
            elapsed = time.time() - track['start_time']
            time_text = f"({elapsed:.0f}s)"
        elif track['start_time'] and track['end_time']:
            duration = track['end_time'] - track['start_time']
            time_text = f"({duration:.0f}s)"
        
        print(f"{icon} {name} {status_text:<12} {progress_text} {size_text:<12} {time_text}")
    
    def _final_display(self):
        """Show final summary"""
        with self.lock:
            completed = [t for t in self.tracks if t['status'] == 'completed']
            failed = [t for t in self.tracks if t['status'] == 'failed']
            
            print(f"\n🎉 Download Summary for: {self.current_song}")
            print("-" * 50)
            print(f"✅ Completed: {len(completed)}")
            print(f"❌ Failed: {len(failed)}")
            print(f"📊 Success Rate: {len(completed)/len(self.tracks)*100:.1f}%")
            
            if failed:
                print("\nFailed tracks:")
                for track in failed:
                    print(f"  ❌ {track['name']}")
            
            total_time = 0
            if completed:
                for track in completed:
                    if track['start_time'] and track['end_time']:
                        total_time += track['end_time'] - track['start_time']
                avg_time = total_time / len(completed)
                print(f"\n⏱️ Average download time: {avg_time:.1f}s per track")
            
            print()

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
    
    def logout(self):
        """Logout from the current session"""
        try:
            # Look for logout/account links
            logout_selectors = [
                "//a[contains(text(), 'Log out')]",
                "//a[contains(text(), 'Logout')]", 
                "//a[contains(text(), 'Sign out')]",
                "//a[contains(text(), 'My Account')]"
            ]
            
            for selector in logout_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        if "my account" in element.text.lower():
                            # Click My Account to access logout
                            element.click()
                            time.sleep(2)
                            # Now look for logout within account area
                            logout_element = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Log out')]")
                            logout_element.click()
                        else:
                            # Direct logout link
                            element.click()
                        
                        time.sleep(3)
                        logging.info("Logout completed")
                        return True
                except:
                    continue
            
            # Alternative: Clear cookies to force logout
            logging.info("Direct logout not found, clearing session cookies")
            self.driver.delete_all_cookies()
            self.driver.refresh()
            time.sleep(3)
            return True
            
        except Exception as e:
            logging.error(f"Error during logout: {e}")
            # Fallback: clear cookies
            try:
                self.driver.delete_all_cookies()
                self.driver.refresh()
                time.sleep(3)
                return True
            except:
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
    
    def login(self, username=None, password=None, force_relogin=False):
        """Complete login process with optimized login checking
        
        Args:
            username (str): Username (uses config if not provided)
            password (str): Password (uses config if not provided)  
            force_relogin (bool): Force re-login even if already logged in
        """
        # Use config credentials if not provided
        if not username:
            username = config.USERNAME
        if not password:
            password = config.PASSWORD
        
        if not username or not password:
            logging.error("Username or password not provided")
            return False
        
        logging.info("Starting optimized login process...")
        
        # Navigate to homepage to check current login status
        self.driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # Check if already logged in (unless forced)
        if not force_relogin and self.is_logged_in():
            logging.info("✅ Already logged in - skipping login process")
            logging.info("💡 Use force_relogin=True to force re-authentication")
            return True
        
        if force_relogin:
            logging.info("🔄 Force re-login requested")
            # If already logged in, need to logout first
            if self.is_logged_in():
                logging.info("Already logged in - logging out first for force re-login")
                if not self.logout():
                    logging.warning("Logout failed, continuing with login attempt")
        
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
        self.progress_tracker = None
    
    def set_progress_tracker(self, progress_tracker):
        """Set the progress tracker for download monitoring"""
        self.progress_tracker = progress_tracker
    
    def ensure_intro_count_enabled(self, song_url):
        """Ensure the intro count checkbox is enabled"""
        try:
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                time.sleep(3)
            
            logging.info("🎼 Checking intro count checkbox...")
            
            # Find the intro count checkbox by ID
            intro_checkbox = self.driver.find_element(By.ID, "precount")
            
            # Check if it's already checked
            is_checked = intro_checkbox.is_selected()
            
            if not is_checked:
                logging.info("📝 Enabling intro count checkbox...")
                try:
                    intro_checkbox.click()
                except Exception as e:
                    if "element click intercepted" in str(e):
                        # Use JavaScript click as fallback
                        logging.info("Click intercepted, using JavaScript click")
                        self.driver.execute_script("arguments[0].click();", intro_checkbox)
                    else:
                        raise e
                
                time.sleep(1)  # Brief pause for UI update
                logging.info("✅ Intro count checkbox enabled")
            else:
                logging.info("✅ Intro count checkbox already enabled")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Error enabling intro count checkbox: {e}")
            return False
    
    def adjust_key(self, song_url, target_key):
        """Adjust the mixer key to the target value"""
        try:
            # Skip if target key is 0 (no adjustment needed)
            if target_key == 0:
                logging.info("🎵 Key adjustment: 0 (no change needed)")
                return True
            
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                time.sleep(3)
            
            logging.info(f"🎵 Adjusting key to: {target_key:+d} semitones")
            
            # Find current key value (should start at 0)
            try:
                # Look for the div that contains the current numeric value
                pitch_container = self.driver.find_element(By.CSS_SELECTOR, ".pitch")
                current_value_element = pitch_container.find_element(By.XPATH, ".//div[text()='0' or text()!='' and not(@class)]")
                current_key = int(current_value_element.text.strip())
                logging.debug(f"Current key value: {current_key}")
            except:
                # Assume starting at 0 if we can't read current value
                current_key = 0
                logging.debug("Could not read current key, assuming 0")
            
            # Calculate how many steps we need
            steps_needed = target_key - current_key
            
            if steps_needed == 0:
                logging.info("✅ Key already at target value")
                return True
            
            # Find the pitch adjustment buttons
            pitch_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.btn--pitch.pitch__button")
            
            if len(pitch_buttons) < 2:
                logging.error("❌ Could not find pitch adjustment buttons")
                return False
            
            # Determine which button is up and which is down by checking onclick
            up_button = None
            down_button = None
            
            for button in pitch_buttons:
                onclick = button.get_attribute('onclick') or ''
                if '+ 1' in onclick:
                    up_button = button
                elif '- 1' in onclick:
                    down_button = button
            
            if not up_button or not down_button:
                logging.error("❌ Could not identify up/down pitch buttons")
                return False
            
            # Click the appropriate button the right number of times
            if steps_needed > 0:
                # Need to go up
                button_to_click = up_button
                direction = "up"
            else:
                # Need to go down
                button_to_click = down_button
                direction = "down"
                steps_needed = abs(steps_needed)
            
            logging.info(f"🔄 Clicking {direction} button {steps_needed} times...")
            
            for step in range(steps_needed):
                try:
                    button_to_click.click()
                except Exception as e:
                    if "element click intercepted" in str(e):
                        # Use JavaScript click as fallback
                        self.driver.execute_script("arguments[0].click();", button_to_click)
                    else:
                        raise e
                
                time.sleep(0.5)  # Small delay between clicks
                logging.debug(f"   Step {step + 1}/{steps_needed}")
            
            # Verify the final key value
            time.sleep(1)  # Wait for UI to update
            try:
                final_value_element = pitch_container.find_element(By.XPATH, ".//div[text()!='' and not(@class) and not(contains(@class, 'pitch__label'))]")
                final_key = int(final_value_element.text.strip())
                if final_key == target_key:
                    logging.info(f"✅ Key successfully adjusted to: {final_key:+d}")
                    return True
                else:
                    logging.warning(f"⚠️ Key adjustment may not be complete. Target: {target_key}, Final: {final_key}")
                    return True  # Still return True as we tried our best
            except:
                logging.info(f"✅ Key adjustment completed (could not verify final value)")
                return True
            
        except Exception as e:
            logging.error(f"❌ Error adjusting key: {e}")
            return False
    
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
        logging.debug(f"Searching for track elements with CSS selector: .track")
        
        track_elements = self.driver.find_elements(By.CSS_SELECTOR, ".track")
        logging.debug(f"Found {len(track_elements)} track elements on page")
        
        tracks = []
        for i, track_element in enumerate(track_elements):
            try:
                caption_element = track_element.find_element(By.CSS_SELECTOR, ".track__caption")
                track_name = caption_element.text.strip()
                data_index = track_element.get_attribute("data-index")
                
                logging.debug(f"Processing track element {i}: data-index='{data_index}', name='{track_name}'")
                
                if track_name and data_index is not None:
                    tracks.append({
                        'name': track_name,
                        'index': data_index,
                        'element': track_element
                    })
                    logging.info(f"Found track {data_index}: '{track_name}'")
                else:
                    logging.debug(f"Skipping track element {i}: missing name or index")
            except Exception as e:
                logging.debug(f"Error processing track element {i}: {e}")
                continue
        
        logging.info(f"Discovered {len(tracks)} tracks")
        logging.debug(f"Track discovery complete for: {song_url}")
        return tracks
    
    def solo_track(self, track_info, song_url):
        """Solo a specific track (mutes all others)"""
        track_name = track_info['name']
        track_index = track_info['index']
        
        logging.info(f"Soloing track {track_index}: {track_name}")
        
        # Update progress tracker
        if self.progress_tracker:
            self.progress_tracker.update_track_status(track_index, 'isolating')
        
        # Navigate to song page if not already there
        if self.driver.current_url != song_url:
            self.driver.get(song_url)
            time.sleep(3)
        
        try:
            # Find the specific track element
            track_selector = f".track[data-index='{track_index}']"
            logging.debug(f"Looking for track element with selector: {track_selector}")
            track_elements = self.driver.find_elements(By.CSS_SELECTOR, track_selector)
            
            if not track_elements:
                logging.error(f"Could not find track element with data-index='{track_index}'")
                logging.debug(f"Available tracks on page: {[el.get_attribute('data-index') for el in self.driver.find_elements(By.CSS_SELECTOR, '.track')]}")
                return False
            
            track_element = track_elements[0]
            logging.debug(f"Found track element for index {track_index}")
            
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
                    logging.debug(f"Trying solo button selector: {selector}")
                    solo_button = track_element.find_element(By.CSS_SELECTOR, selector)
                    if solo_button and solo_button.is_displayed():
                        logging.info(f"Found solo button with selector: {selector}")
                        logging.debug(f"Solo button is displayed: {solo_button.is_displayed()}, enabled: {solo_button.is_enabled()}")
                        break
                except Exception as e:
                    logging.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not solo_button:
                logging.error(f"Could not find solo button for track {track_index}")
                logging.debug(f"Track element HTML: {track_element.get_attribute('outerHTML')[:200]}...")
                return False
            
            # Click the solo button using JavaScript to avoid interception
            logging.info(f"Clicking solo button for {track_name}")
            try:
                # Try regular click first
                solo_button.click()
            except Exception as e:
                if "element click intercepted" in str(e):
                    # Use JavaScript click as fallback
                    logging.info("Click intercepted, using JavaScript click")
                    self.driver.execute_script("arguments[0].click();", solo_button)
                else:
                    raise e
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
    
    def download_current_mix(self, song_url, track_name="current_mix", cleanup_existing=True, song_folder=None):
        """Download the current track mix (after soloing)
        
        Args:
            song_url (str): URL of the song page
            track_name (str): Name for the downloaded file
            cleanup_existing (bool): Remove existing files before download
            song_folder (str): Optional specific folder name for the song
        """
        # Extract or create song folder name
        if not song_folder:
            song_folder = self._extract_song_folder_name(song_url)
        
        logging.info(f"Downloading current mix: {track_name} to folder: {song_folder}")
        
        # Update progress tracker
        track_index = None
        if self.progress_tracker:
            # Find track by name to get index
            for track in self.progress_tracker.tracks:
                if track_name.lower() in track['name'].lower() or track['name'].lower() in track_name.lower():
                    track_index = track['index']
                    break
            
            if track_index:
                self.progress_tracker.update_track_status(track_index, 'downloading')
        
        # Create song-specific folder and update download path
        song_path = self._setup_song_folder(song_folder)
        
        # Update Chrome download directory to song folder BEFORE clicking download
        try:
            self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': str(song_path.absolute())
            })
            logging.info(f"✅ Updated Chrome download path to: {song_path}")
        except Exception as e:
            logging.warning(f"⚠️ Could not update Chrome download path: {e}")
            logging.info(f"💡 Files may download to default location and will be moved automatically")
        
        # Store song path for backup file moving
        self.song_path = song_path
        
        # Clean up existing downloads if requested (within song folder)
        # TEMPORARILY COMMENTED OUT - testing if this causes file deletion issues
        # if cleanup_existing:
        #     self._cleanup_existing_downloads(track_name, song_path)
        
        try:
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                time.sleep(3)
            
            # Find the download button - discovered selector
            download_selectors = [
                "a.download",  # Primary discovered selector
                "a[class*='download']",
                "//a[contains(@class, 'download')]",
                "//a[contains(text(), 'Download')]",
                "//a[contains(text(), 'MP3')]"
            ]
            
            logging.debug(f"Searching for download button with {len(download_selectors)} selectors")
            
            download_button = None
            for i, selector in enumerate(download_selectors):
                try:
                    logging.debug(f"Trying download selector {i+1}/{len(download_selectors)}: {selector}")
                    if selector.startswith("//"):
                        from selenium.webdriver.common.by import By
                        download_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        from selenium.webdriver.common.by import By
                        download_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if download_button and download_button.is_displayed() and download_button.is_enabled():
                        logging.info(f"Found download button with selector: {selector}")
                        logging.debug(f"Download button displayed: {download_button.is_displayed()}, enabled: {download_button.is_enabled()}")
                        break
                    else:
                        logging.debug(f"Download button found but not usable (displayed: {download_button.is_displayed()}, enabled: {download_button.is_enabled()})")
                        download_button = None
                except Exception as e:
                    logging.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not download_button:
                logging.error("Could not find download button")
                logging.debug("Available download-related elements on page:")
                try:
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    download_links = [link for link in all_links if 'download' in link.get_attribute('class').lower() or 'download' in link.text.lower()]
                    for link in download_links[:5]:  # Show first 5 matches
                        logging.debug(f"  - {link.tag_name} class='{link.get_attribute('class')}' text='{link.text[:30]}'")
                except:
                    pass
                return False
            
            # Get button details for logging
            button_text = download_button.text.strip()
            button_onclick = download_button.get_attribute('onclick') or ''
            
            logging.info(f"Download button text: '{button_text}'")
            if button_onclick:
                logging.info(f"Download onclick: {button_onclick[:50]}...")
            
            # Scroll to download button and click
            logging.info("Clicking download button...")
            try:
                # Scroll element into view first
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
                time.sleep(1)
                
                # Try regular click first
                download_button.click()
                logging.info("✅ Download button clicked successfully")
            except Exception as e:
                if "element click intercepted" in str(e):
                    # Use JavaScript click as fallback
                    logging.info("Click intercepted, using JavaScript click")
                    self.driver.execute_script("arguments[0].click();", download_button)
                    logging.info("✅ Download button clicked via JavaScript")
                else:
                    raise e
            
            # Give a moment for any immediate response
            time.sleep(2)
            
            # Check if any popup or new window appeared
            original_window_count = len(self.driver.window_handles)
            logging.debug(f"Windows before download: {original_window_count}")
            
            # Wait a moment and check again
            time.sleep(3)
            current_window_count = len(self.driver.window_handles)
            logging.debug(f"Windows after download: {current_window_count}")
            
            if current_window_count > original_window_count:
                logging.info(f"🪟 New window/popup detected ({current_window_count} vs {original_window_count})")
                # Switch to new window to see what it contains
                try:
                    new_window = self.driver.window_handles[-1]
                    self.driver.switch_to.window(new_window)
                    logging.info(f"📄 New window title: {self.driver.title}")
                    logging.info(f"📄 New window URL: {self.driver.current_url}")
                    
                    # Look for download-related text
                    page_text = self.driver.page_source.lower()
                    if any(phrase in page_text for phrase in ['download', 'generating', 'preparing', 'your file']):
                        logging.info("🎵 Download generation page detected!")
                    
                    # Switch back to original window
                    self.driver.switch_to.window(self.driver.window_handles[0])
                except Exception as e:
                    logging.warning(f"Could not inspect new window: {e}")
                    try:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                    except:
                        pass
            
            # Update progress tracker to indicate we're waiting for download to start
            if self.progress_tracker and track_index:
                self.progress_tracker.update_track_status(track_index, 'processing')
            
            # Wait for download to actually start (critical for proper sequencing)
            logging.info(f"⏳ Waiting for download to start for: {track_name}")
            download_started = self._wait_for_download_to_start(track_name, track_index)
            
            if download_started:
                logging.info(f"✅ Download started for: {track_name} - proceeding to next track")
                
                # Start background monitoring for completion and file cleanup
                self._schedule_download_completion_monitoring(song_path, track_name, track_index)
                
            else:
                logging.warning(f"⚠️ Download not detected for: {track_name}")
                
                # Since we're only monitoring song folder, no download detected means failure
                logging.error(f"❌ No download detected in song folder for: {track_name}")
                if self.progress_tracker and track_index:
                    self.progress_tracker.update_track_status(track_index, 'failed')
                return False
            
            # Don't mark as completed immediately since downloads continue in background
            # Progress will be updated when we check for completion later or in next iteration
            
            return True
            
        except Exception as e:
            # Update progress tracker to failed
            if self.progress_tracker and track_index:
                self.progress_tracker.update_track_status(track_index, 'failed')
            logging.error(f"Error downloading mix: {e}")
            return False
    
    def _extract_song_folder_name(self, song_url):
        """Extract song information from URL to create folder name"""
        try:
            # Extract from URL pattern: /custombackingtrack/artist/song.html
            url_parts = song_url.rstrip('/').split('/')
            if len(url_parts) >= 3 and 'custombackingtrack' in url_parts:
                artist_part = url_parts[-2] if len(url_parts) >= 2 else 'unknown_artist'
                song_part = url_parts[-1].replace('.html', '') if len(url_parts) >= 1 else 'unknown_song'
                
                # Clean up names
                artist = artist_part.replace('-', ' ').title()
                song = song_part.replace('-', ' ').title()
                
                folder_name = f"{artist} - {song}"
                return self._sanitize_folder_name(folder_name)
            
            # Fallback: use domain and timestamp
            return f"karaoke_download_{int(time.time())}"
            
        except Exception as e:
            logging.warning(f"Could not extract song info from URL: {e}")
            return f"karaoke_download_{int(time.time())}"
    
    def _sanitize_folder_name(self, folder_name):
        """Clean folder name for filesystem compatibility"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            folder_name = folder_name.replace(char, '_')
        
        # Limit length and clean up
        folder_name = folder_name[:100].strip()
        if not folder_name:
            folder_name = f"song_{int(time.time())}"
        
        return folder_name
    
    def _setup_song_folder(self, song_folder_name):
        """Create song-specific folder in downloads directory"""
        try:
            base_download_folder = Path(config.DOWNLOAD_FOLDER)
            song_path = base_download_folder / song_folder_name
            song_path.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"Song folder ready: {song_path}")
            return song_path
            
        except Exception as e:
            logging.error(f"Error creating song folder: {e}")
            # Fallback to base download folder
            return Path(config.DOWNLOAD_FOLDER)
    
    def _cleanup_existing_downloads(self, track_name, download_folder=None):
        """Remove existing files that might conflict with new download"""
        try:
            if download_folder is None:
                download_folder = Path(config.DOWNLOAD_FOLDER)
            else:
                download_folder = Path(download_folder)
                
            if not download_folder.exists():
                return
            
            # Only clean up files that are likely duplicates of what we're about to download
            # Use correct file extensions (.aif is primary, .mp3 as backup)
            removed_files = []
            
            # Look for files that match the track name specifically
            for file_path in download_folder.iterdir():
                if file_path.is_file():
                    filename = file_path.name.lower()
                    track_lower = track_name.lower()
                    
                    # Check if it's an audio file that matches this track
                    is_audio = any(filename.endswith(ext) for ext in ['.aif', '.mp3', '.wav', '.m4a'])
                    matches_track = track_lower in filename or any(word in filename for word in track_lower.split('_'))
                    has_backing_track_suffix = 'custom_backing_track' in filename or 'backing_track' in filename
                    
                    if is_audio and (matches_track or has_backing_track_suffix):
                        # Only remove if it's older than 30 seconds (avoid removing active downloads)
                        file_age = time.time() - file_path.stat().st_mtime
                        if file_age > 30:  # Only remove files older than 30 seconds
                            try:
                                file_path.unlink()
                                removed_files.append(file_path.name)
                                logging.info(f"Removed existing file: {file_path.name}")
                            except Exception as e:
                                logging.warning(f"Could not remove {file_path.name}: {e}")
                        else:
                            logging.debug(f"Skipping recent file (may be downloading): {file_path.name}")
            
            if removed_files:
                logging.info(f"Cleaned up {len(removed_files)} existing files")
            else:
                logging.debug("No existing files to clean up")
                
        except Exception as e:
            logging.warning(f"Error during download cleanup: {e}")
    
    def _wait_for_download_to_start(self, track_name, track_index=None):
        """Wait for download to actually start by monitoring song folder only"""
        try:
            # Only monitor the song folder since Chrome downloads directly there
            song_path = getattr(self, 'song_path', None)
            
            if not song_path or not song_path.exists():
                logging.error(f"Song folder not available for monitoring: {song_path}")
                return False
            
            paths_to_monitor = [song_path]
            logging.info(f"🔍 Monitoring song folder: {song_path}")
            
            # Get initial file lists for all paths
            initial_files_by_path = {}
            initial_counts = {}
            
            for path in paths_to_monitor:
                try:
                    all_files = list(path.iterdir())
                    files = {f.name for f in all_files if f.is_file()}
                    initial_files_by_path[path] = files
                    initial_counts[path] = len(files)
                    logging.info(f"📊 Initial {path.name}: {len(files)} files")
                except PermissionError:
                    logging.warning(f"Permission denied accessing {path}")
                    continue
            
            # Wait for new files to appear (indicating download started)
            max_wait = 60  # 60 seconds max wait for download to start
            check_interval = 2  # Check every 2 seconds
            waited = 0
            
            logging.info(f"⏳ Waiting up to {max_wait} seconds for download to start...")
            
            while waited < max_wait:
                time.sleep(check_interval)
                waited += check_interval
                
                # Check all monitored paths for new files
                for path in paths_to_monitor:
                    try:
                        current_files = {f.name for f in path.iterdir() if f.is_file()}
                        current_count = len(current_files)
                        initial_files = initial_files_by_path.get(path, set())
                        initial_count = initial_counts.get(path, 0)
                        new_files = current_files - initial_files
                        
                        # Log any change in file count
                        if current_count != initial_count:
                            logging.info(f"📈 {path.name} file count changed: {initial_count} → {current_count}")
                            
                        # Look for any new files that could be our download
                        for filename in new_files:
                            logging.info(f"🆕 New file detected in {path.name}: {filename}")
                            
                            # Check for karaoke-related patterns or Chrome download indicators
                            is_karaoke_file = any(indicator in filename.lower() for indicator in [
                                'custom_backing_track', 'backing_track', 'karaoke',
                                track_name.lower().replace('_', '').replace('-', ''),
                                '.crdownload',  # Chrome partial download indicator
                                '.aif', '.mp3', '.wav', '.m4a'  # Audio file extensions
                            ])
                            
                            # Also check for any audio file or download-related file
                            is_audio_or_download = any(ext in filename.lower() for ext in [
                                '.aif', '.mp3', '.wav', '.m4a', '.crdownload', '.download', '.tmp'
                            ])
                            
                            if is_karaoke_file or is_audio_or_download:
                                logging.info(f"✅ Download started - detected relevant file in {path.name}: {filename}")
                                
                                # Update progress tracker if available
                                if self.progress_tracker and track_index:
                                    if '.crdownload' in filename.lower():
                                        self.progress_tracker.update_track_status(track_index, 'downloading', progress=25)
                                    else:
                                        self.progress_tracker.update_track_status(track_index, 'downloading', progress=50)
                                
                                return True
                            else:
                                logging.debug(f"🔍 New file not relevant: {filename}")
                    
                    except PermissionError:
                        logging.warning(f"Permission error checking {path}")
                        continue
                    except Exception as e:
                        logging.warning(f"Error checking {path}: {e}")
                        continue
                
                # Show progress every 10 seconds
                if waited % 10 == 0:
                    logging.info(f"⏳ Still waiting for download to start... ({waited}s elapsed)")
                    for path in paths_to_monitor:
                        try:
                            count = len([f for f in path.iterdir() if f.is_file()])
                            logging.debug(f"📊 Current files in {path.name}: {count}")
                        except:
                            pass
            
            logging.warning(f"⚠️ Download did not start within {max_wait} seconds")
            logging.info(f"📊 Final folder checks:")
            for path in paths_to_monitor:
                try:
                    final_files = {f.name for f in path.iterdir() if f.is_file()}
                    initial_files = initial_files_by_path.get(path, set())
                    final_new = final_files - initial_files
                    if final_new:
                        logging.info(f"🔍 New files in {path.name}: {list(final_new)}")
                    else:
                        logging.info(f"🔍 No new files in {path.name}")
                except:
                    pass
                
            return False
            
        except Exception as e:
            logging.error(f"Error waiting for download to start: {e}")
            return False

    def _check_song_folder_for_new_files(self, song_path, track_name):
        """Check if new files appeared directly in the song folder (Chrome path worked)"""
        try:
            if not song_path.exists():
                return False
            
            # Check for recent audio files in song folder
            for file_path in song_path.iterdir():
                if file_path.is_file():
                    # Check if it's an audio file
                    if any(file_path.name.lower().endswith(ext) for ext in ['.aif', '.mp3', '.wav', '.m4a']):
                        # Check if it's recent (less than 30 seconds old)
                        file_age = time.time() - file_path.stat().st_mtime
                        if file_age < 30:
                            logging.info(f"📁 Found recent file in song folder: {file_path.name} ({file_age:.1f}s old)")
                            return True
            
            return False
            
        except Exception as e:
            logging.debug(f"Error checking song folder: {e}")
            return False

    def _check_alternative_download_locations(self, track_name):
        """Check for downloads in alternative locations"""
        logging.info(f"🔍 Checking alternative download locations for: {track_name}")
        
        alternative_paths = [
            Path.home() / "Desktop",
            Path.home() / "Documents", 
            Path.home() / "Music",
            Path("/tmp"),
            Path("/var/folders").glob("*/*/T") if Path("/var/folders").exists() else []
        ]
        
        # Flatten the glob results
        paths_to_check = []
        for path in alternative_paths:
            if isinstance(path, Path):
                paths_to_check.append(path)
            else:  # It's a generator from glob
                paths_to_check.extend(list(path))
        
        for path in paths_to_check:
            if path.exists():
                try:
                    audio_files = list(path.glob("*.aif")) + list(path.glob("*.mp3")) + list(path.glob("*.wav"))
                    recent_files = [f for f in audio_files if (time.time() - f.stat().st_mtime) < 300]  # Last 5 minutes
                    
                    if recent_files:
                        logging.info(f"🎵 Found recent audio files in {path}:")
                        for f in recent_files:
                            age = time.time() - f.stat().st_mtime
                            logging.info(f"  - {f.name} ({age:.0f}s ago)")
                except:
                    continue

    def _schedule_download_completion_monitoring(self, song_path, track_name, track_index):
        """Start background monitoring for download completion and file cleanup"""
        import threading
        
        def completion_monitor():
            try:
                # Monitor for up to 5 minutes for download completion
                max_wait = 300  # 5 minutes
                check_interval = 2  # Check every 2 seconds
                waited = 0
                
                logging.debug(f"Starting completion monitoring for {track_name}")
                
                while waited < max_wait:
                    time.sleep(check_interval)
                    waited += check_interval
                    
                    # Look for .crdownload files that have completed
                    completed_files = self._check_for_completed_downloads(song_path, track_name)
                    
                    if completed_files:
                        logging.info(f"🎉 Download completed for {track_name}: {len(completed_files)} files")
                        
                        # Clean up filenames
                        for file_path in completed_files:
                            self._clean_filename_after_download(file_path)
                        
                        # Update progress tracker
                        if self.progress_tracker and track_index:
                            self.progress_tracker.update_track_status(track_index, 'completed', progress=100)
                        
                        break
                    
                    # Update progress periodically for ongoing downloads
                    if waited % 20 == 0 and self.progress_tracker and track_index:  # Every 20 seconds
                        # Check if we still have .crdownload files (download in progress)
                        crdownload_files = list(song_path.glob("*.crdownload"))
                        if crdownload_files:
                            # Calculate rough progress based on time elapsed
                            progress = min(95, 25 + (waited / max_wait) * 70)  # 25% to 95%
                            self.progress_tracker.update_track_status(track_index, 'downloading', progress=progress)
                
                # Timeout handling
                if waited >= max_wait:
                    logging.warning(f"⚠️ Download completion monitoring timed out for {track_name}")
                    if self.progress_tracker and track_index:
                        self.progress_tracker.update_track_status(track_index, 'failed')
                        
            except Exception as e:
                logging.error(f"Error in completion monitoring for {track_name}: {e}")
                if self.progress_tracker and track_index:
                    self.progress_tracker.update_track_status(track_index, 'failed')
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=completion_monitor, daemon=True)
        monitor_thread.start()
        logging.debug(f"Started background completion monitoring for {track_name}")
    
    def _check_for_completed_downloads(self, song_path, track_name):
        """Check for files that have completed downloading (no more .crdownload)"""
        try:
            if not song_path.exists():
                return []
            
            completed_files = []
            
            # Look for audio files that don't have .crdownload extension
            for file_path in song_path.iterdir():
                if file_path.is_file():
                    filename = file_path.name.lower()
                    
                    # Check if it's an audio file (not .crdownload)
                    is_audio = any(filename.endswith(ext) for ext in ['.mp3', '.aif', '.wav', '.m4a'])
                    is_recent = (time.time() - file_path.stat().st_mtime) < 120  # Less than 2 minutes old
                    
                    # Check if it looks like a karaoke file
                    is_karaoke = any(indicator in filename for indicator in [
                        'custom_backing_track', 'backing_track', 'karaoke'
                    ])
                    
                    if is_audio and is_recent and is_karaoke:
                        # Make sure there's no corresponding .crdownload file
                        crdownload_path = file_path.with_suffix(file_path.suffix + '.crdownload')
                        if not crdownload_path.exists():
                            completed_files.append(file_path)
                            logging.debug(f"Found completed download: {file_path.name}")
            
            return completed_files
            
        except Exception as e:
            logging.debug(f"Error checking for completed downloads: {e}")
            return []
    
    def _clean_filename_after_download(self, file_path):
        """Remove '_Custom_Backing_Track' from completed download filename"""
        try:
            original_name = file_path.name
            
            # Remove '_Custom_Backing_Track' pattern
            new_name = original_name.replace('_Custom_Backing_Track', '')
            
            # Clean up any resulting double parentheses or underscores
            new_name = new_name.replace('()', '')  # Remove empty parentheses
            new_name = new_name.replace('__', '_')  # Fix double underscores
            new_name = new_name.replace('_.', '.')  # Fix underscore before extension
            
            # Only rename if the name actually changed
            if new_name != original_name:
                new_path = file_path.parent / new_name
                
                # Avoid overwriting existing files
                counter = 1
                final_path = new_path
                while final_path.exists():
                    name_part = new_path.stem
                    ext_part = new_path.suffix
                    final_path = file_path.parent / f"{name_part}_{counter}{ext_part}"
                    counter += 1
                
                file_path.rename(final_path)
                logging.info(f"📝 Cleaned filename: '{original_name}' → '{final_path.name}'")
                return final_path
            else:
                logging.debug(f"Filename already clean: {original_name}")
                return file_path
                
        except Exception as e:
            logging.warning(f"Could not clean filename for {file_path.name}: {e}")
            return file_path

    def _clean_downloaded_filename(self, original_filename, track_name):
        """Clean up downloaded filename to be more readable"""
        try:
            # Remove common unwanted patterns
            clean_name = original_filename
            
            # Patterns to remove
            patterns_to_remove = [
                r'_Custom_Backing_Track',
                r'Custom_Backing_Track_?',
                r'\(Custom_Backing_Track\)',
                r'_custom_backing_track',
                r'.*?\((.*?)\).*Custom_Backing_Track.*',  # Extract content from parentheses
            ]
            
            import re
            for pattern in patterns_to_remove:
                clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
            
            # Clean up formatting
            clean_name = re.sub(r'_+', '_', clean_name)  # Multiple underscores
            clean_name = re.sub(r'-+', '-', clean_name)  # Multiple dashes
            clean_name = clean_name.strip('_-. ')  # Leading/trailing chars
            
            # If name becomes too short, use track name
            if len(clean_name) < 5 or clean_name in ['.aif', '.mp3', '.wav']:
                clean_name = f"{track_name}.aif"
            
            # Ensure it has an extension
            if not any(clean_name.endswith(ext) for ext in ['.aif', '.mp3', '.wav', '.m4a']):
                clean_name += '.aif'  # Default to aif based on what we observed
            
            return clean_name
            
        except Exception as e:
            logging.debug(f"Error cleaning filename: {e}")
            # Fallback to track name
            return f"{track_name}.aif"

    def _schedule_filename_cleanup(self, song_path, track_name):
        """Schedule cleanup of downloaded filenames to remove unwanted suffixes"""
        import threading
        import time
        
        def cleanup_worker():
            # Wait for download to complete (check every 2 seconds for up to 30 seconds)
            max_wait = 30
            check_interval = 2
            waited = 0
            
            while waited < max_wait:
                time.sleep(check_interval)
                waited += check_interval
                
                # Look for newly downloaded files
                try:
                    if self._cleanup_downloaded_filenames(song_path, track_name):
                        logging.info("✅ Filename cleanup completed")
                        break
                except Exception as e:
                    logging.debug(f"Filename cleanup attempt failed: {e}")
            
            if waited >= max_wait:
                logging.debug("Filename cleanup timed out - file may still be downloading")
        
        # Start cleanup in background thread
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logging.debug("Scheduled filename cleanup in background thread")
    
    def _cleanup_downloaded_filenames(self, song_path, track_name):
        """Clean up downloaded filenames by removing unwanted suffixes"""
        try:
            song_folder = Path(song_path)
            if not song_folder.exists():
                return False
            
            # Patterns to clean up
            cleanup_patterns = [
                "_Custom_Backing_Track",
                "(Custom_Backing_Track)",
                "_Custom_Backing_Track_",
                "(Custom Backing Track)",
                "_custom_backing_track",
                "Custom_Backing_Track"
            ]
            
            files_cleaned = 0
            
            # Look for recently downloaded MP3 files
            for file_path in song_folder.glob("*.mp3"):
                # Check if file is recent (less than 60 seconds old)
                file_age = time.time() - file_path.stat().st_mtime
                if file_age > 60:  # Skip old files
                    continue
                
                original_name = file_path.name
                new_name = original_name
                
                # Remove unwanted patterns
                for pattern in cleanup_patterns:
                    if pattern in new_name:
                        new_name = new_name.replace(pattern, "")
                        logging.debug(f"Removed pattern '{pattern}' from filename")
                
                # Clean up any double extensions or weird formatting
                new_name = new_name.replace(".mp3.mp3", ".mp3")  # Fix double extensions
                
                # Fix multiple underscores/dashes iteratively
                while "__" in new_name:
                    new_name = new_name.replace("__", "_")
                while "--" in new_name:
                    new_name = new_name.replace("--", "-")
                
                new_name = new_name.replace("()", "")   # Remove empty parentheses
                new_name = new_name.strip("_-. ")       # Trim leading/trailing chars
                
                # Handle edge case where name becomes empty or just extension
                if not new_name or new_name in [".mp3", "mp3"]:
                    # Use track name as fallback
                    new_name = f"{track_name}_cleaned.mp3"
                
                # Ensure it still has .mp3 extension
                if not new_name.endswith(".mp3"):
                    new_name += ".mp3"
                
                # Rename if changed
                if new_name != original_name:
                    new_path = song_folder / new_name
                    
                    # Avoid overwriting existing files
                    counter = 1
                    final_name = new_name
                    while new_path.exists():
                        name_part = new_name.replace(".mp3", "")
                        final_name = f"{name_part}_{counter}.mp3"
                        new_path = song_folder / final_name
                        counter += 1
                    
                    try:
                        file_path.rename(new_path)
                        logging.info(f"📝 Cleaned filename: '{original_name}' → '{final_name}'")
                        files_cleaned += 1
                    except Exception as e:
                        logging.warning(f"Could not rename {original_name}: {e}")
            
            return files_cleaned > 0
            
        except Exception as e:
            logging.debug(f"Error during filename cleanup: {e}")
            return False


class KaraokeVersionAutomator:
    """Main automation class that coordinates all functionality"""
    
    def __init__(self, headless=False, show_progress=True):
        """
        Initialize automator
        
        Args:
            headless (bool): Run browser in headless mode (True) or visible mode (False)
            show_progress (bool): Show progress bar during downloads (True) or use simple logging (False)
        """
        self.headless = headless
        self.show_progress = show_progress
        self.progress = ProgressTracker() if show_progress else None
        self.setup_driver()
        self.setup_folders()
        self.login_handler = KaraokeVersionLogin(self.driver, self.wait)
        self.track_handler = KaraokeVersionTracker(self.driver, self.wait)
        
        # Pass progress tracker to track handler
        if self.progress:
            self.track_handler.set_progress_tracker(self.progress)
    
    def setup_driver(self):
        """Initialize Chrome driver with headless option support"""
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
        
        # Initial download preferences (will be updated per song)
        prefs = {
            "download.default_directory": os.path.abspath(config.DOWNLOAD_FOLDER),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        logging.debug(f"Chrome download directory: {os.path.abspath(config.DOWNLOAD_FOLDER)}")
        logging.debug("Chrome preferences configured for automatic downloads")
        
        try:
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
                    service = Service(path)
                    break
            
            # Fallback to webdriver-manager if no local version found
            if not service:
                logging.info("⏳ No local ChromeDriver found, downloading...")
                try:
                    service = Service(ChromeDriverManager().install())
                    logging.info("✅ ChromeDriver downloaded successfully")
                except Exception as e:
                    logging.error(f"❌ ChromeDriver download failed: {e}")
                    logging.error("💡 Please install ChromeDriver manually:")
                    logging.error("   macOS: brew install chromedriver")
                    logging.error("   Then run: xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver")
                    logging.error("   Test with: python test_chrome_quick.py")
                    raise Exception("ChromeDriver not available")
            
            logging.info("⏳ Starting Chrome browser...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            logging.info("✅ Chrome browser started successfully")
            
        except Exception as e:
            logging.error(f"❌ Failed to start Chrome browser: {e}")
            logging.error("💡 Troubleshooting tips:")
            logging.error("   1. Make sure Chrome is installed: https://www.google.com/chrome/")
            logging.error("   2. Try updating Chrome to the latest version")  
            logging.error("   3. Run manual setup: python manual_chromedriver_setup.py")
            logging.error("   4. Install via Homebrew: brew install chromedriver")
            logging.error("   5. Check your internet connection")
            raise
    
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
                song_key = song.get('key', 0)  # Get key adjustment value
                
                # Log song configuration
                if song_key != 0:
                    logging.info(f"🎵 Song configuration - Key: {song_key:+d} semitones")
                else:
                    logging.info(f"🎵 Song configuration - Key: no adjustment")
                
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
                    
                    # Start progress tracking for this song
                    if self.progress:
                        self.progress.start_song(song['name'], tracks)
                    
                    # Setup mixer controls once per song
                    logging.info("🎛️ Setting up mixer controls...")
                    
                    # Ensure intro count is enabled
                    intro_success = self.track_handler.ensure_intro_count_enabled(song['url'])
                    if not intro_success:
                        logging.warning("⚠️ Could not enable intro count - continuing anyway")
                    
                    # Adjust key if needed
                    if song_key != 0:
                        key_success = self.track_handler.adjust_key(song['url'], song_key)
                        if not key_success:
                            logging.warning(f"⚠️ Could not adjust key to {song_key:+d} - continuing with default key")
                    
                    # Download each track individually
                    for track in tracks:
                        track_name = self.sanitize_filename(track['name'])
                        
                        # Solo this track
                        if self.solo_track(track, song['url']):
                            # Download the soloed track
                            success = self.track_handler.download_current_mix(
                                song['url'], 
                                track_name,
                                cleanup_existing=True,
                                song_folder=song.get('name', 'unknown_song')
                            )
                            
                            if not success:
                                logging.error(f"Failed to download {track_name}")
                        else:
                            logging.error(f"Failed to solo track {track_name}")
                            if self.progress:
                                self.progress.update_track_status(track['index'], 'failed')
                        
                        # Brief pause between tracks
                        time.sleep(2)
                    
                    # Clear all solos when done
                    self.clear_all_solos(song['url'])
                    
                    # Finish progress tracking for this song
                    if self.progress:
                        self.progress.finish_song()
                        
                else:
                    logging.error(f"No tracks found for {song['name']}")
            
            logging.info("Automation completed")
            return True
            
        except Exception as e:
            logging.error(f"Automation failed: {e}")
            return False
        finally:
            self.driver.quit()


def setup_logging(debug_mode):
    """Setup logging configuration based on debug mode"""
    # Clear existing handlers
    logging.getLogger().handlers.clear()
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    if debug_mode:
        # Debug mode: detailed logs to file, minimal to console
        logging.getLogger().setLevel(logging.DEBUG)
        
        # File handler for all debug output
        file_handler = logging.FileHandler('logs/debug.log', mode='w')  # Overwrite each run
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logging.getLogger().addHandler(file_handler)
        
        # Console handler for important messages only (so progress bar works)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        console_handler.setFormatter(simple_formatter)
        logging.getLogger().addHandler(console_handler)
        
        logging.info("🐛 Debug mode enabled - detailed logs in logs/debug.log")
        logging.info("👁️ Browser will be visible, progress bar on console")
        
    else:
        # Production mode: normal logging to both file and console
        logging.getLogger().setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler('logs/automation.log')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        logging.getLogger().addHandler(file_handler)
        
        # Console handler  
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logging.getLogger().addHandler(console_handler)
        
        logging.info("🚀 Running in production mode - headless browser")

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Karaoke-Version.com Track Automation')
    parser.add_argument('--debug', action='store_true', 
                       help='Run in debug mode with visible browser and detailed file logging')
    args = parser.parse_args()
    
    # Setup logging based on debug mode
    setup_logging(args.debug)
    
    # Set browser mode
    headless_mode = not args.debug
    
    # Initialize automator with appropriate mode
    automator = KaraokeVersionAutomator(headless=headless_mode)
    automator.run_automation()