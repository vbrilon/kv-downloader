"""
Core track validation logic extracted from download_manager and track_manager
"""

import time
import logging
from typing import Dict, List, Any, Union, Optional
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException

from .validation_config import ValidationConfig
from .audio_validator import AudioValidator


class TrackValidator:
    """Unified track validation system for solo button and track state verification"""
    
    def __init__(self, driver, config: ValidationConfig):
        """
        Initialize track validator
        
        Args:
            driver: Selenium WebDriver instance
            config: ValidationConfig specifying behavior
        """
        self.driver = driver
        self.config = config
        self.audio_validator = AudioValidator(driver, config)
    
    def validate_track_selection(self, track_name: str, track_index: Union[str, int]) -> Union[bool, Dict[str, Any]]:
        """
        Main validation method supporting both strict and audio_mix validation types
        
        Args:
            track_name: Name of the track that should be isolated
            track_index: Data-index of the track that should be active
            
        Returns:
            bool: If return_format is 'boolean'
            Dict: If return_format is 'detailed' with validation results and error info
        """
        return self._validate_with_retry(track_name, track_index)
    
    def _validate_with_retry(self, track_name: str, track_index: Union[str, int]) -> Union[bool, Dict[str, Any]]:
        """Execute validation with retry logic"""
        for attempt in range(self.config.max_retries):
            if self.config.log_details:
                logging.info(f"🔄 Validation attempt {attempt + 1}/{self.config.max_retries} for {track_name}")
            
            result = self._execute_validation(track_name, track_index)
            
            # Check if validation passed based on return format
            validation_passed = result if isinstance(result, bool) else result.get('validation_passed', False)
            
            if validation_passed:
                if self.config.log_details:
                    logging.info(f"✅ Validation passed on attempt {attempt + 1}")
                return result
            
            if attempt < self.config.max_retries - 1:  # Don't wait after the last attempt
                if self.config.log_details:
                    logging.warning(f"⚠️ Validation failed, waiting {self.config.retry_delay}s before retry {attempt + 2}...")
                time.sleep(self.config.retry_delay)
        
        if self.config.log_details:
            logging.error(f"❌ All {self.config.max_retries} validation attempts failed for {track_name}")
        
        # Return failed result in appropriate format
        if self.config.return_format == 'boolean':
            return False
        else:
            return {
                'validation_passed': False,
                'error_code': 'MAX_RETRIES_EXCEEDED',
                'details': [f"All {self.config.max_retries} validation attempts failed"],
                'validation_results': {}
            }
    
    def _execute_validation(self, track_name: str, track_index: Union[str, int]) -> Union[bool, Dict[str, Any]]:
        """Execute the validation checks based on configuration"""
        try:
            if self.config.log_details:
                logging.info(f"🔍 Validating track selection for {track_name} (index {track_index})")
            
            # Collect validation results
            validation_results = {}
            
            if self.config.validation_type == 'strict':
                # Download manager style validation
                validation_results = {
                    'solo_button_active': self._check_solo_button_active(track_index),
                    'track_element_found': self._check_track_element_exists(track_index),
                    'other_solos_inactive': self._check_other_solos_inactive(track_index),
                    'track_name_match': self._check_track_name_match(track_name, track_index)
                }
            elif self.config.validation_type == 'audio_mix':
                # Track manager style validation using audio validator
                mixer_result = self.audio_validator.validate_mixer_audio_configuration(track_index)
                server_result = self.audio_validator.validate_audio_server_response()
                isolation_result = self.audio_validator.validate_track_isolation_fingerprint(track_name, track_index)
                
                validation_results = {
                    'mixer_volume_state': mixer_result['valid'],
                    'audio_server_response': server_result['valid'],
                    'track_isolation_confirmed': isolation_result['valid']
                }
                
                # Collect all validation details for detailed return format
                if self.config.return_format == 'detailed':
                    validation_details = []
                    validation_details.extend(mixer_result['details'])
                    validation_details.extend(server_result['details'])
                    validation_details.extend(isolation_result['details'])
            
            # Calculate validation score
            passed_checks = sum(validation_results.values())
            total_checks = len(validation_results)
            validation_score = passed_checks / total_checks if total_checks > 0 else 0.0
            
            validation_passed = validation_score >= self.config.threshold
            
            if self.config.log_details:
                logging.info(f"🔍 Validation: {passed_checks}/{total_checks} checks passed ({validation_score:.1%})")
                if validation_passed:
                    logging.info(f"✅ Validation PASSED for {track_name}")
                else:
                    logging.warning(f"⚠️ Validation FAILED for {track_name}")
                    failed_checks = [k for k, v in validation_results.items() if not v]
                    logging.warning(f"   Failed checks: {failed_checks}")
            
            # Return result in requested format
            if self.config.return_format == 'boolean':
                return validation_passed
            else:
                result = {
                    'validation_passed': validation_passed,
                    'validation_score': validation_score,
                    'passed_checks': passed_checks,
                    'total_checks': total_checks,
                    'validation_results': validation_results,
                    'error_code': None if validation_passed else 'VALIDATION_FAILED',
                    'details': [] if validation_passed else [f"Failed checks: {[k for k, v in validation_results.items() if not v]}"]
                }
                
                # Add audio validation details if available
                if self.config.validation_type == 'audio_mix' and 'validation_details' in locals():
                    result['details'].extend(validation_details)
                
                return result
                
        except Exception as e:
            error_msg = f"Error during validation: {e}"
            if self.config.log_details:
                logging.error(f"❌ {error_msg}")
            
            if self.config.return_format == 'boolean':
                return False
            else:
                return {
                    'validation_passed': False,
                    'error_code': 'VALIDATION_EXCEPTION',
                    'details': [error_msg],
                    'validation_results': {}
                }
    
    def _check_solo_button_active(self, track_index: Union[str, int]) -> bool:
        """Check if the specific track's solo button is active"""
        try:
            track_selector = f".track[data-index='{track_index}']"
            track_elements = self.driver.find_elements(By.CSS_SELECTOR, track_selector)
            
            if track_elements:
                track_element = track_elements[0]
                solo_button = track_element.find_element(By.CSS_SELECTOR, "button.track__solo")
                button_classes = solo_button.get_attribute('class') or ''
                
                is_active = any(active_class in button_classes.lower() for active_class in ['is-active', 'active', 'selected'])
                
                if self.config.log_details and is_active:
                    logging.debug(f"✅ Solo button is active for track {track_index}")
                elif self.config.log_details:
                    logging.warning(f"⚠️ Solo button not active for track {track_index} - classes: {button_classes}")
                
                return is_active
                
        except Exception as e:
            if self.config.log_details:
                logging.warning(f"Error checking solo button state: {e}")
        
        return False
    
    def _check_track_element_exists(self, track_index: Union[str, int]) -> bool:
        """Check if track element exists"""
        try:
            track_selector = f".track[data-index='{track_index}']"
            track_elements = self.driver.find_elements(By.CSS_SELECTOR, track_selector)
            exists = len(track_elements) > 0
            
            if self.config.log_details and not exists:
                logging.warning(f"⚠️ Could not find track element with data-index '{track_index}'")
            
            return exists
            
        except Exception as e:
            if self.config.log_details:
                logging.warning(f"Error finding track element: {e}")
            return False
    
    def _check_other_solos_inactive(self, expected_active_index: Union[str, int]) -> bool:
        """Check that no other solo buttons are active (mutual exclusivity)"""
        try:
            all_solo_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.track__solo")
            active_count = 0
            other_active_tracks = []
            
            for button in all_solo_buttons:
                try:
                    # Get parent track element to find data-index
                    parent_track = button.find_element(By.XPATH, "./ancestor::*[contains(@class, 'track')]")
                    button_track_index = parent_track.get_attribute('data-index')
                    button_classes = button.get_attribute('class') or ''
                    
                    if any(active_class in button_classes.lower() for active_class in ['is-active', 'active', 'selected']):
                        active_count += 1
                        if button_track_index != str(expected_active_index):
                            other_active_tracks.append(button_track_index)
                            
                except Exception as e:
                    if self.config.log_details:
                        logging.debug(f"Error checking solo button state: {e}")
            
            if active_count == 1 and not other_active_tracks:
                if self.config.log_details:
                    logging.debug(f"✅ Exactly one solo button active (track {expected_active_index})")
                return True
            elif active_count == 0:
                if self.config.log_details:
                    logging.warning(f"⚠️ No solo buttons are active (expected track {expected_active_index})")
            elif other_active_tracks:
                if self.config.log_details:
                    logging.warning(f"⚠️ Other tracks also have active solos: {other_active_tracks}")
            
            return False
            
        except Exception as e:
            if self.config.log_details:
                logging.warning(f"Error checking other solo buttons: {e}")
            return False
    
    def _check_track_name_match(self, expected_name: str, track_index: Union[str, int]) -> bool:
        """Check if track name matches expected name"""
        try:
            track_selector = f".track[data-index='{track_index}']"
            track_elements = self.driver.find_elements(By.CSS_SELECTOR, track_selector)
            
            if track_elements:
                track_element = track_elements[0]
                caption_element = track_element.find_element(By.CSS_SELECTOR, ".track__caption")
                actual_track_name = caption_element.text.strip()
                
                # Normalize names for comparison
                normalized_expected = expected_name.lower().replace('_', ' ').replace('-', ' ')
                normalized_actual = actual_track_name.lower().replace('_', ' ').replace('-', ' ')
                
                # Check if names match (allowing for partial matches)
                name_matches = normalized_expected in normalized_actual or normalized_actual in normalized_expected
                
                if self.config.log_details:
                    if name_matches:
                        logging.debug(f"✅ Track name matches: expected '{expected_name}', actual '{actual_track_name}'")
                    else:
                        logging.warning(f"⚠️ Track name mismatch: expected '{expected_name}', actual '{actual_track_name}'")
                
                return name_matches
                
        except Exception as e:
            if self.config.log_details:
                logging.debug(f"Could not verify track name: {e}")
        
        return False
    
