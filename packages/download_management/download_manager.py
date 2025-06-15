"""Download management for karaoke automation - orchestration, monitoring, and completion"""

import time
import logging
import threading
from selenium.webdriver.common.by import By


class DownloadManager:
    """Handles download orchestration, monitoring, and completion detection"""
    
    def __init__(self, driver, wait):
        """Initialize download manager with Selenium driver and wait objects"""
        self.driver = driver
        self.wait = wait
        self.progress_tracker = None
        self.file_manager = None
        self.chrome_manager = None
    
    def set_progress_tracker(self, progress_tracker):
        """Set the progress tracker for status updates"""
        self.progress_tracker = progress_tracker
    
    def set_file_manager(self, file_manager):
        """Set the file manager for download operations"""
        self.file_manager = file_manager
    
    def set_chrome_manager(self, chrome_manager):
        """Set the chrome manager for download path management"""
        self.chrome_manager = chrome_manager
    
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
            song_folder = self.extract_song_folder_name(song_url)
        
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
                self.start_completion_monitoring(song_path, track_name, track_index)
                
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
                except:
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