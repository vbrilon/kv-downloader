#!/usr/bin/env python3
"""
Modular Karaoke-Version.com Automation Library
Centralizes all automation logic into reusable components
"""

import time
import os
import logging
import signal
import sys
import glob
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# CRITICAL: Initialize profiler BEFORE importing instrumented modules
# This ensures decorators capture the correct profiler state
from packages.utils import setup_logging, initialize_profiler, get_profiler, profile_timing

# Setup logging (will be reconfigured based on debug mode)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)



class KaraokeVersionAutomator:
    """Main automation class that coordinates all functionality"""
    
    def __init__(self, headless=False, show_progress=True, config_file="songs.yaml", max_tracks_per_song=None):
        """
        Initialize automator
        
        Args:
            headless (bool): Run browser in headless mode (True) or visible mode (False)
            show_progress (bool): Show progress bar during downloads (True) or use simple logging (False)
            config_file (str): Path to songs configuration file
            max_tracks_per_song (int): Maximum tracks to process per song (None = all tracks)
        """
        self.headless = headless
        self.show_progress = show_progress
        self.max_tracks_per_song = max_tracks_per_song
        self.config_manager = ConfigurationManager(config_file)
        self.progress = ProgressTracker(show_display=show_progress) if show_progress else None
        self.stats = StatsReporter()  # Always track stats
        self.failed_downloads = []  # Track failures for retry

        # Get the global profiler (will be enabled if --profile flag was used)
        self.profiler = get_profiler()
        
        # Initialize browser manager
        self.chrome_manager = ChromeManager(headless=headless)
        self.chrome_manager.setup_driver()
        self.chrome_manager.setup_folders()
        
        # Get driver and wait from chrome manager
        self.driver = self.chrome_manager.driver
        self.wait = self.chrome_manager.wait
        
        # Initialize managers
        self.login_handler = LoginManager(self.driver, self.wait)
        self.file_manager = FileManager()
        self.track_manager = TrackManager(self.driver, self.wait)
        
        # Set up dependency injection container
        self.di_container = create_container_with_dependencies(
            chrome_manager=self.chrome_manager,
            file_manager=self.file_manager,
            progress_tracker=self.progress,
            stats_reporter=self.stats
        )
        
        # Create download manager using dependency injection
        download_manager_factory = create_download_manager_factory(self.di_container)
        self.download_manager = download_manager_factory(self.driver, self.wait)
        
        # Connect track manager with progress tracker (still using setter for now)
        if self.progress:
            self.track_manager.set_progress_tracker(self.progress)
    
    
    @profile_timing("login", "system", "method")
    def login(self, force_relogin=False):
        """Login using centralized login handler with session persistence"""
        return self.login_handler.login_with_session_persistence(force_relogin=force_relogin)
    
    def is_logged_in(self):
        """Check login status using centralized handler"""
        return self.login_handler.is_logged_in()
    
    @profile_timing("get_available_tracks", "system", "method")
    def get_available_tracks(self, song_url):
        """Get tracks using centralized track handler"""
        return self.track_manager.discover_tracks(song_url)
    
    def solo_track(self, track_info, song_url):
        """Solo a specific track using centralized track handler"""
        return self.track_manager.solo_track(track_info, song_url)
    
    def clear_all_solos(self, song_url):
        """Clear all solo buttons using centralized track handler"""
        return self.track_manager.clear_all_solos(song_url)
    
    def ensure_only_track_active(self, target_index, song_url):
        """Smart solo management - only deactivate conflicting tracks"""
        return self.track_manager.ensure_only_track_active(target_index, song_url)
    
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
    
    @profile_timing("run_automation", "system", "system")
    def run_automation(self):
        """Run complete automation workflow"""
        try:
            if not self._setup_automation_session():
                return False
            
            songs = self.load_songs_config()
            if not songs:
                logging.error("No songs configured")
                return False
            
            logging.info(f"Processing {len(songs)} songs...")
            
            for song in songs:
                self._process_single_song(song)
            
            logging.info("Automation completed")
            
            # Run final cleanup pass to catch any files that weren't cleaned up
            try:
                logging.info("🧹 Running final cleanup pass...")
                self.file_manager.final_cleanup_pass()
            except Exception as e:
                logging.error(f"Error during final cleanup pass: {e}")
            
            self._generate_final_reports()
            return True
            
        except Exception as e:
            logging.error(f"Automation failed: {e}")
            self._generate_final_reports(failed=True)
            return False
        finally:
            # Cleanup is handled by chrome_manager.quit() in main finally block
            pass
    
    def _setup_automation_session(self):
        """Setup login and verify session is ready"""
        if not self.login():
            logging.error("Login failed - cannot proceed")
            return False
        return True
    
    @profile_timing("_process_single_song", "system", "component")
    def _process_single_song(self, song):
        """Process a single song with all its tracks"""
        logging.info(f"Processing: {song['name']}")
        song_key = song.get('key', 0)
        
        self._log_song_configuration(song_key)
        
        if not self._verify_login_session():
            return False
        
        tracks = self.get_available_tracks(song['url'])
        if tracks:
            self._process_song_with_tracks(song, tracks, song_key)
        else:
            self._handle_no_tracks_found(song)
    
    def _log_song_configuration(self, song_key):
        """Log the current song configuration"""
        if song_key != 0:
            logging.info(f"🎵 Song configuration - Key: {song_key:+d} semitones")
        else:
            logging.info(f"🎵 Song configuration - Key: no adjustment")
    
    def _verify_login_session(self):
        """Verify login session is still valid"""
        if not self.is_logged_in():
            logging.error("Login session expired")
            if not self.login():
                logging.error("Re-login failed")
                return False
        return True
    
    def _process_song_with_tracks(self, song, tracks, song_key):
        """Process a song that has available tracks"""
        logging.info(f"Found {len(tracks)} tracks for {song['name']}")
        
        self._start_song_tracking(song, tracks)
        self._setup_mixer_controls(song, song_key)
        self._prepare_song_folder(song)
        self._download_all_tracks(song, tracks, song_key)
        self._finish_song_processing(song)
    
    def _start_song_tracking(self, song, tracks):
        """Initialize progress and statistics tracking for song"""
        if self.progress:
            self.progress.start_song(song['name'], tracks)
        self.stats.start_song(song['name'], song['url'], len(tracks))
    
    def _setup_mixer_controls(self, song, song_key):
        """Configure mixer controls for the song"""
        logging.info("🎛️ Setting up mixer controls...")
        
        intro_success = self.track_manager.ensure_intro_count_enabled(song['url'])
        if not intro_success:
            logging.warning("⚠️ Could not enable intro count - continuing anyway")
        
        if song_key != 0:
            key_success = self.track_manager.adjust_key(song['url'], song_key)
            if not key_success:
                logging.warning(f"⚠️ Could not adjust key to {song_key:+d} - continuing with default key")
    
    def _prepare_song_folder(self, song):
        """Clear and prepare the song folder for downloads"""
        song_folder_name = song.get('name') or self.download_manager.extract_song_folder_name(song['url'])
        self.file_manager.clear_song_folder(song_folder_name)
    
    def _download_all_tracks(self, song, tracks, song_key):
        """Download all tracks for the song (or limited by max_tracks_per_song)"""
        # Limit tracks if max_tracks_per_song is specified
        if self.max_tracks_per_song is not None:
            limited_tracks = tracks[:self.max_tracks_per_song]
            if len(limited_tracks) < len(tracks):
                logging.info(f"📊 Limiting to {self.max_tracks_per_song} tracks (of {len(tracks)} available) for faster profiling")
            tracks_to_process = limited_tracks
        else:
            tracks_to_process = tracks
            
        for track in tracks_to_process:
            self._download_single_track(song, track, song_key)
            time.sleep(BETWEEN_TRACKS_PAUSE)  # Brief pause between tracks
    
    @profile_timing("_download_single_track", "system", "method")
    def _download_single_track(self, song, track, song_key):
        """Download a single track"""
        track_name = self.sanitize_filename(track['name'])
        success = False  # Initialize success variable to prevent scope issues
        
        if self.progress:
            self.progress.update_track_status(track['index'], 'isolating')
        
        self.stats.record_track_start(song['name'], track_name, track['index'])
        
        # Smart solo management - only clear conflicting tracks (performance optimized)
        logging.debug(f"Ensuring clean solo state for {track_name} (track {track['index']})")
        self.ensure_only_track_active(track['index'], song['url'])
        
        if self.solo_track(track, song['url']):
            try:
                success = self.download_manager.download_current_mix(
                    song['url'], 
                    track_name,
                    cleanup_existing=False,
                    song_folder=song.get('name'),
                    key_adjustment=song_key,
                    track_index=track['index']
                )
            except Exception as e:
                logging.error(f"Exception during download for {track_name}: {e}")
                success = False
            
            if not success:
                logging.error(f"Failed to download {track_name}")
        else:
            logging.error(f"Failed to solo track {track_name}")
            if self.progress:
                self.progress.update_track_status(track['index'], 'failed')
            self.stats.record_track_completion(song['name'], track_name, success=False, 
                                             error_message="Failed to solo track")
    
    def _finish_song_processing(self, song):
        """Complete song processing and cleanup"""
        self.clear_all_solos(song['url'])
        
        if self.progress:
            self.progress.finish_song()
        
        self.stats.finish_song(song['name'])
    
    def _handle_no_tracks_found(self, song):
        """Handle case where no tracks are found for a song"""
        logging.error(f"No tracks found for {song['name']}")
        self.stats.start_song(song['name'], song['url'], 0)
        self.stats.finish_song(song['name'])
    
    def _generate_final_reports(self, failed=False):
        """Generate and display final statistics reports"""
        try:
            if self.show_progress:
                print("\n" + "="*80)
                if failed:
                    print("📊 GENERATING FINAL STATISTICS REPORT (AUTOMATION FAILED)")
                else:
                    print("📊 GENERATING FINAL STATISTICS REPORT...")
                print("="*80)
                
                final_report = self.stats.generate_final_report()
                print(final_report)
                
                # Generate performance report if profiling was enabled
                if self.profiler.enabled:
                    print("\n" + "="*80)
                    print("🔍 GENERATING PERFORMANCE PROFILING REPORT...")
                    print("="*80)
                    perf_report = self.profiler.generate_performance_report()
                    print(perf_report)
                
            else:
                # Use logging for non-display mode
                if failed:
                    logging.info("Generating final statistics report (automation failed)")
                else:
                    logging.info("Generating final statistics report")
                
                final_report = self.stats.generate_final_report()
                logging.info(f"Final report:\n{final_report}")
                
                # Generate performance report if profiling was enabled
                if self.profiler.enabled:
                    logging.info("Generating performance profiling report...")
                    perf_report = self.profiler.generate_performance_report()
                    logging.info(f"Performance report:\n{perf_report}")
            
            filename = "logs/automation_stats_failed.json" if failed else "logs/automation_stats.json"
            stats_saved = self.stats.save_detailed_report(filename)
            
            if stats_saved and not failed:
                if self.show_progress:
                    print(f"\n📁 Detailed statistics saved to: {filename}")
                else:
                    logging.info(f"Detailed statistics saved to: {filename}")
            
            # Save detailed performance report if profiling was enabled
            if self.profiler.enabled:
                perf_filename = self.profiler.save_detailed_report()
                if perf_filename:
                    if self.show_progress:
                        print(f"📁 Detailed performance report saved to: {perf_filename}")
                    else:
                        logging.info(f"Detailed performance report saved to: {perf_filename}")
            
        except Exception as e:
            logging.error(f"Error generating final statistics report: {e}")


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Karaoke-Version.com Track Automation')
    parser.add_argument('--debug', action='store_true', 
                       help='Run in debug mode with visible browser and detailed file logging')
    parser.add_argument('--force-login', action='store_true',
                       help='Force fresh login instead of using saved session')
    parser.add_argument('--clear-session', action='store_true',
                       help='Clear saved session data and exit')
    parser.add_argument('--profile', action='store_true',
                       help='Enable performance profiling with detailed timing logs')
    parser.add_argument('--baseline-test', type=str, choices=['current', 'pre_optimization', 'solo_only', 'download_only'],
                       help='Run baseline performance test with specified configuration')
    parser.add_argument('--ab-test', nargs=2, metavar=('BASELINE_A', 'BASELINE_B'),
                       help='Run A/B comparison between two baselines (e.g., --ab-test pre_optimization current)')
    parser.add_argument('--list-baselines', action='store_true',
                       help='List available baseline configurations and exit')
    parser.add_argument('--max-tracks', type=int, default=None,
                       help='Maximum tracks per song to process (default: all tracks)')
    args = parser.parse_args()
    
    # CRITICAL: Initialize profiler immediately after argument parsing
    # This must happen BEFORE importing any instrumented modules
    if args.profile:
        initialize_profiler(enabled=True, enable_memory=True, enable_detailed_logging=True)
        print("🔍 Performance profiling enabled")
    
    # Now import instrumented modules AFTER profiler initialization
    from packages.configuration import ConfigurationManager
    from packages.configuration.config import BETWEEN_TRACKS_PAUSE
    from packages.browser import ChromeManager
    from packages.authentication import LoginManager
    from packages.progress import ProgressTracker, StatsReporter
    from packages.file_operations import FileManager
    from packages.track_management import TrackManager
    from packages.download_management import DownloadManager
    from packages.di.factory import create_container_with_dependencies, create_download_manager_factory
    
    # Handle baseline testing commands
    if args.list_baselines:
        from packages.utils import list_baselines
        list_baselines()
        exit(0)
        
    if args.ab_test:
        from packages.utils import run_ab_test
        baseline_a, baseline_b = args.ab_test
        print(f"🔬 Running A/B test: {baseline_a} vs {baseline_b}")
        result = run_ab_test(baseline_a, baseline_b, max_tracks=args.max_tracks or 3)
        print(result)
        exit(0)
        
    if args.baseline_test:
        from packages.utils import PerformanceBaselineTester
        tester = PerformanceBaselineTester()
        print(f"🧪 Running baseline test: {args.baseline_test}")
        result = tester.run_baseline_test(args.baseline_test, max_tracks_per_song=args.max_tracks or 3)
        if result:
            print(f"\n✅ Baseline test completed in {result['test_duration']:.2f}s")
            print(f"📁 Results saved to logs/performance/baselines/")
        else:
            print("❌ Baseline test failed - check logs for details")
        exit(0)
    
    # Handle session clearing
    if args.clear_session:
        from packages.authentication import LoginManager
        # Create a temporary login manager just to clear session
        temp_login = LoginManager(None, None)
        if temp_login.clear_session():
            print("✅ Saved session data cleared successfully")
        else:
            print("❌ Could not clear session data")
        exit(0)
    
    # Setup logging based on debug mode
    setup_logging(args.debug)
    
    # Set browser mode
    headless_mode = not args.debug
    
    # Initialize automator with appropriate mode
    automator = None
    
    # Setup signal handler for graceful shutdown
    def signal_handler(signum, frame):
        logging.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        if automator:
            try:
                # Only use chrome_manager.quit() to avoid duplicate cleanup
                if hasattr(automator, 'chrome_manager') and automator.chrome_manager:
                    logging.info("🧹 Shutting down Chrome manager...")
                    automator.chrome_manager.quit()
                elif hasattr(automator, 'driver') and automator.driver:
                    logging.info("🧹 Shutting down browser driver...")
                    try:
                        automator.driver.quit()
                    except Exception as e:
                        if "connection refused" not in str(e).lower():
                            logging.debug(f"Signal cleanup error: {e}")
            except Exception as e:
                logging.error(f"⚠️ Error during signal cleanup: {e}")
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        automator = KaraokeVersionAutomator(
            headless=headless_mode, 
            show_progress=True,
            max_tracks_per_song=args.max_tracks
        )
        
        # Override login method if force login requested
        if args.force_login:
            logging.info("🔄 Force login requested via command line")
            original_run = automator.run_automation
            def run_with_force_login():
                # Step 1: Login (force relogin)
                if not automator.login(force_relogin=True):
                    logging.error("Login failed")
                    return False
                return original_run()
            automator.run_automation = run_with_force_login
        
        # Run the automation
        automator.run_automation()
        
    except KeyboardInterrupt:
        logging.info("🛑 Automation interrupted by user")
    except Exception as e:
        logging.error(f"💥 Fatal error during automation: {e}")
        sys.exit(1)
    finally:
        # Comprehensive cleanup - ensure browser resources are properly closed
        if automator:
            try:
                # Only use chrome_manager.quit() to avoid duplicate cleanup
                if hasattr(automator, 'chrome_manager') and automator.chrome_manager:
                    logging.info("🧹 Cleaning up Chrome manager...")
                    automator.chrome_manager.quit()
                elif hasattr(automator, 'driver') and automator.driver:
                    # Fallback if chrome_manager is not available
                    logging.info("🧹 Cleaning up browser driver...")
                    try:
                        automator.driver.quit()
                    except Exception as e:
                        if "connection refused" not in str(e).lower():
                            logging.debug(f"Driver cleanup error: {e}")
                
                # Clean up any temporary files in download directory
                if hasattr(automator, 'file_manager') and automator.file_manager:
                    try:
                        logging.info("🧹 Cleaning up temporary download files...")
                        # Clean up .crdownload files that may be left behind
                        from packages.configuration import DOWNLOAD_FOLDER
                        temp_files = glob.glob(os.path.join(DOWNLOAD_FOLDER, "*.crdownload"))
                        for temp_file in temp_files:
                            try:
                                os.remove(temp_file)
                                logging.debug(f"Removed temporary file: {temp_file}")
                            except Exception:
                                pass  # Don't log failed temp file cleanup
                    except Exception:
                        pass  # Don't fail cleanup for temporary file issues
                    
                logging.info("✅ Resource cleanup completed successfully")
                
            except Exception as cleanup_error:
                logging.error(f"⚠️ Error during resource cleanup: {cleanup_error}")
                # Don't raise - we don't want cleanup errors to mask the original error