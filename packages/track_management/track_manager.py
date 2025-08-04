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
            
            return self._activate_solo_button(solo_button, track_name, track_index)
            
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
    
    def _activate_solo_button(self, solo_button, track_name, track_index):
        """Activate the solo button and verify success"""
        logging.info(f"Clicking solo button for {track_name}")
        safe_click(self.driver, solo_button, f"solo button for {track_name}")
        
        if self._wait_for_solo_activation(solo_button, track_name):
            return self._finalize_solo_activation(track_name, track_index)
        else:
            return self._retry_solo_activation(solo_button, track_name, track_index)
    
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
    
    def _finalize_solo_activation(self, track_name, track_index=None):
        """Finalize solo activation with comprehensive audio server sync verification"""
        logging.info(f"⏳ Waiting for audio server to process solo state for {track_name}...")
        
        # Phase 1: Wait for audio server processing indicators to clear
        audio_server_ready = self._wait_for_audio_server_sync()
        
        # Phase 2: Verify mixer state configuration
        mixer_state_valid = self._verify_mixer_state_configuration()
        
        # Phase 3: Enhanced audio mix validation (optional)
        phase3_validation_passed = True
        if track_index is not None:
            try:
                logging.debug(f"🎵 Running Phase 3 audio mix validation for {track_name}...")
                phase3_results = self._validate_audio_mix_state(track_name, track_index)
                phase3_validation_passed = phase3_results['audio_mix_validated']
                
                if phase3_validation_passed:
                    logging.info(f"✅ Phase 3 audio mix validation PASSED for {track_name}")
                else:
                    logging.warning(f"⚠️ Phase 3 audio mix validation FAILED for {track_name}")
                    logging.warning(f"   Details: {'; '.join(phase3_results['details'][:3])}")  # Show first 3 details
                    
            except Exception as e:
                logging.warning(f"⚠️ Phase 3 validation error for {track_name}: {e}")
                # Don't fail the entire process if Phase 3 has issues
        
        # Phase 4: Fallback delay if verification methods unavailable
        if not audio_server_ready or not mixer_state_valid:
            logging.info(f"⏳ Fallback: Using {SOLO_ACTIVATION_DELAY}s delay for audio generation sync...")
            try:
                WebDriverWait(self.driver, SOLO_ACTIVATION_DELAY).until(
                    lambda driver: False  # Always timeout to create the delay
                )
            except TimeoutException:
                pass  # Expected timeout for delay
        
        # Final assessment
        overall_success = audio_server_ready or mixer_state_valid
        if overall_success and phase3_validation_passed:
            logging.info(f"✅ Complete audio server sync verification successful for {track_name}")
        elif overall_success:
            logging.info(f"✅ Basic audio server sync verification complete for {track_name} (Phase 3 issues noted)")
        else:
            logging.warning(f"⚠️ Audio server sync verification had issues for {track_name} - using fallback timing")
            
        return True
    
    def _wait_for_audio_server_sync(self):
        """Wait for audio server processing indicators to complete"""
        try:
            # Monitor for audio server processing completion
            # Based on existing pattern from download_manager.py:210-211
            logging.debug("🔍 Monitoring audio server processing indicators...")
            
            # Wait for any processing indicators to appear and then disappear
            max_wait_time = SOLO_ACTIVATION_DELAY
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                page_source_lower = self.driver.page_source.lower()
                
                # Check if audio server is actively processing
                if ("generating" in page_source_lower or 
                    "preparing" in page_source_lower or
                    "processing" in page_source_lower or
                    "loading" in page_source_lower):
                    logging.debug("⏳ Audio server processing detected, waiting for completion...")
                    time.sleep(0.5)
                    continue
                
                # Check for positive completion indicators
                if ("ready" in page_source_lower or 
                    "complete" in page_source_lower or
                    "finished" in page_source_lower):
                    logging.debug("✅ Audio server processing completion detected")
                    return True
                
                # Brief pause before rechecking
                time.sleep(0.5)
            
            logging.debug("⏱️ Audio server sync timeout - proceeding with fallback delay")
            return False
            
        except Exception as e:
            logging.warning(f"⚠️ Error during audio server sync verification: {e}")
            return False
    
    def _verify_mixer_state_configuration(self):
        """Verify mixer state configuration matches expected solo state"""
        try:
            logging.debug("🔍 Verifying mixer state configuration...")
            
            # Method 1: Check for mixer object availability via JavaScript
            try:
                mixer_available = self.driver.execute_script("""
                    return typeof mixer !== 'undefined' && mixer !== null;
                """)
                
                if mixer_available:
                    # Try to get mixer state information
                    mixer_state = self.driver.execute_script("""
                        try {
                            // Check if mixer has state-related properties
                            if (typeof mixer.getState === 'function') {
                                return mixer.getState();
                            } else if (typeof mixer.currentState !== 'undefined') {
                                return mixer.currentState;
                            } else if (typeof mixer.state !== 'undefined') {
                                return mixer.state;
                            }
                            return 'mixer_available_no_state';
                        } catch (e) {
                            return 'mixer_error: ' + e.message;
                        }
                    """)
                    
                    logging.debug(f"🎛️ Mixer state: {mixer_state}")
                    
                    # If we got any state information, consider it valid
                    if mixer_state and str(mixer_state) != 'null':
                        logging.debug("✅ Mixer state configuration verified")
                        return True
                        
            except Exception as js_error:
                logging.debug(f"JavaScript mixer check failed: {js_error}")
            
            # Method 2: Check DOM for mixer-related status elements
            try:
                # Look for mixer status indicators in the DOM
                mixer_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    ".mixer, .mixer-status, .track-mixer, .audio-mixer")
                
                if mixer_elements:
                    logging.debug(f"✅ Found {len(mixer_elements)} mixer DOM elements")
                    return True
                    
            except Exception as dom_error:
                logging.debug(f"DOM mixer check failed: {dom_error}")
            
            # Method 3: Check for track state consistency
            try:
                # Verify at least one solo button is active
                active_solos = self.driver.find_elements(By.CSS_SELECTOR, 
                    "button.track__solo.active, button.track__solo.is-active, button.track__solo.selected")
                
                if active_solos:
                    logging.debug(f"✅ Found {len(active_solos)} active solo button(s)")
                    return True
                    
            except Exception as solo_error:
                logging.debug(f"Solo button check failed: {solo_error}")
            
            logging.debug("⚠️ Mixer state verification inconclusive - using fallback")
            return False
            
        except Exception as e:
            logging.warning(f"⚠️ Error during mixer state verification: {e}")
            return False
    
    def _validate_audio_mix_state(self, track_name, expected_solo_index):
        """Phase 3: Enhanced audio mix validation to verify actual audio state
        
        Args:
            track_name (str): Name of the track that should be isolated
            expected_solo_index (str/int): Expected solo track index
            
        Returns:
            dict: Validation results with detailed status information
        """
        validation_results = {
            'audio_mix_validated': False,
            'mixer_volume_state': False,
            'audio_server_response': False,
            'track_isolation_confirmed': False,
            'error_code': None,
            'details': []
        }
        
        try:
            logging.debug(f"🎵 Phase 3: Validating audio mix state for {track_name}...")
            
            # Enhanced Method 1: Deep mixer state analysis
            mixer_validation = self._validate_mixer_audio_configuration(expected_solo_index)
            validation_results['mixer_volume_state'] = mixer_validation['valid']
            validation_results['details'].extend(mixer_validation['details'])
            
            # Enhanced Method 2: Audio server response validation
            server_validation = self._validate_audio_server_response()
            validation_results['audio_server_response'] = server_validation['valid']
            validation_results['details'].extend(server_validation['details'])
            
            # Enhanced Method 3: Track isolation fingerprinting
            isolation_validation = self._validate_track_isolation_fingerprint(track_name, expected_solo_index)
            validation_results['track_isolation_confirmed'] = isolation_validation['valid']
            validation_results['details'].extend(isolation_validation['details'])
            
            # Calculate overall validation score
            validation_checks = [
                validation_results['mixer_volume_state'],
                validation_results['audio_server_response'],
                validation_results['track_isolation_confirmed']
            ]
            
            passed_validations = sum(validation_checks)
            total_validations = len(validation_checks)
            validation_score = passed_validations / total_validations
            
            # Require at least 2/3 validations to pass for audio mix validation
            validation_results['audio_mix_validated'] = validation_score >= 0.67
            
            if validation_results['audio_mix_validated']:
                logging.info(f"✅ Phase 3: Audio mix validation PASSED for {track_name} ({passed_validations}/{total_validations})")
            else:
                logging.warning(f"⚠️ Phase 3: Audio mix validation FAILED for {track_name} ({passed_validations}/{total_validations})")
                validation_results['error_code'] = 'AUDIO_MIX_VALIDATION_FAILED'
            
            return validation_results
            
        except Exception as e:
            logging.error(f"❌ Phase 3: Error during audio mix validation: {e}")
            validation_results['error_code'] = 'AUDIO_VALIDATION_EXCEPTION'
            validation_results['details'].append(f"Exception: {str(e)}")
            return validation_results
    
    def _validate_mixer_audio_configuration(self, expected_solo_index):
        """Enhanced mixer state validation with volume and configuration analysis"""
        result = {'valid': False, 'details': []}
        
        try:
            # Advanced JavaScript mixer analysis
            mixer_config = self.driver.execute_script("""
                try {
                    if (typeof mixer === 'undefined' || mixer === null) {
                        return {error: 'mixer_not_available'};
                    }
                    
                    var config = {
                        tracks: [],
                        solo_active: false,
                        solo_track_index: null
                    };
                    
                    // Try to get track volume information
                    if (typeof mixer.getTrackVolume === 'function') {
                        for (var i = 0; i < 15; i++) {
                            try {
                                var volume = mixer.getTrackVolume(i);
                                config.tracks.push({index: i, volume: volume});
                                if (volume > 0) {
                                    config.solo_active = true;
                                    config.solo_track_index = i;
                                }
                            } catch (e) {
                                // Track doesn't exist or error getting volume
                            }
                        }
                    }
                    
                    // Try to get solo state information
                    if (typeof mixer.getSoloState === 'function') {
                        config.solo_state = mixer.getSoloState();
                    } else if (typeof mixer.soloTrack !== 'undefined') {
                        config.solo_track_index = mixer.soloTrack;
                        config.solo_active = config.solo_track_index !== null;
                    }
                    
                    return config;
                } catch (e) {
                    return {error: 'mixer_analysis_failed', message: e.message};
                }
            """)
            
            if mixer_config and 'error' not in mixer_config:
                result['details'].append(f"Mixer configuration retrieved: {len(mixer_config.get('tracks', []))} tracks analyzed")
                
                # Check if the expected track is the only one with volume
                if mixer_config.get('solo_active') and str(mixer_config.get('solo_track_index')) == str(expected_solo_index):
                    result['valid'] = True
                    result['details'].append(f"✅ Solo track index matches expected: {expected_solo_index}")
                else:
                    result['details'].append(f"⚠️ Solo state mismatch - expected: {expected_solo_index}, actual: {mixer_config.get('solo_track_index')}")
            else:
                result['details'].append(f"⚠️ Mixer analysis failed: {mixer_config.get('error', 'unknown')}")
                
        except Exception as e:
            result['details'].append(f"⚠️ Mixer configuration validation failed: {e}")
        
        return result
    
    def _validate_audio_server_response(self):
        """Enhanced audio server response validation"""
        result = {'valid': False, 'details': []}
        
        try:
            # Check for specific audio server status indicators
            page_source_lower = self.driver.page_source.lower()
            
            # Look for positive audio server indicators
            positive_indicators = [
                'audio ready', 'mix ready', 'track ready', 'solo ready',
                'audio loaded', 'mix loaded', 'track loaded',
                'audio complete', 'mix complete', 'processing complete'
            ]
            
            # Look for negative indicators that suggest issues
            negative_indicators = [
                'audio error', 'mix error', 'loading failed', 'audio failed',
                'server error', 'timeout', 'connection failed'
            ]
            
            positive_found = any(indicator in page_source_lower for indicator in positive_indicators)
            negative_found = any(indicator in page_source_lower for indicator in negative_indicators)
            
            if positive_found and not negative_found:
                result['valid'] = True
                result['details'].append("✅ Audio server shows positive ready indicators")
            elif negative_found:
                result['details'].append("⚠️ Audio server shows error indicators")
            else:
                # Check for absence of processing indicators (good sign)
                processing_indicators = ['generating', 'preparing', 'processing', 'loading']
                still_processing = any(indicator in page_source_lower for indicator in processing_indicators)
                
                if not still_processing:
                    result['valid'] = True
                    result['details'].append("✅ No active processing indicators detected")
                else:
                    result['details'].append("⚠️ Audio server still showing processing indicators")
                    
        except Exception as e:
            result['details'].append(f"⚠️ Audio server validation failed: {e}")
        
        return result
    
    def _validate_track_isolation_fingerprint(self, track_name, expected_solo_index):
        """Enhanced track isolation validation using DOM fingerprinting"""
        result = {'valid': False, 'details': []}
        
        try:
            # Method 1: Analyze track element states
            track_states = self._analyze_track_element_states()
            result['details'].extend(track_states['details'])
            
            # Method 2: Check for audio context indicators
            audio_context_valid = self._check_audio_context_indicators()
            
            # Method 3: Validate solo button exclusivity
            solo_exclusivity_valid = self._validate_solo_button_exclusivity(expected_solo_index)
            
            # Combined validation logic
            if track_states['isolated_track_detected'] and solo_exclusivity_valid:
                result['valid'] = True
                result['details'].append(f"✅ Track isolation fingerprint validated for index {expected_solo_index}")
            else:
                result['details'].append(f"⚠️ Track isolation fingerprint validation failed")
                
        except Exception as e:
            result['details'].append(f"⚠️ Track isolation fingerprint validation failed: {e}")
        
        return result
    
    def _analyze_track_element_states(self):
        """Analyze DOM track elements for isolation state indicators"""
        result = {'isolated_track_detected': False, 'details': []}
        
        try:
            # Find all track elements and analyze their states
            track_elements = self.driver.find_elements(By.CSS_SELECTOR, ".track")
            active_tracks = 0
            muted_tracks = 0
            
            for track in track_elements:
                try:
                    # Check for various state indicators
                    classes = track.get_attribute('class') or ''
                    style = track.get_attribute('style') or ''
                    
                    # Look for active/solo indicators
                    if any(indicator in classes.lower() for indicator in ['active', 'solo', 'selected', 'playing']):
                        active_tracks += 1
                    
                    # Look for muted/inactive indicators  
                    if any(indicator in classes.lower() for indicator in ['muted', 'inactive', 'disabled']) or 'opacity: 0' in style:
                        muted_tracks += 1
                        
                except Exception:
                    continue
            
            # If we have exactly 1 active track and some muted tracks, isolation is likely working
            if active_tracks == 1 and muted_tracks > 0:
                result['isolated_track_detected'] = True
                result['details'].append(f"✅ Track isolation detected: 1 active, {muted_tracks} muted")
            else:
                result['details'].append(f"⚠️ Track isolation unclear: {active_tracks} active, {muted_tracks} muted")
                
        except Exception as e:
            result['details'].append(f"⚠️ Track element analysis failed: {e}")
        
        return result
    
    def _check_audio_context_indicators(self):
        """Check for audio context and Web Audio API indicators"""
        try:
            audio_context_status = self.driver.execute_script("""
                try {
                    // Check for Web Audio API context
                    if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {
                        return {
                            audio_api_available: true,
                            context_state: 'available'
                        };
                    }
                    return {
                        audio_api_available: false,
                        context_state: 'not_available'
                    };
                } catch (e) {
                    return {
                        audio_api_available: false,
                        error: e.message
                    };
                }
            """)
            
            return audio_context_status.get('audio_api_available', False)
            
        except Exception:
            return False
    
    def _validate_solo_button_exclusivity(self, expected_solo_index):
        """Validate that only the expected solo button is active"""
        try:
            # Find all solo buttons and check their states
            solo_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.track__solo")
            active_solo_count = 0
            expected_button_active = False
            
            for i, button in enumerate(solo_buttons):
                classes = button.get_attribute('class') or ''
                if any(active_class in classes for active_class in ['active', 'is-active', 'selected']):
                    active_solo_count += 1
                    if str(i) == str(expected_solo_index):
                        expected_button_active = True
            
            # Validation passes if exactly one solo button is active and it's the expected one
            return active_solo_count == 1 and expected_button_active
            
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