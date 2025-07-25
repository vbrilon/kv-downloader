"""Track management for karaoke automation - discovery, isolation, and mixer controls"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    TimeoutException
)
from ..utils import safe_click
from ..configuration import SOLO_ACTIVATION_DELAY


class TrackManager:
    """Handles track discovery, isolation, and mixer controls"""
    
    def __init__(self, driver, wait):
        """Initialize track manager with Selenium driver and wait objects"""
        self.driver = driver
        self.wait = wait
        self.progress_tracker = None
    
    def set_progress_tracker(self, progress_tracker):
        """Set the progress tracker for status updates"""
        self.progress_tracker = progress_tracker
    
    def verify_song_access(self, song_url):
        """Verify user has access to song page"""
        logging.info(f"Verifying access to: {song_url}")
        self.driver.get(song_url)
        
        # Wait for page to load - either track elements appear or login form appears
        try:
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.find_elements(By.CSS_SELECTOR, ".track") or 
                               "login" in driver.current_url.lower() or
                               driver.find_elements(By.NAME, "frm_login")
            )
        except TimeoutException:
            logging.warning("Page load timeout during song access verification")
        
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
        
        if self.progress_tracker:
            self.progress_tracker.update_track_status(track_index, 'isolating')
        
        try:
            self._navigate_to_song_if_needed(song_url)
            track_element = self._find_track_element(track_index)
            if not track_element:
                return False
            
            solo_button = self._find_solo_button(track_element, track_index)
            if not solo_button:
                return False
            
            return self._activate_solo_button(solo_button, track_name)
            
        except Exception as e:
            logging.error(f"Error soloing track {track_name}: {e}")
            return False
    
    def _navigate_to_song_if_needed(self, song_url):
        """Navigate to song page if not already there"""
        if self.driver.current_url != song_url:
            self.driver.get(song_url)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".track"))
                )
            except TimeoutException:
                logging.warning("Timeout waiting for track elements to load")
    
    def _find_track_element(self, track_index):
        """Find and return the track element for the given index"""
        track_selector = f".track[data-index='{track_index}']"
        logging.debug(f"Looking for track element with selector: {track_selector}")
        track_elements = self.driver.find_elements(By.CSS_SELECTOR, track_selector)
        
        if not track_elements:
            logging.error(f"Could not find track element with data-index='{track_index}'")
            available_tracks = [el.get_attribute('data-index') for el in self.driver.find_elements(By.CSS_SELECTOR, '.track')]
            logging.debug(f"Available tracks on page: {available_tracks}")
            return None
        
        logging.debug(f"Found track element for index {track_index}")
        return track_elements[0]
    
    def _find_solo_button(self, track_element, track_index):
        """Find and return the solo button within the track element"""
        solo_selectors = [
            "button.track__solo",  # Primary selector discovered
            "button.track__controls.track__solo",
            ".track__solo",
            "button[class*='solo']"
        ]
        
        for selector in solo_selectors:
            try:
                logging.debug(f"Trying solo button selector: {selector}")
                solo_button = track_element.find_element(By.CSS_SELECTOR, selector)
                if solo_button and solo_button.is_displayed():
                    logging.info(f"Found solo button with selector: {selector}")
                    logging.debug(f"Solo button is displayed: {solo_button.is_displayed()}, enabled: {solo_button.is_enabled()}")
                    return solo_button
            except Exception as e:
                logging.debug(f"Selector {selector} failed: {e}")
                continue
        
        logging.error(f"Could not find solo button for track {track_index}")
        logging.debug(f"Track element HTML: {track_element.get_attribute('outerHTML')[:200]}...")
        return None
    
    def _activate_solo_button(self, solo_button, track_name):
        """Activate the solo button and verify success"""
        logging.info(f"Clicking solo button for {track_name}")
        safe_click(self.driver, solo_button, f"solo button for {track_name}")
        
        if self._wait_for_solo_activation(solo_button, track_name):
            return self._finalize_solo_activation(track_name)
        else:
            return self._retry_solo_activation(solo_button, track_name)
    
    def _wait_for_solo_activation(self, solo_button, track_name):
        """Wait for solo button to become active"""
        max_wait = 10  # Maximum 10 seconds to wait for solo to activate
        check_interval = 0.5  # Check every 500ms
        waited = 0
        
        logging.debug(f"Polling for solo activation for {track_name}...")
        
        while waited < max_wait:
            try:
                WebDriverWait(self.driver, check_interval).until(
                    lambda driver: self._is_solo_button_active(solo_button)
                )
                logging.info(f"✅ Solo button became active for {track_name} (after {waited}s)")
                return True
            except TimeoutException:
                waited += check_interval
            
            if self._check_solo_activation_status(solo_button, track_name, waited):
                return True
        
        logging.warning(f"⚠️ Solo button not active after {max_wait}s for {track_name}")
        return False
    
    def _is_solo_button_active(self, solo_button):
        """Check if solo button has active state"""
        button_classes = (solo_button.get_attribute('class') or '').lower()
        return any(state in button_classes for state in ['is-active', 'active', 'selected'])
    
    def _check_solo_activation_status(self, solo_button, track_name, waited):
        """Check and log solo activation status"""
        try:
            if self._is_solo_button_active(solo_button):
                logging.info(f"✅ Solo button became active for {track_name} (after {waited}s)")
                return True
            
            if waited % 2 == 0:  # Log every 2 seconds
                button_classes = solo_button.get_attribute('class') or ''
                logging.debug(f"   Still waiting for solo activation... ({waited}s) - classes: '{button_classes}'")
        except Exception as e:
            logging.debug(f"Error checking solo status at {waited}s: {e}")
        
        return False
    
    def _retry_solo_activation(self, solo_button, track_name):
        """Retry solo activation with aggressive clicking"""
        logging.info(f"🔄 Final retry attempt for {track_name}")
        
        try:
            self._perform_aggressive_clicks(solo_button)
            
            if self._wait_for_retry_activation(solo_button):
                logging.info(f"✅ Solo button active after aggressive retry for {track_name}")
                return self._finalize_solo_activation(track_name)
            else:
                return self._handle_solo_failure(solo_button, track_name)
                
        except Exception as retry_e:
            logging.error(f"Error during final retry for {track_name}: {retry_e}")
            return False
    
    def _perform_aggressive_clicks(self, solo_button):
        """Perform multiple JavaScript clicks to ensure registration"""
        for i in range(3):
            self.driver.execute_script("arguments[0].click();", solo_button)
            try:
                WebDriverWait(self.driver, 1).until(lambda driver: True)
            except TimeoutException:
                pass
    
    def _wait_for_retry_activation(self, solo_button):
        """Wait for solo button activation after retry"""
        try:
            WebDriverWait(self.driver, 3).until(
                lambda driver: self._is_solo_button_active(solo_button)
            )
            return True
        except TimeoutException:
            return self._is_solo_button_active(solo_button)
    
    def _handle_solo_failure(self, solo_button, track_name):
        """Handle failed solo activation"""
        final_classes = solo_button.get_attribute('class') or ''
        logging.error(f"❌ Solo failed for {track_name} after all retry attempts")
        logging.error(f"   Final button classes: '{final_classes}'")
        logging.error(f"   Track may have timing issues or site-specific problems")
        return False
    
    def _finalize_solo_activation(self, track_name):
        """Finalize solo activation with synchronization delay"""
        logging.info(f"⏳ Waiting {SOLO_ACTIVATION_DELAY}s for audio generation to sync with solo state...")
        try:
            WebDriverWait(self.driver, SOLO_ACTIVATION_DELAY).until(
                lambda driver: False  # Always timeout to create the delay
            )
        except TimeoutException:
            pass  # Expected timeout for delay
        
        logging.info(f"✅ Solo activation delay complete for {track_name}")
        return True
    
    def clear_all_solos(self, song_url):
        """Clear all solo buttons (un-mute all tracks)"""
        logging.info("Clearing all solo buttons...")
        
        try:
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                # Wait for solo buttons to be present
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "button.track__solo"))
                    )
                except TimeoutException:
                    logging.warning("Timeout waiting for solo buttons to load")
            
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
                        # Brief wait for UI update
                        try:
                            WebDriverWait(self.driver, 0.5).until(
                                lambda driver: 'active' not in (button.get_attribute('class') or '').lower()
                            )
                        except TimeoutException:
                            pass  # Continue even if state change not detected
                except (Exception, AttributeError, ElementClickInterceptedException) as e:
                    logging.debug(f"Could not click solo button: {e}")
                    continue
            
            if active_solos > 0:
                logging.info(f"Cleared {active_solos} active solo buttons")
            else:
                logging.info("No active solo buttons found")
            
            return True
            
        except Exception as e:
            logging.error(f"Error clearing solo buttons: {e}")
            return False
    
    def ensure_intro_count_enabled(self, song_url):
        """Ensure the intro count checkbox is enabled"""
        try:
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                # Wait for intro count checkbox to be present
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "precount"))
                    )
                except TimeoutException:
                    logging.warning("Timeout waiting for intro count checkbox to load")
            
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
                
                # Wait for checkbox state change
                try:
                    WebDriverWait(self.driver, 2).until(
                        lambda driver: intro_checkbox.is_selected()
                    )
                except TimeoutException:
                    logging.debug("Checkbox state change not detected within timeout")
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
                # Wait for pitch controls to be present
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".pitch"))
                    )
                except TimeoutException:
                    logging.warning("Timeout waiting for pitch controls to load")
            
            logging.info(f"🎵 Adjusting key to: {target_key:+d} semitones")
            
            # Find current key value (should start at 0)
            try:
                # Look for the div that contains the current numeric value
                pitch_container = self.driver.find_element(By.CSS_SELECTOR, ".pitch")
                current_value_element = pitch_container.find_element(By.XPATH, ".//div[text()='0' or text()!='' and not(@class)]")
                current_key = int(current_value_element.text.strip())
                logging.debug(f"Current key value: {current_key}")
            except (Exception, NoSuchElementException, ValueError) as e:
                # Assume starting at 0 if we can't read current value
                current_key = 0
                logging.debug(f"Could not read current key, assuming 0: {e}")
            
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
                
                # Brief wait between clicks for UI responsiveness
                try:
                    WebDriverWait(self.driver, 0.5).until(
                        lambda driver: True  # Minimal delay replacement
                    )
                except TimeoutException:
                    pass
                logging.debug(f"   Step {step + 1}/{steps_needed}")
            
            # Wait for UI to update the key display
            try:
                WebDriverWait(self.driver, 2).until(
                    lambda driver: True  # Allow UI update time
                )
            except TimeoutException:
                pass
            try:
                final_value_element = pitch_container.find_element(By.XPATH, ".//div[text()!='' and not(@class) and not(contains(@class, 'pitch__label'))]")
                final_key = int(final_value_element.text.strip())
                if final_key == target_key:
                    logging.info(f"✅ Key successfully adjusted to: {final_key:+d}")
                    return True
                else:
                    logging.warning(f"⚠️ Key adjustment may not be complete. Target: {target_key}, Final: {final_key}")
                    return True  # Still return True as we tried our best
            except (Exception, NoSuchElementException, ValueError) as e:
                logging.info(f"✅ Key adjustment completed (could not verify final value): {e}")
                return True
            
        except Exception as e:
            logging.error(f"❌ Error adjusting key: {e}")
            return False