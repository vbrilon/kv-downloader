"""Download management for karaoke automation - orchestration, monitoring, and completion"""

import time
import logging
import string
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchElementException,
    NoSuchWindowException,
    TimeoutException,
    WebDriverException,
)
from ..utils import js_click_with_scroll, profile_timing, profile_selenium, is_solo_button_active, ACTIVE_SOLO_CLASS_TOKENS
from ..configuration.selectors import DOWNLOAD_BUTTON_SELECTORS
from ..di.interfaces import IProgressTracker, IFileManager, IChromeManager, IStatsReporter
from ..configuration.config import (WEBDRIVER_DEFAULT_TIMEOUT, WEBDRIVER_SHORT_TIMEOUT, 
                                    WEBDRIVER_BRIEF_TIMEOUT, DOWNLOAD_MAX_WAIT, 
                                    DOWNLOAD_CHECK_INTERVAL, TRACK_SELECTION_MAX_RETRIES, 
                                    RETRY_VERIFICATION_DELAY, LOG_INTERVAL_SECONDS, 
                                    PROGRESS_UPDATE_LOG_INTERVAL, TRACK_MATCH_MIN_RATIO)


class DownloadManager:
    """Handles download orchestration, monitoring, and completion detection"""
    
    def __init__(self, 
                 driver, 
                 wait,
                 progress_tracker: IProgressTracker,
                 file_manager: IFileManager,
                 chrome_manager: IChromeManager,
                 stats_reporter: IStatsReporter):
        """Initialize download manager with all required dependencies"""
        self.driver = driver
        self.wait = wait
        self.progress_tracker = progress_tracker
        self.file_manager = file_manager
        self.chrome_manager = chrome_manager
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
        # Use provided track_index if available, otherwise try to find by name.
        # `tracks` is not part of the IProgressTracker contract — adapters may
        # not expose it — so look it up defensively rather than assuming.
        if track_index is None:
            tracks = getattr(self.progress_tracker, 'tracks', None) or []
            for track in tracks:
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
            self.chrome_manager.set_download_path(song_path.absolute())
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
        # Find the download button using centralized selectors
        logging.debug(f"Searching for download button with {len(DOWNLOAD_BUTTON_SELECTORS)} selectors")
        download_button = None
        for i, selector in enumerate(DOWNLOAD_BUTTON_SELECTORS):
            try:
                logging.debug(f"Trying download selector {i+1}/{len(DOWNLOAD_BUTTON_SELECTORS)}: {selector}")
                if selector.startswith("//"):
                    # Wait for presence with XPath
                    download_button = WebDriverWait(self.driver, WEBDRIVER_SHORT_TIMEOUT).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    # Wait for presence with CSS
                    download_button = WebDriverWait(self.driver, WEBDRIVER_SHORT_TIMEOUT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                
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
        """Click the download button, then wait for the readiness modal to populate.

        Verified 2026-05-08 on the live site: clicking `a.custom__song-download`
        fires `mixer.getMix();return false;` which triggers ~14s of server-side
        mix generation. When generation completes, the modal's __overlay sibling
        gets the `is-open` class and the modal__content is populated.

        We wait for that activation signal directly. Replaces the previous code
        that polled `len(driver.window_handles)` and `page_source.lower()` for
        text like "generating"/"preparing" — both with full timeouts that always
        expired since (a) no new window opens on this site, (b) page_source is
        an expensive full-DOM serialization.
        """
        from ..configuration.selectors import DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR

        button_text = download_button.text.strip()
        button_onclick = download_button.get_attribute('onclick') or ''
        logging.info(f"Download button text: '{button_text}'")
        if button_onclick:
            logging.info(f"Download onclick: {button_onclick[:50]}...")

        logging.info("Clicking download button...")
        if not js_click_with_scroll(self.driver, download_button, "download button"):
            raise Exception("DOWNLOAD_BUTTON_CLICK_FAILED")

        # Server mix-generation runs ~14s typical; allow generous timeout.
        # When it completes, .modal__overlay.is-open is the deterministic signal.
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR)
                )
            )
            logging.debug("✅ Download modal overlay opened")
        except TimeoutException:
            logging.warning(
                "⚠️ Download modal overlay did not open within 30s — "
                "proceeding to file-system monitoring anyway"
            )

        # Note: we deliberately do NOT close the modal here. The next phase
        # (`_wait_for_download_readiness` in `_monitor_download_progress`) needs
        # to read the readiness text from the populated modal. Closing first was
        # the bug that made the previous code fall back to page_source polling.
        return True

    @profile_timing("download_current_mix", "download_management", "method")
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
            # Navigate to song page and find download button
            download_button = self._navigate_and_find_download_button(song_url)
            
            # Perform pre-download validation checks
            if not self._validate_pre_download_requirements(track_name, track_index, song_name):
                return False
            
            # Execute download action
            self._execute_download_action(download_button, track_index)
            
            # Monitor download completion
            if not self._monitor_download_completion(song_path, track_name, track_index, song_name):
                return False
            
            return True

        except (InvalidSessionIdException, NoSuchWindowException):
            # Chrome is gone — propagate so callers can distinguish this from
            # a per-track product failure and decide whether to abort.
            raise
        except Exception as e:
            # Handle specific error types
            if str(e) == "SONG_NOT_PURCHASED":
                logging.error(f"❌ SONG NOT PURCHASED: '{track_name}' is not available for download")
                logging.error("   💳 Please purchase this song on Karaoke-Version.com to download it")
                logging.error("   ⏭️  Skipping to next song...")
            elif str(e) == "DOWNLOAD_BUTTON_NOT_FOUND":
                logging.error("Could not find download button - unknown error")
            else:
                logging.error(f"Error downloading mix: {e}")

            # Update progress tracker to failed
            if self.progress_tracker and track_index:
                self.progress_tracker.update_track_status(track_index, 'failed')

            # Record failure in stats
            self.stats_reporter.record_track_completion(song_name, track_name, success=False,
                                                       error_message=str(e))

            return False
    
    @profile_timing("_navigate_and_find_download_button", "download_management", "method")
    def _navigate_and_find_download_button(self, song_url):
        """Navigate to song page and locate download button
        
        Args:
            song_url (str): URL of the song page
            
        Returns:
            download_button: WebElement if found
            
        Raises:
            Exception: If navigation fails or button cannot be found
        """
        # Navigate to song page if needed
        if self.driver.current_url != song_url:
            self.driver.get(song_url)
            # Wait for song page to load and download button to be available
            try:
                WebDriverWait(self.driver, WEBDRIVER_DEFAULT_TIMEOUT).until(
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
                raise Exception("SONG_NOT_PURCHASED")
            else:
                raise Exception("DOWNLOAD_BUTTON_NOT_FOUND")
        
        return download_button
    
    @profile_timing("_validate_pre_download_requirements", "download_management", "method")
    def _validate_pre_download_requirements(self, track_name, track_index, song_name):
        """Verify the solo state once before clicking download.

        We used to call this twice ("initial" and "final") with nothing in between,
        which doubled cost and hid no real bug. The single call is sufficient: the
        solo button cannot change state between two adjacent Python statements with
        no DOM interaction.
        """
        if self._verify_track_selection_with_retry(track_name, track_index):
            return True

        logging.error(f"❌ Track selection verification failed for {track_name} - BLOCKING DOWNLOAD")
        if self.progress_tracker and track_index:
            self.progress_tracker.update_track_status(track_index, 'failed')
        self.stats_reporter.record_track_completion(
            song_name, track_name, success=False,
            error_message="Solo verification failed"
        )
        return False
    
    @profile_timing("_execute_download_action", "download_management", "method")
    def _execute_download_action(self, download_button, track_index):
        """Execute download click and update progress tracking
        
        Args:
            download_button: WebElement for the download button
            track_index (int): Track index for progress tracking
            
        Returns:
            bool: True if click executed successfully
        """
        # Execute download click and handle any popups
        self._execute_download_click(download_button)
        
        # Update progress tracker to indicate we're waiting for download to start
        if self.progress_tracker and track_index:
            self.progress_tracker.update_track_status(track_index, 'processing')
        
        return True
    
    @profile_timing("_monitor_download_completion", "download_management", "method")
    def _monitor_download_completion(self, song_path, track_name, track_index, song_name):
        """Wait for download start and monitor completion
        
        Args:
            song_path (str): Path to song directory
            track_name (str): Name of the track being downloaded
            track_index (int): Track index for progress tracking
            song_name (str): Song name for stats recording
            
        Returns:
            bool: True if download completes successfully, False if failed
        """
        # Wait for download to actually start (critical for proper sequencing)
        logging.info(f"⏳ Waiting for download to start for: {track_name}")
        download_started = self.file_manager.wait_for_download_to_start(track_name, song_path, track_index)
        
        if download_started:
            logging.info(f"✅ Download started for: {track_name} - monitoring completion")

            # Capture the worker's actual outcome via a shared dict. Without this,
            # a started-but-timed-out download (e.g. .crdownload stuck at 32KB
            # because the CDN connection died) would silently return True here,
            # bypassing the retry tier in karaoke_automator.
            result = {"success": False}
            monitor_thread = self.start_completion_monitoring(song_path, track_name, track_index, result)

            logging.info(f"⏳ Waiting for {track_name} completion monitoring to finish...")
            monitor_thread.join()
            logging.info(f"✅ Completion monitoring finished for {track_name} (success={result['success']})")

            return result["success"]
        else:
            logging.warning(f"⚠️ Download not detected for: {track_name}")
            
            # Since we're only monitoring song folder, no download detected means failure
            logging.error(f"❌ No download detected in song folder for: {track_name}")
            if self.progress_tracker and track_index:
                self.progress_tracker.update_track_status(track_index, 'failed')
            
            # Record failure in stats
            self.stats_reporter.record_track_completion(song_name, track_name, success=False, 
                                                       error_message="Download not detected")
            return False

    def extract_song_folder_name(self, song_url):
        """Extract song information from URL to create folder name"""
        try:
            # Extract from URL pattern: /custombackingtrack/artist/song.html
            url_parts = song_url.rstrip('/').split('/')
            if len(url_parts) >= 3 and 'custombackingtrack' in url_parts:
                artist_part = url_parts[-2] if len(url_parts) >= 2 else 'unknown_artist'
                song_part = url_parts[-1].replace('.html', '') if len(url_parts) >= 1 else 'unknown_song'
                
                # capwords (not str.title) so contractions like "don't" don't become "Don'T"
                artist = string.capwords(artist_part.replace('-', ' '))
                song = string.capwords(song_part.replace('-', ' '))
                
                folder_name = f"{artist} - {song}"
                return self.sanitize_folder_name(folder_name)
            
            # Fallback: use domain and timestamp
            return f"karaoke_download_{int(time.time())}"
            
        except Exception as e:
            logging.warning(f"Could not extract song info from URL: {e}")
            return f"karaoke_download_{int(time.time())}"
    
    def sanitize_filesystem_name(self, name):
        """Remove invalid filesystem characters (preserve apostrophes)"""
        invalid_chars = '<>:"/\\|?*'  # Removed apostrophe from invalid chars
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
    
    def start_completion_monitoring(self, song_path, track_name, track_index, result=None):
        """Start background monitoring for download completion and file cleanup.

        result: optional dict updated with {'success': bool} reflecting the
        worker's actual outcome. Without it, callers can't distinguish a
        completed download from a started-but-timed-out one.
        """
        if result is None:
            result = {"success": False}
        monitor_thread = threading.Thread(
            target=self._completion_monitor_worker,
            args=(song_path, track_name, track_index, result),
            daemon=False
        )
        monitor_thread.start()
        logging.info(f"🎆 Started background completion monitoring for {track_name}")
        return monitor_thread

    def _completion_monitor_worker(self, song_path, track_name, track_index, result):
        """Worker function for completion monitoring. Sets result['success']."""
        try:
            context = self._initialize_monitoring_context(song_path, track_name)
            self._monitor_download_progress(context, track_index, result)
        except Exception as e:
            self._handle_monitoring_error(e, song_path.name, track_name, track_index)
            # result['success'] stays False (default)
    
    def _initialize_monitoring_context(self, song_path, track_name):
        """Initialize monitoring context and parameters"""
        context = {
            'song_name': song_path.name,
            'song_path': song_path,
            'track_name': track_name,
            'max_wait': DOWNLOAD_MAX_WAIT,  # 5 minutes
            'check_interval': DOWNLOAD_CHECK_INTERVAL,  # Check every 2 seconds
            'waited': 0,
            'initial_files': self._get_initial_file_snapshot(song_path)
        }
        
        logging.info(f"🔍 Starting completion monitoring for {track_name}")
        logging.info(f"📂 Initial files in folder: {len(context['initial_files'])}")
        
        return context
    
    def _get_initial_file_snapshot(self, song_path):
        """Get snapshot of existing files before download - optimized"""
        initial_files = set()
        
        # Use file manager's optimized methods to reduce file system calls
        song_info = self.file_manager._get_file_info(song_path)
        if song_info['exists']:
            # Get audio files using optimized directory scan
            audio_patterns = {'.mp3', '.aif', '.wav'}
            files_info = self.file_manager._scan_directory_cached(song_path, audio_patterns)
            
            for file_info in files_info:
                if file_info['is_file']:
                    initial_files.add(file_info['name'])
        
        return initial_files
    
    @profile_timing("_wait_for_download_readiness", "download_management", "method")
    def _wait_for_download_readiness(self, track_name, max_wait=60):
        """Wait for the readiness text to appear inside the populated modal.

        Reads modal element text only — does NOT read page_source. The earlier
        version polled the entire DOM serialization on every tick across all
        windows; this version waits for the modal__overlay.is-open class
        (verified 2026-05-08 to be the deterministic activation signal) and
        then reads modal__content text.

        Returns True if readiness detected, False on timeout.
        """
        from ..configuration.selectors import (
            DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR,
            DOWNLOAD_MODAL_CONTENT_SELECTOR,
        )

        primary_pattern = "you can also click on the link below to manually begin your download:"
        fallback_patterns = (
            "your download will begin in a moment",
            "download will begin",
            "download is ready",
            "click here to download",
            "download starting",
        )

        def readiness_in_modal(_driver):
            try:
                # Step 1: is the modal active at all?
                overlays = _driver.find_elements(
                    By.CSS_SELECTOR, DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR
                )
                if not overlays:
                    return False
                # Step 2: read the populated content's text
                contents = _driver.find_elements(By.CSS_SELECTOR, DOWNLOAD_MODAL_CONTENT_SELECTOR)
                for c in contents:
                    text = (c.text or "").lower()
                    if primary_pattern in text:
                        return "primary"
                    for pat in fallback_patterns:
                        if pat in text:
                            return pat
            except Exception:
                pass
            return False

        try:
            matched = WebDriverWait(self.driver, max_wait, poll_frequency=0.5).until(readiness_in_modal)
            logging.info(f"🎉 Download readiness ({matched}) detected for {track_name}")
            return True
        except TimeoutException:
            logging.warning(f"⚠️ Download readiness not detected within {max_wait}s for {track_name}")
            return False
    
    def _monitor_download_progress(self, context, track_index, result=None):
        """Main monitoring loop. Scan-then-sleep so an already-present file is
        detected on iteration 0 instead of after one full check_interval.

        result: optional dict; sets result['success'] = True on completion. Stays
        False on timeout (so the caller can route through the retry tier).
        """
        download_ready = self._wait_for_download_readiness(context['track_name'])
        if download_ready:
            logging.info(f"✅ Download ready signal detected for {context['track_name']}")
            # Now (and only now) close the modal — we've already extracted
            # what we needed. This was the previous code's bug: closing first
            # forced page_source polling for the readiness text.
            self._check_and_handle_inline_popups()
        else:
            logging.warning(f"⚠️ Download readiness not detected for {context['track_name']}, falling back")
            self._wait_for_check_interval(3)
            context['waited'] += 3

        download_detected = False
        in_progress_detected = False
        adaptive_interval = context['check_interval']

        while context['waited'] < context['max_wait']:
            in_progress_files = self._check_for_in_progress_downloads(context['song_path'])
            new_completed_files = self._check_for_new_downloads(context)

            if in_progress_files and not in_progress_detected:
                in_progress_detected = True
                download_detected = True
                adaptive_interval = 2
                logging.info(f"🚀 Download in progress for {context['track_name']}, polling at 2s")
            elif in_progress_detected and not in_progress_files:
                adaptive_interval = 1
                logging.info(f"⚡ Download completion imminent for {context['track_name']}, polling at 1s")

            if new_completed_files:
                self._handle_completed_download(new_completed_files, context, track_index)
                if result is not None:
                    result["success"] = True
                return

            if download_detected:
                if context['waited'] % 5 == 0:
                    progress_status = "in progress" if in_progress_files else "completing"
                    logging.info(f"   📊 Download {progress_status} for {context['track_name']} (waited {context['waited']}s)")
            else:
                self._update_progress_if_needed(context, track_index)

            self._wait_for_check_interval(adaptive_interval)
            context['waited'] += adaptive_interval

        self._handle_timeout(context['track_name'], track_index, context['song_name'])
    
    def _wait_for_check_interval(self, check_interval):
        """Wait for the specified check interval"""
        try:
            WebDriverWait(self.driver, check_interval).until(
                lambda driver: False  # Always timeout to create the delay
            )
        except TimeoutException:
            pass  # Expected timeout for delay
    
    def _check_for_in_progress_downloads(self, song_path):
        """Check for in-progress download files (.crdownload) for intelligent timing"""
        try:
            in_progress_files = []
            if song_path.exists():
                for file_path in song_path.iterdir():
                    if file_path.is_file() and file_path.suffix == '.crdownload':
                        in_progress_files.append(file_path)
            return in_progress_files
        except Exception as e:
            logging.debug(f"Error checking for in-progress downloads: {e}")
            return []
    
    def _check_for_new_downloads(self, context):
        """Check for newly completed download files"""
        logging.info(f"🔍 Checking for NEW downloads in {context['song_path']} (waited {context['waited']}s)")
        new_completed_files = self._find_new_completed_files(
            context['song_path'], context['track_name'], context['initial_files']
        )
        
        if not new_completed_files and context['waited'] % LOG_INTERVAL_SECONDS == 0:  # Log every 10 seconds
            logging.info(f"   No new completed files found yet (waited {context['waited']}s)")
        
        return new_completed_files
    
    def _handle_completed_download(self, new_completed_files, context, track_index):
        """Handle completed download files"""
        logging.info(f"🎉 NEW download completed for {context['track_name']}: {len(new_completed_files)} files")
        
        files_needing_cleanup = self._identify_files_needing_cleanup(new_completed_files, context['track_name'])
        total_file_size = sum(f.stat().st_size for f in new_completed_files)
        
        # Clean files and get updated paths
        updated_file_paths = self._clean_downloaded_files(files_needing_cleanup, context['track_name'])
        
        # Update the file list with cleaned paths
        files_to_validate = []
        for original_path in new_completed_files:
            # Check if this file was cleaned (renamed)
            updated_path = updated_file_paths.get(original_path, original_path)
            files_to_validate.append(updated_path)
        
        self._validate_downloaded_files(files_to_validate, context['track_name'])
        self._update_completion_tracking(track_index, context['song_name'], context['track_name'], total_file_size)
    
    def _identify_files_needing_cleanup(self, new_completed_files, track_name):
        """Identify which files need filename cleanup"""
        files_needing_cleanup = []
        for file_path in new_completed_files:
            filename = file_path.name
            track_match = self._does_file_match_track(filename, track_name)
            has_custom_suffix = 'Custom_Backing_Track' in filename
            
            if has_custom_suffix:
                files_needing_cleanup.append(file_path)
                logging.info(f"📝 File needs cleanup (Custom_Backing_Track suffix): {filename}")
            else:
                logging.debug(f"📝 File already clean: {filename}")
        
        return files_needing_cleanup
    
    def _clean_downloaded_files(self, files_needing_cleanup, track_name):
        """Clean filenames for downloaded files and return path mapping"""
        updated_file_paths = {}
        
        for file_path in files_needing_cleanup:
            new_path = self.file_manager.clean_downloaded_filename(file_path, track_name)
            updated_file_paths[file_path] = new_path
        
        if files_needing_cleanup:
            logging.info(f"✅ Cleaned {len(files_needing_cleanup)} files for {track_name}")
        else:
            logging.info(f"✅ All files already clean for {track_name}")
        
        return updated_file_paths
    
    def _validate_downloaded_files(self, new_completed_files, track_name):
        """Perform content validation on downloaded files"""
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
        
        if validation_warnings:
            self._log_validation_warnings(validation_warnings, track_name)
    
    def _log_validation_warnings(self, validation_warnings, track_name):
        """Log validation warnings with summary"""
        logging.warning(f"⚠️ Content validation warnings for {track_name}:")
        for warning in validation_warnings[:3]:  # Limit to first 3 warnings
            logging.warning(f"   - {warning}")
        if len(validation_warnings) > 3:
            logging.warning(f"   ... and {len(validation_warnings) - 3} more warnings")
    
    def _update_completion_tracking(self, track_index, song_name, track_name, total_file_size):
        """Update progress and statistics tracking for completed download"""
        if self.progress_tracker and track_index:
            self.progress_tracker.update_track_status(track_index, 'completed', progress=100)
        
        self.stats_reporter.record_track_completion(song_name, track_name, success=True, 
                                                   file_size=total_file_size)
    
    def _update_progress_if_needed(self, context, track_index):
        """Update progress periodically for ongoing downloads"""
        if context['waited'] % PROGRESS_UPDATE_LOG_INTERVAL == 0 and self.progress_tracker and track_index:  # Every 20 seconds
            crdownload_files = list(context['song_path'].glob("*.crdownload"))
            if crdownload_files:
                progress = min(95, 25 + (context['waited'] / context['max_wait']) * 70)  # 25% to 95%
                self.progress_tracker.update_track_status(track_index, 'downloading', progress=progress)
    
    def _handle_timeout(self, track_name, track_index, song_name):
        """Handle download monitoring timeout"""
        logging.warning(f"⚠️ Download completion monitoring timed out for {track_name}")
        
        if self.progress_tracker and track_index:
            self.progress_tracker.update_track_status(track_index, 'failed')
        
        self.stats_reporter.record_track_completion(song_name, track_name, success=False, 
                                                   error_message="Download completion timeout")
    
    def _handle_monitoring_error(self, error, song_name, track_name, track_index):
        """Handle errors during monitoring process"""
        logging.error(f"Error in completion monitoring for {track_name}: {error}")
        
        if self.progress_tracker and track_index:
            self.progress_tracker.update_track_status(track_index, 'failed')
        
        self.stats_reporter.record_track_completion(song_name, track_name, success=False, 
                                                   error_message=f"Monitoring error: {str(error)}")
    
    def _find_new_completed_files(self, song_path, track_name, initial_files):
        """Find completed files that need processing (both new and existing unprocessed files) - optimized"""
        try:
            # Use file manager's optimized file info method
            song_info = self.file_manager._get_file_info(song_path)
            if not song_info['exists']:
                return []
            
            completed_files = []
            
            # Use optimized directory scan from file manager
            current_files_info = self.file_manager._scan_directory_cached(song_path)
            
            for file_info in current_files_info:
                if not file_info['is_file']:
                    continue
                    
                filename = file_info['name']
                filename_lower = file_info['name_lower']
                
                # Check if it's an audio file (not .crdownload) using file manager's method
                is_audio = self.file_manager._is_audio_file(filename_lower)
                is_recent = file_info['age'] < 300  # Less than 5 minutes old
                is_new = filename not in initial_files  # Wasn't there when we started monitoring
                
                # Check if existing file needs processing (has custom backing track suffix)
                needs_processing = 'Custom_Backing_Track' in filename or 'custom_backing_track' in filename
                is_existing_unprocessed = filename in initial_files and needs_processing
                
                # Process files that are either:
                # 1. New (normal case for visible mode)
                # 2. Existing but unprocessed (headless mode case)
                should_process = is_audio and is_recent and (is_new or is_existing_unprocessed)
                
                if should_process:
                    file_path = file_info['path']
                    # Make sure there's no corresponding .crdownload file (use cached check)
                    crdownload_path = file_path.with_suffix(file_path.suffix + '.crdownload')
                    crdownload_info = self.file_manager._get_file_info(crdownload_path)
                    if not crdownload_info['exists']:
                        completed_files.append(file_path)
                        if is_new:
                            logging.info(f"✅ Found NEW completed download: {filename}")
                        else:
                            logging.info(f"✅ Found EXISTING unprocessed download: {filename}")
            
            return completed_files
            
        except Exception as e:
            logging.debug(f"Error finding completed files: {e}")
            return []
    
    def _does_file_match_track(self, filename, track_name):
        """Check if a downloaded filename matches the track we're monitoring"""
        try:
            filename_lower = filename.lower()
            track_lower = track_name.lower()
            
            # Clean both names for comparison, normalize whitespace
            clean_filename = filename_lower.replace('_', ' ').replace('-', ' ')
            clean_track = ' '.join(track_lower.split())  # Normalize multiple spaces to single spaces
            
            # Handle special cases first
            # For "Click" tracks (including "Intro count Click"), match if both contain "click"
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
            # Note: 'intro' and 'count' are NOT in skip words for Click tracks
            skip_words = {'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for'}
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
                is_match = match_ratio >= TRACK_MATCH_MIN_RATIO
            
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
                            WebDriverWait(self.driver, WEBDRIVER_SHORT_TIMEOUT).until(
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
    
    def _verify_track_selection_with_retry(self, track_name, track_index, max_retries=3):
        """Verify track selection state with retry logic
        
        Args:
            track_name (str): Name of the track that should be isolated
            track_index (str/int): Data-index of the track that should be active
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            bool: True if verification passes, False otherwise
        """
        for attempt in range(max_retries):
            logging.info(f"🔄 Verification attempt {attempt + 1}/{max_retries} for {track_name}")
            
            verification_passed = self._verify_track_selection_state(track_name, track_index)
            
            if verification_passed:
                logging.info(f"✅ Verification passed on attempt {attempt + 1}")
                return True
            
            if attempt < max_retries - 1:  # Don't wait after the last attempt
                logging.warning(f"⚠️ Verification failed, waiting 2s before retry {attempt + 2}...")
                time.sleep(RETRY_VERIFICATION_DELAY)
        
        logging.error(f"❌ All {max_retries} verification attempts failed for {track_name}")
        return False

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
                    
                    # Use the shared solo button detector (single source of truth)
                    is_solo_active = is_solo_button_active(solo_button)
                    
                    if is_solo_active:
                        verification_results['solo_button_active'] = True
                        logging.debug(f"✅ Solo button is active for track {track_index}")
                    else:
                        button_classes = solo_button.get_attribute('class') or ''
                        logging.warning(f"⚠️ Solo button not active for track {track_index} - classes: {button_classes}")
                    
                    # Check track name matches
                    try:
                        caption_element = track_element.find_element(By.CSS_SELECTOR, ".track__caption")
                        # ' '.join(...split()) collapses any whitespace (incl. embedded
                        # newlines + leading spaces — e.g. "Intro count\n      Click")
                        # to single spaces. Must match the same normalization
                        # discover_tracks applies, otherwise the track name passed
                        # in (already normalized) won't match the freshly-read DOM text.
                        actual_track_name = ' '.join(caption_element.text.split())

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
                        class_tokens = set((button.get_attribute('class') or '').lower().split())

                        if class_tokens & ACTIVE_SOLO_CLASS_TOKENS:
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
            
            # Require 100% pass rate for all verification checks
            verification_passed = verification_score >= 1.0
            
            if verification_passed:
                logging.info(f"✅ Track selection verification PASSED for {track_name}")
            else:
                logging.warning(f"⚠️ Track selection verification FAILED for {track_name}")
                logging.warning(f"   Failed checks: {[k for k, v in verification_results.items() if not v]}")
            
            return verification_passed
            
        except Exception as e:
            logging.error(f"❌ Error during track selection verification: {e}")
            return False  # Fail safely
