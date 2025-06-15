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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from packages.configuration import ConfigurationManager
from packages.browser import ChromeManager
from packages.authentication import LoginManager
from packages.progress import ProgressTracker
from packages.file_operations import FileManager

# Setup logging (will be reconfigured based on debug mode)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)



class KaraokeVersionTracker:
    """Handles track discovery and manipulation"""
    
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait
        self.progress_tracker = None
        self.file_manager = FileManager()
    
    def set_progress_tracker(self, progress_tracker):
        """Set the progress tracker for download monitoring"""
        self.progress_tracker = progress_tracker
    
    def set_chrome_manager(self, chrome_manager):
        """Set the chrome manager for download path management"""
        self.chrome_manager = chrome_manager
    
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
    
    def download_current_mix(self, song_url, track_name="current_mix", cleanup_existing=True, song_folder=None, key_adjustment=0):
        """Download the current track mix (after soloing)
        
        Args:
            song_url (str): URL of the song page
            track_name (str): Name for the downloaded file
            cleanup_existing (bool): Remove existing files before download
            song_folder (str): Optional specific folder name for the song
            key_adjustment (int): Key adjustment applied to the track (-12 to +12)
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
        song_path = self.file_manager.setup_song_folder(song_folder)
        
        # Update Chrome download directory to song folder BEFORE clicking download
        try:
            if hasattr(self, 'chrome_manager') and self.chrome_manager:
                self.chrome_manager.set_download_path(song_path.absolute())
            else:
                # Fallback to direct CDP command
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
                        download_button = self.driver.find_element(By.XPATH, selector)
                    else:
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
            download_started = self.file_manager.wait_for_download_to_start(track_name, song_path, track_index)
            
            if download_started:
                logging.info(f"✅ Download started for: {track_name} - proceeding to next track")
                
                # Start background monitoring for completion and file cleanup
                self._start_completion_monitoring(song_path, track_name, track_index)
                
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
    
    def _sanitize_filesystem_name(self, name):
        """Remove invalid filesystem characters"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name
    
    def _sanitize_folder_name(self, folder_name):
        """Clean folder name for filesystem compatibility"""
        folder_name = self._sanitize_filesystem_name(folder_name)
        
        # Limit length and clean up
        folder_name = folder_name[:100].strip()
        if not folder_name:
            folder_name = f"song_{int(time.time())}"
        
        return folder_name
    
    def _start_completion_monitoring(self, song_path, track_name, track_index):
        """Start background monitoring for download completion and file cleanup"""
        
        def completion_monitor():
            try:
                # Monitor for up to 5 minutes for download completion
                max_wait = 300  # 5 minutes
                check_interval = 2  # Check every 2 seconds
                waited = 0
                
                logging.info(f"🔍 Starting completion monitoring for {track_name}")
                
                while waited < max_wait:
                    time.sleep(check_interval)
                    waited += check_interval
                    
                    # Look for completed downloads
                    logging.info(f"🔍 Checking for completed downloads in {song_path}")
                    completed_files = self.file_manager.check_for_completed_downloads(song_path, track_name)
                    
                    if not completed_files:
                        logging.info(f"   No completed files found yet (waited {waited}s)")
                    
                    if completed_files:
                        logging.info(f"🎉 Download completed for {track_name}: {len(completed_files)} files")
                        
                        # Clean up filenames by removing '_Custom_Backing_Track'
                        for file_path in completed_files:
                            self.file_manager.clean_downloaded_filename(file_path)
                        
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
        logging.info(f"🎆 Started background completion monitoring for {track_name}")


class KaraokeVersionAutomator:
    """Main automation class that coordinates all functionality"""
    
    def __init__(self, headless=False, show_progress=True, config_file="songs.yaml"):
        """
        Initialize automator
        
        Args:
            headless (bool): Run browser in headless mode (True) or visible mode (False)
            show_progress (bool): Show progress bar during downloads (True) or use simple logging (False)
            config_file (str): Path to songs configuration file
        """
        self.headless = headless
        self.show_progress = show_progress
        self.config_manager = ConfigurationManager(config_file)
        self.progress = ProgressTracker() if show_progress else None
        
        # Initialize browser manager
        self.chrome_manager = ChromeManager(headless=headless)
        self.chrome_manager.setup_driver()
        self.chrome_manager.setup_folders()
        
        # Get driver and wait from chrome manager
        self.driver = self.chrome_manager.driver
        self.wait = self.chrome_manager.wait
        
        self.login_handler = LoginManager(self.driver, self.wait)
        self.track_handler = KaraokeVersionTracker(self.driver, self.wait)
        
        # Pass chrome manager and progress tracker to track handler
        self.track_handler.set_chrome_manager(self.chrome_manager)
        if self.progress:
            self.track_handler.set_progress_tracker(self.progress)
    
    
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
        return self.config_manager.load_songs_config()
    
    def validate_configuration(self):
        """Validate the configuration file"""
        return self.config_manager.validate_configuration_file()
    
    def get_configuration_summary(self):
        """Get configuration summary"""
        return self.config_manager.get_configuration_summary()
    
    def sanitize_filename(self, filename):
        """Clean filename for saving"""
        return self.track_handler._sanitize_filesystem_name(filename)
    
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
                                song_folder=song.get('name'),  # None if not specified, triggers URL extraction
                                key_adjustment=song_key
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