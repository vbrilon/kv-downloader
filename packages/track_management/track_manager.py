"""Track management for karaoke automation - discovery, isolation, and mixer controls"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    InvalidSessionIdException,
    NoSuchWindowException,
    TimeoutException,
)
from ..utils import js_click_with_scroll, profile_timing, profile_selenium, is_solo_button_active
from ..configuration import SOLO_ACTIVATION_DELAY
from ..configuration.selectors import (
    TRACK_ELEMENT_SELECTOR,
    SOLO_BUTTON_SELECTORS,
    TRACK_CAPTION_SELECTOR,
)
from ..configuration.config import (WEBDRIVER_DEFAULT_TIMEOUT, WEBDRIVER_SHORT_TIMEOUT,
                                    WEBDRIVER_BRIEF_TIMEOUT, WEBDRIVER_MICRO_TIMEOUT,
                                    TRACK_INTERACTION_DELAY, SOLO_BUTTON_MAX_RETRIES,
                                    SOLO_ACTIVATION_MAX_WAIT, SOLO_CHECK_INTERVAL,
                                    SOLO_ACTIVATION_DELAY_SIMPLE, SOLO_ACTIVATION_DELAY_COMPLEX)


def _build_indexed_track_selector(track_element_selector, track_index):
    """Apply [data-index='N'] to every part of a comma-list selector.

    TRACK_ELEMENT_SELECTOR is a comma-list (legacy + modern A/B variants); the
    naive `f"{SEL}[data-index='X']"` only filters the LAST selector in the
    list, leaving the others unfiltered. Splitting on comma and re-joining
    applies the index filter to each variant.
    """
    parts = [s.strip() for s in track_element_selector.split(",")]
    return ", ".join(f"{p}[data-index='{track_index}']" for p in parts)


class TrackManager:
    """Handles track discovery, isolation, and mixer controls"""
    
    def __init__(self, driver, wait):
        """Initialize track manager with Selenium driver and wait objects"""
        self.driver = driver
        self.wait = wait
        self.progress_tracker = None
        self.track_complexity = "simple"  # Default to simple complexity
    
    def set_progress_tracker(self, progress_tracker):
        """Set the progress tracker for status updates"""
        self.progress_tracker = progress_tracker
    
    def verify_song_access(self, song_url):
        """Verify user has access to song page"""
        logging.info(f"Verifying access to: {song_url}")
        self.driver.get(song_url)
        
        # Wait for page to load - either track elements appear or login form appears
        try:
            WebDriverWait(self.driver, WEBDRIVER_DEFAULT_TIMEOUT).until(
                lambda driver: driver.find_elements(By.CSS_SELECTOR, TRACK_ELEMENT_SELECTOR) or 
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
        track_elements = self.driver.find_elements(By.CSS_SELECTOR, TRACK_ELEMENT_SELECTOR)
        if not track_elements:
            logging.warning("No track elements found - may not have access")
            return False
        
        logging.info(f"✅ Access verified - found {len(track_elements)} tracks")
        return True
    
    @profile_timing("discover_tracks", "track_management", "method")
    def discover_tracks(self, song_url):
        """Discover all available tracks for a song"""
        if not self.verify_song_access(song_url):
            return []
        
        logging.info("Discovering available tracks...")
        logging.debug(f"Searching for track elements with CSS selector: .track")
        
        track_elements = self.driver.find_elements(By.CSS_SELECTOR, TRACK_ELEMENT_SELECTOR)
        logging.debug(f"Found {len(track_elements)} track elements on page")
        
        tracks = []
        for i, track_element in enumerate(track_elements):
            try:
                caption_element = track_element.find_element(By.CSS_SELECTOR, TRACK_CAPTION_SELECTOR)
                # Some captions (e.g. "Intro count\n      Click") have embedded
                # newlines + leading whitespace between sibling elements; collapse
                # any run of whitespace to a single space so progress display and
                # filenames render cleanly on one line.
                track_name = ' '.join(caption_element.text.split())
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
        
        # Detect track complexity for adaptive timeouts
        self.track_complexity = self._detect_track_complexity(len(tracks))
        logging.info(f"Discovered {len(tracks)} tracks - {self.track_complexity} complexity")
        logging.debug(f"Track discovery complete for: {song_url}")
        return tracks
    
    def _detect_track_complexity(self, track_count):
        """Detect track complexity based on track count"""
        if track_count <= 8:
            return "simple"
        else:
            return "complex"
    
    def _detect_track_type(self, track_name):
        """Detect track type based on track name for adaptive timeout strategies
        
        Args:
            track_name (str): Name of the track to classify
            
        Returns:
            str: Track type classification ('click', 'bass', 'drums', 'standard')
        """
        if not track_name:
            return "standard"
            
        track_name_lower = track_name.lower()
        
        # Click track detection (most problematic type)
        if any(keyword in track_name_lower for keyword in ['click', 'metronome', 'count']):
            return "click"
        
        # Bass track detection
        if any(keyword in track_name_lower for keyword in ['bass', 'low', 'sub']):
            return "bass"
            
        # Drum track detection  
        if any(keyword in track_name_lower for keyword in ['drum', 'kick', 'snare', 'hihat', 'cymbal', 'perc']):
            return "drums"
            
        # Vocal track detection
        if any(keyword in track_name_lower for keyword in ['vocal', 'voice', 'lead', 'backing', 'harmony']):
            return "vocal"
            
        # Default to standard for unrecognized types
        return "standard"
    
    def _get_adaptive_timeout(self):
        """Get adaptive timeout based on track complexity"""
        if self.track_complexity == "simple":
            return SOLO_ACTIVATION_DELAY_SIMPLE
        else:
            return SOLO_ACTIVATION_DELAY_COMPLEX
    
    def _get_track_type_timeout(self, track_name):
        """Get timeout based on track type for enhanced reliability."""
        track_type = self._detect_track_type(track_name)

        from packages.configuration.config import SOLO_ACTIVATION_DELAY_SPECIAL

        if track_type in ("bass", "drums"):
            return SOLO_ACTIVATION_DELAY_SPECIAL
        return self._get_adaptive_timeout()
    
    @profile_timing("solo_track", "track_management", "method")
    def solo_track(self, track_info, song_url):
        """Ensure the target track is solo'd. Assumes ensure_only_track_active was just called."""
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

            # ensure_only_track_active is the single source of activation
            # clicks. We MUST NOT click here: the button is already active and
            # a redundant click toggles it OFF (verified live 2026-05-08), which
            # is what the old 12s click-track timeout was masking. If anything
            # is wrong, _retry_solo_activation's 3-click hammer (odd count =>
            # ends ON whatever the start state) is the safety net.
            return self._activate_solo_button_verify_only(solo_button, track_name, track_index)

        except (InvalidSessionIdException, NoSuchWindowException):
            # Infrastructure failure — Chrome is gone. Don't pretend this is
            # a product-side "couldn't solo this track"; let the caller see
            # it and decide whether to retry, restart Chrome, or abort.
            raise
        except Exception as e:
            logging.error(f"Error soloing track {track_name}: {e}")
            return False
    
    def _navigate_to_song_if_needed(self, song_url):
        """Navigate to song page if not already there"""
        if self.driver.current_url != song_url:
            self.driver.get(song_url)
            try:
                WebDriverWait(self.driver, WEBDRIVER_DEFAULT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, TRACK_ELEMENT_SELECTOR))
                )
            except TimeoutException:
                logging.warning("Timeout waiting for track elements to load")
    
    def _find_track_element(self, track_index):
        """Find and return the track element for the given index"""
        track_selector = _build_indexed_track_selector(TRACK_ELEMENT_SELECTOR, track_index)
        logging.debug(f"Looking for track element with selector: {track_selector}")
        try:
            track_element = WebDriverWait(self.driver, WEBDRIVER_SHORT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, track_selector))
            )
            logging.debug(f"Found track element for index {track_index}")
            return track_element
        except TimeoutException:
            logging.error(f"Could not find track element with data-index='{track_index}'")
            available_tracks = [
                el.get_attribute('data-index')
                for el in self.driver.find_elements(By.CSS_SELECTOR, TRACK_ELEMENT_SELECTOR)
            ]
            logging.debug(f"Available tracks on page: {available_tracks}")
            return None
    
    def _find_solo_button(self, track_element, track_index):
        """Find and return the solo button within the track element"""
        solo_selectors = SOLO_BUTTON_SELECTORS

        for i, selector in enumerate(solo_selectors):
            try:
                logging.debug(f"Trying solo selector {i+1}/{len(solo_selectors)}: {selector}")
                # Prefer searching within the track element first
                solo_button = track_element.find_element(By.CSS_SELECTOR, selector)
                # Ensure it's present/visible by waiting briefly if needed
                if not (solo_button and solo_button.is_displayed() and solo_button.is_enabled()):
                    solo_button = WebDriverWait(self.driver, WEBDRIVER_BRIEF_TIMEOUT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                if solo_button and solo_button.is_displayed():
                    logging.info(f"Found solo button with selector: {selector}")
                    logging.debug(
                        f"Solo button is displayed: {solo_button.is_displayed()}, enabled: {solo_button.is_enabled()}"
                    )
                    return solo_button
            except Exception as e:
                logging.debug(f"Selector {selector} failed: {e}")
                continue
        
        logging.error(f"Could not find solo button for track {track_index}")
        logging.debug(f"Track element HTML: {track_element.get_attribute('outerHTML')[:200]}...")
        return None
    
    @profile_timing("_activate_solo_button_verify_only", "track_management", "method")
    def _activate_solo_button_verify_only(self, solo_button, track_name, track_index):
        """Wait for solo activation; click was already handled by caller."""
        if self._wait_for_solo_activation(solo_button, track_name):
            return self._finalize_solo_activation(track_name, track_index)
        return self._retry_solo_activation(solo_button, track_name, track_index)
    
    def _wait_for_solo_activation(self, solo_button, track_name):
        """Wait for solo button to become active - track-type-aware timeout with enhanced detection"""
        # Use track-type-specific timeout for better reliability
        track_type_timeout = self._get_track_type_timeout(track_name)
        max_wait = max(8, track_type_timeout)  # Ensure minimum 8s for backward compatibility
        
        # Track type-specific polling intervals
        track_type = self._detect_track_type(track_name)
        if track_type == "click":
            check_interval = 0.3  # Slightly slower polling for click tracks to avoid missing brief states
        else:
            check_interval = 0.2  # Standard polling for other tracks
            
        waited = 0
        
        logging.info(f"Polling for solo activation for {track_name} (type: {track_type}, timeout: {max_wait}s)...") 
        
        # Brief initial delay to allow click to register
        time.sleep(0.1)
        
        while waited < max_wait:
            try:
                # Check immediately without waiting first
                if is_solo_button_active(solo_button):
                    logging.info(f"✅ Solo button became active for {track_name} (after {waited:.1f}s)")
                    return True
                
                # Brief wait before next check
                time.sleep(check_interval)
                waited += check_interval
                
                # Log progress every 2s
                if int(waited) > int(waited - check_interval) and waited >= 2.0 and int(waited) % 2 == 0:
                    logging.debug(f"   Solo button activation check: {waited:.1f}s elapsed")
                
            except Exception as e:
                logging.debug(f"Error checking solo button activation: {e}")
                time.sleep(check_interval)
                waited += check_interval
        
        track_type = self._detect_track_type(track_name)
        logging.warning(f"⚠️ Solo button not active after {max_wait}s for {track_name} (type: {track_type})")
        logging.warning(f"   Track-specific timeout was {track_type_timeout}s, actual timeout used: {max_wait}s")
        return False
    
    def _retry_solo_activation(self, solo_button, track_name, track_index=None):
        """Retry solo activation with aggressive clicking"""
        logging.info(f"🔄 Final retry attempt for {track_name}")
        
        try:
            self._perform_aggressive_clicks(solo_button)
            
            if self._wait_for_retry_activation(solo_button):
                logging.info(f"✅ Solo button active after aggressive retry for {track_name}")
                return self._finalize_solo_activation(track_name, track_index)
            else:
                return self._handle_solo_failure(solo_button, track_name)
                
        except Exception as retry_e:
            logging.error(f"Error during final retry for {track_name}: {retry_e}")
            return False
    
    def _perform_aggressive_clicks(self, solo_button):
        """Perform multiple JavaScript clicks to ensure registration"""
        for i in range(SOLO_BUTTON_MAX_RETRIES):
            self.driver.execute_script("arguments[0].click();", solo_button)
    
    def _wait_for_retry_activation(self, solo_button):
        """Wait for solo button activation after retry"""
        try:
            WebDriverWait(self.driver, WEBDRIVER_SHORT_TIMEOUT).until(
                lambda driver: is_solo_button_active(solo_button)
            )
            return True
        except TimeoutException:
            return is_solo_button_active(solo_button)
    
    def _handle_solo_failure(self, solo_button, track_name):
        """Handle failed solo activation"""
        final_classes = solo_button.get_attribute('class') or ''
        logging.error(f"❌ Solo failed for {track_name} after all retry attempts")
        logging.error(f"   Final button classes: '{final_classes}'")
        logging.error(f"   Track may have timing issues or site-specific problems")
        return False
    
    @profile_timing("_finalize_solo_activation", "track_management", "method")
    def _finalize_solo_activation(self, track_name, track_index=None):
        """Wait for audio server sync via DOM polling; brief safety buffer if needed."""
        logging.info(f"⏳ Waiting for audio server to process solo state for {track_name}...")

        audio_server_ready = (
            self._wait_for_audio_server_sync(track_index)
            if track_index is not None
            else False
        )

        if audio_server_ready:
            # Tier 1 perf tweak (2026-05-08): no post-detection buffer.
            # _wait_for_audio_server_sync already deterministically confirmed
            # the solo button is active in the DOM. The next operation is a
            # click on the same page, which goes through chromedriver's own
            # readiness checks. 0.2s here was pure padding × 15 tracks.
            logging.info(f"✅ Audio server sync verified for {track_name}")
        else:
            # When sync was NOT confirmed, the buffer is the only safety net.
            # Keep it: we have no positive signal, so we trade wall-time for
            # avoiding race conditions on the click that follows.
            time.sleep(1.0)
            logging.warning(f"⚠️ Audio server sync inconclusive for {track_name} — using fallback")

        return True
    
    @profile_timing("_wait_for_audio_server_sync", "track_management", "method")
    def _wait_for_audio_server_sync(self, expected_solo_index):
        """Wait for solo button to achieve active state - deterministic DOM-based detection"""
        try:
            logging.debug(f"🔍 Waiting for solo button {expected_solo_index} to become active...")
            
            # Brief initial delay to let server start processing
            time.sleep(0.3)
            
            # Active polling for solo button state - much faster than blind waiting
            max_checks = 25  # 25 * 0.2s = 5s maximum wait (vs previous 10s)
            
            for check_num in range(max_checks):
                try:
                    # Reuse the reliable solo-button predicate
                    if self._is_solo_button_active_for_index(expected_solo_index):
                        elapsed_time = (check_num * 0.2) + 0.3
                        logging.debug(f"✅ Solo button active after {elapsed_time:.1f}s - server sync complete")
                        return True
                    
                    # Short poll interval for responsiveness
                    time.sleep(0.2)
                    
                except Exception as e:
                    # Don't fail on individual check errors - keep trying
                    logging.debug(f"Solo button check {check_num} failed: {e}")
                    time.sleep(0.2)
                    continue
            
            # If we get here, we timed out - but this is much faster than before
            total_wait_time = (max_checks * 0.2) + 0.3
            logging.debug(f"⚠️ Solo button state timeout after {total_wait_time:.1f}s - proceeding anyway")
            return False
            
        except Exception as e:
            logging.warning(f"⚠️ Error during audio server sync verification: {e}")
            return False
    
    def _is_solo_button_active_for_index(self, expected_solo_index):
        """Fast check if solo button is active for specific track index"""
        try:
            track_selector = f".track[data-index='{expected_solo_index}']"
            track_elements = self.driver.find_elements(By.CSS_SELECTOR, track_selector)
            if not track_elements:
                return False
            solo_button = track_elements[0].find_element(By.CSS_SELECTOR, "button.track__solo")
            return is_solo_button_active(solo_button)
        except Exception:
            return False

    def clear_all_solos(self, song_url):
        """Clear all solo buttons (un-mute all tracks)"""
        logging.info("Clearing all solo buttons...")
        
        try:
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                # Wait for solo buttons to be present
                try:
                    WebDriverWait(self.driver, WEBDRIVER_DEFAULT_TIMEOUT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "button.track__solo"))
                    )
                except TimeoutException:
                    logging.warning("Timeout waiting for solo buttons to load")
            
            # Find all solo buttons
            solo_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.track__solo")
            
            active_solos = 0
            for button in solo_buttons:
                try:
                    # Use enhanced detection to identify active solo buttons
                    if is_solo_button_active(button):
                        logging.info("Clicking to deactivate active solo button")
                        js_click_with_scroll(self.driver, button, "active solo button")
                        active_solos += 1
                        # Brief wait for UI update with enhanced detection
                        try:
                            WebDriverWait(self.driver, WEBDRIVER_MICRO_TIMEOUT).until(
                                lambda driver: not is_solo_button_active(button)
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
    
    def ensure_only_track_active(self, target_index, song_url):
        """Intelligent solo management - only deactivate conflicting tracks, then activate target
        
        This replaces the inefficient clear_all_solos() approach that was causing 2x performance regression.
        Only deactivates tracks that are actually active, then activates the target track.
        
        Args:
            target_index (int): Index of track that should be the only active track
            song_url (str): URL to navigate to if needed
            
        Returns:
            bool: True if successful, False on error
        """
        try:
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                
            logging.debug(f"Ensuring only track {target_index} is active (smart clearing)")
            
            # Find all solo buttons
            solo_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.track__solo")
            if not solo_buttons:
                logging.warning("No solo buttons found for smart clearing")
                return False
                
            active_tracks = []
            target_button = None

            # data-index comes from the DOM as a string; coerce so it can be
            # compared against enumerate()'s int loop counter.
            target_index_int = int(target_index) if isinstance(target_index, str) else target_index

            # Scan for currently active tracks using enhanced detection
            for i, button in enumerate(solo_buttons):
                try:
                    if is_solo_button_active(button):
                        active_tracks.append(i)
                        logging.debug(f"Found active track: {i}")

                    if i == target_index_int:
                        target_button = button

                except Exception as e:
                    logging.debug(f"Error checking button {i}: {e}")
                    continue

            # Check if target is already the only active track
            if len(active_tracks) == 1 and active_tracks[0] == target_index_int:
                logging.debug(f"Track {target_index} is already the only active track - no clearing needed")
                return True

            # Deactivate only the conflicting tracks (not target)
            conflicting_tracks = [track for track in active_tracks if track != target_index_int]
            
            if conflicting_tracks:
                logging.info(f"Deactivating {len(conflicting_tracks)} conflicting tracks: {conflicting_tracks}")
                
                for track_index in conflicting_tracks:
                    try:
                        button = solo_buttons[track_index]
                        logging.debug(f"Deactivating track {track_index}")
                        js_click_with_scroll(self.driver, button, f"conflicting solo button (track {track_index})")
                        
                        # Brief wait for deactivation with enhanced detection
                        try:
                            WebDriverWait(self.driver, WEBDRIVER_MICRO_TIMEOUT).until(
                                lambda driver: not is_solo_button_active(button)
                            )
                        except TimeoutException:
                            pass  # Continue even if state change not detected immediately
                            
                    except Exception as e:
                        logging.debug(f"Error deactivating track {track_index}: {e}")
                        continue
            else:
                logging.debug("No conflicting tracks to deactivate")
            
            # Activate target track if it's not already active
            if target_index_int not in active_tracks:
                if target_button:
                    logging.debug(f"Activating target track {target_index}")
                    js_click_with_scroll(self.driver, target_button, f"target solo button (track {target_index})")
                    
                    # Brief wait for activation
                    try:
                        WebDriverWait(self.driver, WEBDRIVER_MICRO_TIMEOUT).until(
                            lambda driver: is_solo_button_active(target_button)
                        )
                    except TimeoutException:
                        pass  # Continue even if state change not detected immediately
                else:
                    logging.warning(f"Could not find target button for track {target_index}")
                    return False
            else:
                logging.debug(f"Target track {target_index} already active")
            
            logging.debug(f"Smart clearing completed for track {target_index}")
            return True
            
        except Exception as e:
            logging.error(f"Error in smart solo management: {e}")
            return False
    
    def ensure_intro_count_enabled(self, song_url):
        """Ensure the intro count checkbox is enabled"""
        try:
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                # Wait for intro count checkbox to be present
                try:
                    WebDriverWait(self.driver, WEBDRIVER_DEFAULT_TIMEOUT).until(
                        EC.presence_of_element_located((By.ID, "precount"))
                    )
                except TimeoutException:
                    logging.warning("Timeout waiting for intro count checkbox to load")
            
            logging.info("🎼 Checking intro count checkbox...")
            
            # Try multiple selector approaches for intro count checkbox
            intro_checkbox = None
            selectors_to_try = [
                (By.ID, "precount"),
                (By.CSS_SELECTOR, "#precount"),
                (By.CSS_SELECTOR, "input[type='checkbox'][id='precount']"),
                (By.XPATH, "//input[@id='precount']")
            ]
            
            for selector_type, selector_value in selectors_to_try:
                try:
                    intro_checkbox = self.driver.find_element(selector_type, selector_value)
                    logging.debug(f"✅ Found intro count checkbox using {selector_type}: {selector_value}")
                    break
                except NoSuchElementException:
                    logging.debug(f"⚠️ Intro count checkbox not found with {selector_type}: {selector_value}")
                    continue
            
            if not intro_checkbox:
                logging.warning("⚠️ Intro count checkbox not found with any selector - continuing anyway")
                return False
            
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
                    WebDriverWait(self.driver, WEBDRIVER_BRIEF_TIMEOUT).until(
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
            logging.warning("⚠️ Could not enable intro count - continuing anyway")
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
                    WebDriverWait(self.driver, WEBDRIVER_DEFAULT_TIMEOUT).until(
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
                time.sleep(0.1)
                logging.debug(f"   Step {step + 1}/{steps_needed}")
            
            # Wait for UI to update the key display
            time.sleep(0.5)
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
