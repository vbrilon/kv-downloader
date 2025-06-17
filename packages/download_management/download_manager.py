"""Download management for karaoke automation - orchestration, monitoring, and completion"""

import time
import logging
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    WebDriverException,
    TimeoutException
)
from ..utils import safe_click_with_scroll


class DownloadManager:
    """Handles download orchestration, monitoring, and completion detection"""
    
    def __init__(self, driver, wait):
        """Initialize download manager with Selenium driver and wait objects"""
        self.driver = driver
        self.wait = wait
        self.progress_tracker = None
        self.file_manager = None
        self.chrome_manager = None
        self.stats_reporter = None
    
    def set_progress_tracker(self, progress_tracker):
        """Set the progress tracker for status updates"""
        self.progress_tracker = progress_tracker
    
    def set_file_manager(self, file_manager):
        """Set the file manager for download operations"""
        self.file_manager = file_manager
    
    def set_chrome_manager(self, chrome_manager):
        """Set the chrome manager for download path management"""
        self.chrome_manager = chrome_manager
    
    def set_stats_reporter(self, stats_reporter):
        """Set the stats reporter for comprehensive tracking"""
        self.stats_reporter = stats_reporter
    
    def _setup_download_context(self, song_url, track_name, song_folder, track_index):
        """Setup download context and update progress tracking
        
        Args:
            song_url (str): URL of the song page
            track_name (str): Name for the downloaded file  
            song_folder (str): Song folder name (will be created if None)
            track_index (int): Track index for progress tracking
            
        Returns:
            tuple: (song_folder, song_name, track_index)
        """
        # Extract or create song folder name
        if not song_folder:
            song_folder = self.extract_song_folder_name(song_url)
        
        logging.info(f"Downloading current mix: {track_name} to folder: {song_folder}")
        
        # Extract song name from folder for stats
        song_name = song_folder
        
        # Update progress tracker
        if self.progress_tracker:
            # Use provided track_index if available, otherwise try to find by name
            if track_index is None:
                # Find track by name to get index (fallback method)
                for track in self.progress_tracker.tracks:
                    if track_name.lower() in track['name'].lower() or track['name'].lower() in track_name.lower():
                        track_index = track['index']
                        logging.debug(f"Found track index {track_index} for {track_name}")
                        break
                
                if track_index is None:
                    logging.warning(f"Could not find track index for {track_name}")
            
            if track_index is not None:
                logging.debug(f"Updating progress for track {track_index}: {track_name}")
                self.progress_tracker.update_track_status(track_index, 'downloading')
                
        return song_folder, song_name, track_index

    def _setup_file_management(self, song_folder, cleanup_existing):
        """Setup file management and configure Chrome download path
        
        Args:
            song_folder (str): Name of the song folder
            cleanup_existing (bool): Whether to clear existing files
            
        Returns:
            Path: Configured song path
        """
        # Create song-specific folder and update download path
        song_path = self.file_manager.setup_song_folder(song_folder, clear_existing=cleanup_existing)
        
        # Update Chrome download directory to song folder BEFORE clicking download
        try:
            if self.chrome_manager:
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
        
        return song_path

    def _find_download_button(self):
        """Find and validate the download button on the current page
        
        Returns:
            WebElement or None: The download button if found and usable, None otherwise
        """
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
            # Debug: show available download-related elements
            logging.debug("Available download-related elements on page:")
            try:
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                download_links = [link for link in all_links if 'download' in link.get_attribute('class').lower() or 'download' in link.text.lower()]
                for link in download_links[:5]:  # Show first 5 matches
                    logging.debug(f"  - {link.tag_name} class='{link.get_attribute('class')}' text='{link.text[:30]}'")
            except (Exception, AttributeError, WebDriverException) as e:
                logging.debug(f"Could not analyze download links: {e}")
                pass
        
        return download_button

    def _execute_download_click(self, download_button):
        """Execute the download button click and handle any popups or windows
        
        Args:
            download_button: The WebElement representing the download button
            
        Returns:
            bool: True if download click was successful, False otherwise
        """
        # Get button details for logging
        button_text = download_button.text.strip()
        button_onclick = download_button.get_attribute('onclick') or ''
        
        logging.info(f"Download button text: '{button_text}'")
        if button_onclick:
            logging.info(f"Download onclick: {button_onclick[:50]}...")
        
        # Scroll to download button and click
        logging.info("Clicking download button...")
        safe_click_with_scroll(self.driver, download_button, "download button")
        
        # Wait for any immediate UI response or popup to appear
        try:
            # Wait briefly for any popups, new windows, or page changes
            WebDriverWait(self.driver, 2).until(
                lambda driver: len(driver.window_handles) > 1 or
                               driver.current_url != self.driver.current_url
            )
        except TimeoutException:
            pass  # No immediate response detected
        
        # Check if any popup or new window appeared
        original_window_count = len(self.driver.window_handles)
        logging.debug(f"Windows before download: {original_window_count}")
        
        # Wait for download initialization to complete
        try:
            # Wait for window changes or download-related indicators
            WebDriverWait(self.driver, 3).until(
                lambda driver: len(driver.window_handles) != original_window_count or
                               "generating" in driver.page_source.lower() or
                               "preparing" in driver.page_source.lower()
            )
        except TimeoutException:
            pass  # Continue with download monitoring
        current_window_count = len(self.driver.window_handles)
        logging.debug(f"Windows after download: {current_window_count}")
        
        if current_window_count > original_window_count:
            logging.info(f"🪟 New window/popup detected ({current_window_count} vs {original_window_count})")
            popup_handled = self._handle_download_popup()
            if popup_handled:
                logging.info("✅ Download popup handled successfully")
            else:
                logging.warning("⚠️ Download popup handling had issues")
        
        # Check for download popup elements in current window (non-window popups)
        self._check_and_handle_inline_popups()
        
        return True

    def download_current_mix(self, song_url, track_name="current_mix", cleanup_existing=True, song_folder=None, key_adjustment=0, track_index=None):
        """Download the current track mix (after soloing)
        
        Args:
            song_url (str): URL of the song page
            track_name (str): Name for the downloaded file
            cleanup_existing (bool): Remove existing files before download
            song_folder (str): Optional specific folder name for the song
            key_adjustment (int): Key adjustment applied to the track (-12 to +12)
            track_index (int): Optional track index for progress tracking
        """
        # Setup download context and progress tracking
        song_folder, song_name, track_index = self._setup_download_context(
            song_url, track_name, song_folder, track_index)
        
        # Setup file management and download paths
        song_path = self._setup_file_management(song_folder, cleanup_existing)
        
        try:
            # Navigate to song page if needed
            if self.driver.current_url != song_url:
                self.driver.get(song_url)
                # Wait for song page to load and download button to be available
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a.download"))
                    )
                except TimeoutException:
                    logging.warning("Timeout waiting for download button to load")
            
            # Find and validate download button
            download_button = self._find_download_button()
            
            if not download_button:
                # Check if this is because the song hasn't been purchased
                purchase_required = self._check_purchase_required()
                if purchase_required:
                    logging.error(f"❌ SONG NOT PURCHASED: '{track_name}' is not available for download")
                    logging.error("   💳 Please purchase this song on Karaoke-Version.com to download it")
                    logging.error("   ⏭️  Skipping to next song...")
                    if self.progress_tracker and track_index:
                        self.progress_tracker.update_track_status(track_index, 'failed')
                    return False
                else:
                    logging.error("Could not find download button - unknown error")
                    return False
            
            # Verify track selection state before download
            verification_passed = self._verify_track_selection_state(track_name, track_index)
            if not verification_passed:
                logging.warning(f"⚠️ Track selection verification failed for {track_name} - proceeding anyway")
            
            # Execute download click and handle any popups
            self._execute_download_click(download_button)
            
            # Update progress tracker to indicate we're waiting for download to start
            if self.progress_tracker and track_index:
                self.progress_tracker.update_track_status(track_index, 'processing')
            
            # Wait for download to actually start (critical for proper sequencing)
            logging.info(f"⏳ Waiting for download to start for: {track_name}")
            download_started = self.file_manager.wait_for_download_to_start(track_name, song_path, track_index)
            
            if download_started:
                logging.info(f"✅ Download started for: {track_name} - proceeding to next track")
                
                # Start background monitoring for completion and file cleanup
                self.start_completion_monitoring(song_path, track_name, track_index)
                
            else:
                logging.warning(f"⚠️ Download not detected for: {track_name}")
                
                # Since we're only monitoring song folder, no download detected means failure
                logging.error(f"❌ No download detected in song folder for: {track_name}")
                if self.progress_tracker and track_index:
                    self.progress_tracker.update_track_status(track_index, 'failed')
                
                # Record failure in stats
                if self.stats_reporter:
                    self.stats_reporter.record_track_completion(song_name, track_name, success=False, 
                                                               error_message="Download not detected")
                return False
            
            # Don't mark as completed immediately since downloads continue in background
            # Progress will be updated when we check for completion later or in next iteration
            
            return True
            
        except Exception as e:
            # Update progress tracker to failed
            if self.progress_tracker and track_index:
                self.progress_tracker.update_track_status(track_index, 'failed')
            
            # Record failure in stats
            if self.stats_reporter:
                self.stats_reporter.record_track_completion(song_name, track_name, success=False, 
                                                           error_message=str(e))
            
            logging.error(f"Error downloading mix: {e}")
            return False
    
    def extract_song_folder_name(self, song_url):
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
                return self.sanitize_folder_name(folder_name)
            
            # Fallback: use domain and timestamp
            return f"karaoke_download_{int(time.time())}"
            
        except Exception as e:
            logging.warning(f"Could not extract song info from URL: {e}")
            return f"karaoke_download_{int(time.time())}"
    
    def sanitize_filesystem_name(self, name):
        """Remove invalid filesystem characters"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name
    
    def sanitize_folder_name(self, folder_name):
        """Clean folder name for filesystem compatibility"""
        folder_name = self.sanitize_filesystem_name(folder_name)
        
        # Limit length and clean up
        folder_name = folder_name[:100].strip()
        if not folder_name:
            folder_name = f"song_{int(time.time())}"
        
        return folder_name
    
    def start_completion_monitoring(self, song_path, track_name, track_index):
        """Start background monitoring for download completion and file cleanup"""
        
        def completion_monitor():
            try:
                # Get song name from song_path for stats
                song_name = song_path.name
                # Monitor for up to 5 minutes for download completion
                max_wait = 300  # 5 minutes
                check_interval = 2  # Check every 2 seconds
                waited = 0
                
                # Get initial file snapshot to track what was there before this download
                initial_files = set()
                if song_path.exists():
                    for f in song_path.iterdir():
                        if f.is_file() and any(f.name.lower().endswith(ext) for ext in ['.mp3', '.aif', '.wav']):
                            initial_files.add(f.name)
                
                logging.info(f"🔍 Starting completion monitoring for {track_name}")
                logging.info(f"📂 Initial files in folder: {len(initial_files)}")
                
                while waited < max_wait:
                    # Use WebDriverWait for the check interval instead of sleep
                    try:
                        WebDriverWait(self.driver, check_interval).until(
                            lambda driver: False  # Always timeout to create the delay
                        )
                    except TimeoutException:
                        pass  # Expected timeout for delay
                    waited += check_interval
                    
                    # Look for NEW completed downloads (files that weren't there initially)
                    logging.info(f"🔍 Checking for NEW downloads in {song_path} (waited {waited}s)")
                    new_completed_files = self._find_new_completed_files(song_path, track_name, initial_files)
                    
                    if not new_completed_files:
                        if waited % 10 == 0:  # Log every 10 seconds
                            logging.info(f"   No new completed files found yet (waited {waited}s)")
                    
                    if new_completed_files:
                        logging.info(f"🎉 NEW download completed for {track_name}: {len(new_completed_files)} files")
                        
                        # Filter to only files that need cleaning and match the current track
                        files_needing_cleanup = []
                        for file_path in new_completed_files:
                            filename = file_path.name
                            
                            # Check if this file actually matches the track we're monitoring
                            track_match = self._does_file_match_track(filename, track_name)
                            has_custom_suffix = 'Custom_Backing_Track' in filename
                            
                            if has_custom_suffix and track_match:
                                files_needing_cleanup.append(file_path)
                                logging.info(f"📝 File needs cleanup (matches {track_name}): {filename}")
                            elif has_custom_suffix and not track_match:
                                logging.info(f"📝 Skipping file (doesn't match {track_name}): {filename}")
                            else:
                                logging.debug(f"📝 File already clean: {filename}")
                        
                        # Calculate file size for stats (all completed files, not just ones needing cleanup)
                        total_file_size = sum(f.stat().st_size for f in new_completed_files)
                        
                        # Clean up filenames only for files that actually need it
                        for file_path in files_needing_cleanup:
                            self.file_manager.clean_downloaded_filename(file_path, track_name)
                        
                        # If we cleaned any files, log success; otherwise log that files were already clean
                        if files_needing_cleanup:
                            logging.info(f"✅ Cleaned {len(files_needing_cleanup)} files for {track_name}")
                        else:
                            logging.info(f"✅ All files already clean for {track_name}")
                        
                        # Perform basic content validation on completed files
                        validation_warnings = []
                        for file_path in new_completed_files:
                            try:
                                validation_result = self.file_manager.validate_audio_content(file_path, track_name)
                                if validation_result['warnings']:
                                    validation_warnings.extend(validation_result['warnings'])
                                if validation_result['errors']:
                                    logging.error(f"❌ Content validation errors for {file_path.name}: {validation_result['errors']}")
                            except Exception as e:
                                logging.warning(f"⚠️ Could not validate content for {file_path.name}: {e}")
                        
                        # Log summary of validation warnings if any
                        if validation_warnings:
                            logging.warning(f"⚠️ Content validation warnings for {track_name}:")
                            for warning in validation_warnings[:3]:  # Limit to first 3 warnings
                                logging.warning(f"   - {warning}")
                            if len(validation_warnings) > 3:
                                logging.warning(f"   ... and {len(validation_warnings) - 3} more warnings")
                        
                        # Update progress tracker
                        if self.progress_tracker and track_index:
                            self.progress_tracker.update_track_status(track_index, 'completed', progress=100)
                        
                        # Record success in stats
                        if self.stats_reporter:
                            self.stats_reporter.record_track_completion(song_name, track_name, success=True, 
                                                                       file_size=total_file_size)
                        
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
                    
                    # Record timeout failure in stats
                    if self.stats_reporter:
                        self.stats_reporter.record_track_completion(song_name, track_name, success=False, 
                                                                   error_message="Download completion timeout")
                        
            except Exception as e:
                logging.error(f"Error in completion monitoring for {track_name}: {e}")
                if self.progress_tracker and track_index:
                    self.progress_tracker.update_track_status(track_index, 'failed')
                
                # Record monitoring error in stats
                if self.stats_reporter:
                    self.stats_reporter.record_track_completion(song_name, track_name, success=False, 
                                                               error_message=f"Monitoring error: {str(e)}")
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=completion_monitor, daemon=True)
        monitor_thread.start()
        logging.info(f"🎆 Started background completion monitoring for {track_name}")
    
    def _find_new_completed_files(self, song_path, track_name, initial_files):
        """Find newly completed files that weren't in the initial snapshot"""
        try:
            if not song_path.exists():
                return []
            
            new_files = []
            
            for file_path in song_path.iterdir():
                if file_path.is_file():
                    filename = file_path.name
                    filename_lower = filename.lower()
                    
                    # Check if it's an audio file (not .crdownload)
                    is_audio = any(filename_lower.endswith(ext) for ext in ['.mp3', '.aif', '.wav', '.m4a'])
                    is_recent = (time.time() - file_path.stat().st_mtime) < 300  # Less than 5 minutes old
                    is_new = filename not in initial_files  # Wasn't there when we started monitoring
                    
                    if is_audio and is_recent and is_new:
                        # Make sure there's no corresponding .crdownload file
                        crdownload_path = file_path.with_suffix(file_path.suffix + '.crdownload')
                        if not crdownload_path.exists():
                            new_files.append(file_path)
                            logging.info(f"✅ Found NEW completed download: {filename}")
            
            return new_files
            
        except Exception as e:
            logging.debug(f"Error finding new completed files: {e}")
            return []
    
    def _does_file_match_track(self, filename, track_name):
        """Check if a downloaded filename matches the track we're monitoring"""
        try:
            filename_lower = filename.lower()
            track_lower = track_name.lower()
            
            # Clean both names for comparison
            clean_filename = filename_lower.replace('_', ' ').replace('-', ' ')
            clean_track = track_lower.replace('_', ' ').replace('-', ' ')
            
            # Handle special cases first
            # For "Click" tracks, the filename often just contains "click"
            if 'click' in clean_track and 'click' in clean_filename:
                logging.debug(f"Track matching for '{filename}' vs '{track_name}': Special 'click' track match -> MATCH")
                return True
            
            # For vocal tracks, be more flexible with naming variations
            if 'vocal' in clean_track:
                vocal_variations = ['vocal', 'vocals', 'voice', 'singer', 'lead vocal', 'backing vocal']
                if any(variation in clean_filename for variation in vocal_variations):
                    logging.debug(f"Track matching for '{filename}' vs '{track_name}': Vocal track variation match -> MATCH")
                    return True
            
            # Check for exact track name match in filename
            track_words = clean_track.split()
            
            # All significant words from track name should be in filename
            # Skip common words like 'the', 'a', 'an', 'and', 'or'
            skip_words = {'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'intro', 'count'}
            significant_words = [word for word in track_words if word not in skip_words and len(word) > 2]
            
            if not significant_words:
                # If no significant words, fall back to basic check
                return track_lower in filename_lower
            
            # Check if most significant words are present
            matches = sum(1 for word in significant_words if word in clean_filename)
            match_ratio = matches / len(significant_words) if significant_words else 0
            
            # For single-word tracks, be more lenient
            if len(significant_words) == 1:
                is_match = matches >= 1  # Must have the one significant word
            else:
                # For multi-word tracks, require at least 60% match
                is_match = match_ratio >= 0.6
            
            logging.debug(f"Track matching for '{filename}' vs '{track_name}': {matches}/{len(significant_words)} significant words matched ({match_ratio:.1%}) -> {'MATCH' if is_match else 'NO MATCH'}")
            
            return is_match
            
        except Exception as e:
            logging.debug(f"Error in track matching: {e}")
            # Fallback to basic string containment
            return track_name.lower() in filename.lower()
    
    def _handle_download_popup(self):
        """Handle download popup windows that appear after clicking download"""
        try:
            original_window = self.driver.window_handles[0]
            
            # Get all windows and find the new one
            all_windows = self.driver.window_handles
            new_windows = [w for w in all_windows if w != original_window]
            
            for new_window in new_windows:
                try:
                    self.driver.switch_to.window(new_window)
                    logging.info(f"📄 Popup window title: {self.driver.title}")
                    logging.info(f"📄 Popup window URL: {self.driver.current_url}")
                    
                    # Look for download-related content
                    page_text = self.driver.page_source.lower()
                    has_download_content = any(phrase in page_text for phrase in [
                        'download', 'generating', 'preparing', 'your file', 'custom backing track'
                    ])
                    
                    if has_download_content:
                        logging.info("🎵 Download generation page detected!")
                        
                        # Wait a bit for download to initialize, then close popup
                        try:
                            WebDriverWait(self.driver, 3).until(
                                lambda driver: True  # Brief wait for initialization
                            )
                        except TimeoutException:
                            pass
                        
                        # Close the popup
                        self.driver.close()
                        logging.info("🗂️ Closed download popup window")
                    else:
                        logging.info("📄 Popup doesn't appear to be download-related")
                        # Close it anyway to avoid interference
                        self.driver.close()
                        logging.info("🗂️ Closed non-download popup window")
                
                except Exception as e:
                    logging.warning(f"Error handling popup window: {e}")
                    try:
                        self.driver.close()  # Try to close problematic popup
                    except:
                        pass
            
            # Ensure we're back on the main window
            self.driver.switch_to.window(original_window)
            return True
            
        except Exception as e:
            logging.error(f"Error in popup handling: {e}")
            try:
                # Try to get back to main window
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _check_and_handle_inline_popups(self):
        """Check for and handle inline popups that don't create new windows"""
        try:
            # Look for common popup/modal selectors
            popup_selectors = [
                ".modal",
                ".popup",
                ".dialog",
                ".overlay",
                "[class*='popup']",
                "[class*='modal']",
                "[class*='overlay']"
            ]
            
            for selector in popup_selectors:
                try:
                    popup_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for popup in popup_elements:
                        if popup.is_displayed():
                            logging.info(f"🔍 Found inline popup with selector: {selector}")
                            
                            # Look for close button
                            close_selectors = [
                                "button[class*='close']",
                                ".close",
                                "[aria-label='close']",
                                "[aria-label='Close']",
                                "button:contains('×')",
                                "button:contains('X')"
                            ]
                            
                            closed = False
                            for close_selector in close_selectors:
                                try:
                                    close_buttons = popup.find_elements(By.CSS_SELECTOR, close_selector)
                                    for close_btn in close_buttons:
                                        if close_btn.is_displayed() and close_btn.is_enabled():
                                            close_btn.click()
                                            logging.info(f"✅ Closed inline popup using: {close_selector}")
                                            closed = True
                                            break
                                    if closed:
                                        break
                                except:
                                    continue
                            
                            if not closed:
                                # Try clicking outside the popup
                                try:
                                    self.driver.execute_script("arguments[0].style.display = 'none';", popup)
                                    logging.info("✅ Hid inline popup with JavaScript")
                                except:
                                    logging.debug("Could not hide inline popup")
                
                except:
                    continue
                    
        except Exception as e:
            logging.debug(f"Error checking for inline popups: {e}")
    
    def _check_purchase_required(self):
        """Check if the current page indicates the song needs to be purchased"""
        try:
            # Look for indicators that the song hasn't been purchased
            purchase_indicators = [
                # Look for "Add to Cart" or "Buy" buttons
                "//a[contains(text(), 'Add to cart')]",
                "//button[contains(text(), 'Add to cart')]",
                "//a[contains(text(), 'Buy')]", 
                "//button[contains(text(), 'Buy')]",
                # Look for price indicators
                "//span[contains(@class, 'price')]",
                "//div[contains(@class, 'price')]",
                # Look for "Purchase" or "Add to basket" text
                "//a[contains(text(), 'Purchase')]",
                "//a[contains(text(), 'Add to basket')]",
                "//button[contains(text(), 'Purchase')]"
            ]
            
            for indicator in purchase_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    if elements and any(elem.is_displayed() for elem in elements):
                        logging.debug(f"Found purchase indicator: {indicator}")
                        return True
                except (Exception, NoSuchElementException) as e:
                    logging.debug(f"Purchase indicator check failed: {e}")
                    continue
            
            # Also check for absence of premium content indicators
            # If there are tracks but no download button, it's likely unpurchased
            track_elements = self.driver.find_elements(By.CSS_SELECTOR, ".track")
            if track_elements:
                logging.debug(f"Found {len(track_elements)} tracks but no download button - likely unpurchased")
                return True
            
            return False
            
        except Exception as e:
            logging.debug(f"Error checking purchase status: {e}")
            return False  # Default to False if we can't determine
    
    def _verify_track_selection_state(self, track_name, track_index):
        """Verify that the correct track is selected/isolated before download
        
        Args:
            track_name (str): Name of the track that should be isolated
            track_index (str/int): Data-index of the track that should be active
            
        Returns:
            bool: True if verification passes, False otherwise
        """
        try:
            logging.info(f"🔍 Verifying track selection state for {track_name} (index {track_index})")
            
            verification_results = {
                'solo_button_active': False,
                'track_element_found': False,
                'other_solos_inactive': True,
                'track_name_match': False
            }
            
            # 1. Check if the specific track's solo button is active
            try:
                track_selector = f".track[data-index='{track_index}']"
                track_elements = self.driver.find_elements(By.CSS_SELECTOR, track_selector)
                
                if track_elements:
                    verification_results['track_element_found'] = True
                    track_element = track_elements[0]
                    
                    # Find solo button within this track
                    solo_button = track_element.find_element(By.CSS_SELECTOR, "button.track__solo")
                    button_classes = solo_button.get_attribute('class') or ''
                    
                    if 'is-active' in button_classes.lower() or 'active' in button_classes.lower():
                        verification_results['solo_button_active'] = True
                        logging.debug(f"✅ Solo button is active for track {track_index}")
                    else:
                        logging.warning(f"⚠️ Solo button not active for track {track_index} - classes: {button_classes}")
                    
                    # Check track name matches
                    try:
                        caption_element = track_element.find_element(By.CSS_SELECTOR, ".track__caption")
                        actual_track_name = caption_element.text.strip()
                        
                        # Normalize names for comparison
                        normalized_expected = track_name.lower().replace('_', ' ').replace('-', ' ')
                        normalized_actual = actual_track_name.lower().replace('_', ' ').replace('-', ' ')
                        
                        # Check if names match (allowing for partial matches)
                        if normalized_expected in normalized_actual or normalized_actual in normalized_expected:
                            verification_results['track_name_match'] = True
                            logging.debug(f"✅ Track name matches: expected '{track_name}', actual '{actual_track_name}'")
                        else:
                            logging.warning(f"⚠️ Track name mismatch: expected '{track_name}', actual '{actual_track_name}'")
                    except Exception as e:
                        logging.debug(f"Could not verify track name: {e}")
                        
                else:
                    logging.warning(f"⚠️ Could not find track element with data-index '{track_index}'")
                    
            except Exception as e:
                logging.warning(f"Error checking specific track solo state: {e}")
            
            # 2. Check that no other solo buttons are active (mutual exclusivity)
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
                        
                        if 'is-active' in button_classes.lower() or 'active' in button_classes.lower():
                            active_count += 1
                            if button_track_index != str(track_index):
                                other_active_tracks.append(button_track_index)
                    except Exception as e:
                        logging.debug(f"Error checking solo button state: {e}")
                
                if active_count == 1 and not other_active_tracks:
                    logging.debug(f"✅ Exactly one solo button active (track {track_index})")
                elif active_count == 0:
                    logging.warning(f"⚠️ No solo buttons are active (expected track {track_index})")
                    verification_results['other_solos_inactive'] = False
                elif other_active_tracks:
                    logging.warning(f"⚠️ Other tracks also have active solos: {other_active_tracks}")
                    verification_results['other_solos_inactive'] = False
                else:
                    logging.debug(f"Solo button state appears correct ({active_count} active)")
                    
            except Exception as e:
                logging.warning(f"Error checking other solo buttons: {e}")
            
            # 3. Additional UI state checks
            try:
                # Check for any visible UI indicators of track isolation
                page_text = self.driver.page_source.lower()
                
                # Look for indicators that might suggest track isolation is working
                isolation_indicators = [
                    'solo', 'isolated', 'muted', 'active'
                ]
                
                found_indicators = [indicator for indicator in isolation_indicators if indicator in page_text]
                if found_indicators:
                    logging.debug(f"Found UI isolation indicators: {found_indicators}")
                    
            except Exception as e:
                logging.debug(f"Error checking UI state indicators: {e}")
            
            # Calculate overall verification score
            passed_checks = sum([
                verification_results['solo_button_active'],
                verification_results['track_element_found'],
                verification_results['other_solos_inactive'],
                verification_results['track_name_match']
            ])
            
            total_checks = len(verification_results)
            verification_score = passed_checks / total_checks
            
            logging.info(f"🔍 Track selection verification: {passed_checks}/{total_checks} checks passed ({verification_score:.1%})")
            
            # Consider verification passed if at least 75% of checks pass
            verification_passed = verification_score >= 0.75
            
            if verification_passed:
                logging.info(f"✅ Track selection verification PASSED for {track_name}")
            else:
                logging.warning(f"⚠️ Track selection verification FAILED for {track_name}")
                logging.warning(f"   Failed checks: {[k for k, v in verification_results.items() if not v]}")
            
            return verification_passed
            
        except Exception as e:
            logging.error(f"❌ Error during track selection verification: {e}")
            return False  # Fail safely