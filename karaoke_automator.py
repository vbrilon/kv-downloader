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
from packages.track_management import TrackManager
from packages.download_management import DownloadManager
from packages.utils import setup_logging

# Setup logging (will be reconfigured based on debug mode)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)



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
        
        # Initialize all managers directly
        self.login_handler = LoginManager(self.driver, self.wait)
        self.file_manager = FileManager()
        self.track_manager = TrackManager(self.driver, self.wait)
        self.download_manager = DownloadManager(self.driver, self.wait)
        
        # Connect managers
        if self.progress:
            self.track_manager.set_progress_tracker(self.progress)
            self.download_manager.set_progress_tracker(self.progress)
        self.download_manager.set_file_manager(self.file_manager)
        self.download_manager.set_chrome_manager(self.chrome_manager)
    
    
    def login(self):
        """Login using centralized login handler"""
        return self.login_handler.login()
    
    def is_logged_in(self):
        """Check login status using centralized handler"""
        return self.login_handler.is_logged_in()
    
    def get_available_tracks(self, song_url):
        """Get tracks using centralized track handler"""
        return self.track_manager.discover_tracks(song_url)
    
    def solo_track(self, track_info, song_url):
        """Solo a specific track using centralized track handler"""
        return self.track_manager.solo_track(track_info, song_url)
    
    def clear_all_solos(self, song_url):
        """Clear all solo buttons using centralized track handler"""
        return self.track_manager.clear_all_solos(song_url)
    
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
        return self.download_manager.sanitize_filesystem_name(filename)
    
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
                    intro_success = self.track_manager.ensure_intro_count_enabled(song['url'])
                    if not intro_success:
                        logging.warning("⚠️ Could not enable intro count - continuing anyway")
                    
                    # Adjust key if needed
                    if song_key != 0:
                        key_success = self.track_manager.adjust_key(song['url'], song_key)
                        if not key_success:
                            logging.warning(f"⚠️ Could not adjust key to {song_key:+d} - continuing with default key")
                    
                    # Clear song folder once at the beginning of the song (not for each track)
                    song_folder_name = song.get('name') or self.download_manager.extract_song_folder_name(song['url'])
                    self.file_manager.clear_song_folder(song_folder_name)
                    
                    # Download each track individually
                    for track in tracks:
                        track_name = self.sanitize_filename(track['name'])
                        
                        # Solo this track
                        if self.solo_track(track, song['url']):
                            # Download the soloed track (folder already cleared once per song)
                            success = self.download_manager.download_current_mix(
                                song['url'], 
                                track_name,
                                cleanup_existing=False,  # Don't clear folder for each track
                                song_folder=song.get('name'),  # None if not specified, triggers URL extraction
                                key_adjustment=song_key,
                                track_index=track['index']  # Pass track index for accurate progress tracking
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