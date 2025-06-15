"""File management for karaoke automation - folders, downloads, cleanup"""

import time
import logging
from pathlib import Path

try:
    from packages.configuration import DOWNLOAD_FOLDER
except ImportError:
    # Fallback for when config is not available during testing
    DOWNLOAD_FOLDER = "./downloads"


class FileManager:
    """Handles file operations, folder management, and filename cleanup"""
    
    def __init__(self):
        """Initialize file manager"""
        pass
    
    def setup_song_folder(self, song_folder_name):
        """Create song-specific folder in downloads directory"""
        try:
            base_download_folder = Path(DOWNLOAD_FOLDER)
            song_path = base_download_folder / song_folder_name
            song_path.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"Song folder ready: {song_path}")
            return song_path
            
        except Exception as e:
            logging.error(f"Error creating song folder: {e}")
            # Fallback to base download folder
            return Path(DOWNLOAD_FOLDER)
    
    def cleanup_existing_downloads(self, track_name, download_folder=None):
        """Remove existing files that might conflict with new download"""
        try:
            if download_folder is None:
                download_folder = Path(DOWNLOAD_FOLDER)
            else:
                download_folder = Path(download_folder)
                
            if not download_folder.exists():
                return
            
            # Only clean up files that are likely duplicates of what we're about to download
            # Use correct file extensions (.aif is primary, .mp3 as backup)
            removed_files = []
            
            # Look for files that match the track name specifically
            for file_path in download_folder.iterdir():
                if file_path.is_file():
                    filename = file_path.name.lower()
                    track_lower = track_name.lower()
                    
                    # Check if it's an audio file that matches this track
                    is_audio = any(filename.endswith(ext) for ext in ['.aif', '.mp3', '.wav', '.m4a'])
                    matches_track = track_lower in filename or any(word in filename for word in track_lower.split('_'))
                    has_backing_track_suffix = 'custom_backing_track' in filename or 'backing_track' in filename
                    
                    if is_audio and (matches_track or has_backing_track_suffix):
                        # Only remove if it's older than 30 seconds (avoid removing active downloads)
                        file_age = time.time() - file_path.stat().st_mtime
                        if file_age > 30:  # Only remove files older than 30 seconds
                            try:
                                file_path.unlink()
                                removed_files.append(file_path.name)
                                logging.info(f"Removed existing file: {file_path.name}")
                            except Exception as e:
                                logging.warning(f"Could not remove {file_path.name}: {e}")
                        else:
                            logging.debug(f"Skipping recent file (may be downloading): {file_path.name}")
            
            if removed_files:
                logging.info(f"Cleaned up {len(removed_files)} existing files")
            else:
                logging.debug("No existing files to clean up")
                
        except Exception as e:
            logging.warning(f"Error during download cleanup: {e}")
    
    def wait_for_download_to_start(self, track_name, song_path, track_index=None):
        """Wait for download to actually start by monitoring song folder only"""
        try:
            if not song_path or not song_path.exists():
                logging.error(f"Song folder not available for monitoring: {song_path}")
                return False
            
            paths_to_monitor = [song_path]
            logging.info(f"🔍 Monitoring song folder: {song_path}")
            
            # Get initial file lists for all paths
            initial_files_by_path = {}
            initial_counts = {}
            
            for path in paths_to_monitor:
                if path.exists():
                    initial_files = list(path.glob("*.mp3")) + list(path.glob("*.aif")) + list(path.glob("*.crdownload"))
                    initial_files_by_path[path] = set(f.name for f in initial_files)
                    initial_counts[path] = len(initial_files)
                    logging.debug(f"Initial files in {path}: {initial_counts[path]}")
                else:
                    initial_files_by_path[path] = set()
                    initial_counts[path] = 0
            
            max_wait = 90  # Maximum wait time in seconds (increased for better detection)
            waited = 0
            check_interval = 2  # Check every 2 seconds
            
            logging.info(f"⏳ Waiting for download to start for: {track_name}")
            
            while waited < max_wait:
                time.sleep(check_interval)
                waited += check_interval
                
                # Check all monitored paths for new files
                for path in paths_to_monitor:
                    if not path.exists():
                        continue
                    
                    current_files = list(path.glob("*.mp3")) + list(path.glob("*.aif")) + list(path.glob("*.crdownload"))
                    current_file_names = set(f.name for f in current_files)
                    
                    # Look for new files
                    new_files = current_file_names - initial_files_by_path[path]
                    
                    if new_files:
                        # Filter new files to those that look like karaoke downloads
                        relevant_new_files = []
                        for filename in new_files:
                            filename_lower = filename.lower()
                            # Check if it looks like a karaoke download
                            is_audio_or_download = any(filename_lower.endswith(ext) for ext in ['.mp3', '.aif', '.crdownload'])
                            
                            # Improved karaoke detection - case insensitive and comprehensive patterns
                            might_be_karaoke = (
                                # Specific karaoke patterns (case-insensitive)
                                'custom_backing_track' in filename_lower or
                                'backing_track' in filename_lower or
                                'custom' in filename_lower or
                                'backing' in filename_lower or
                                'track' in filename_lower or
                                'karaoke' in filename_lower or
                                # Parenthetical patterns like (Custom_Backing_Track)
                                '(custom' in filename_lower or
                                # Long filenames are often karaoke tracks
                                len(filename) > 20 or
                                # Since we're monitoring song folder during download, trust any audio file
                                is_audio_or_download
                            )
                            
                            if is_audio_or_download and might_be_karaoke:
                                relevant_new_files.append(filename)
                        
                        if relevant_new_files:
                            logging.info(f"✅ Download started! New files detected: {relevant_new_files}")
                            logging.info(f"📁 Location: {path}")
                            return True
                        else:
                            logging.debug(f"New files found but don't appear to be karaoke downloads: {new_files}")
                
                # Update progress every 10 seconds
                if waited % 10 == 0:
                    logging.info(f"⏳ Still waiting for download to start... ({waited}s/{max_wait}s)")
            
            logging.warning(f"⚠️ Download detection timeout after {max_wait}s for {track_name}")
            logging.info("💡 Download may have started but wasn't detected - continuing with next track")
            return False
            
        except Exception as e:
            logging.error(f"Error monitoring for download start: {e}")
            return False
    
    def check_for_completed_downloads(self, song_path, track_name):
        """Check for files that have completed downloading (no more .crdownload)"""
        try:
            if not song_path.exists():
                return []
            
            completed_files = []
            
            # Look for audio files that don't have .crdownload extension
            for file_path in song_path.iterdir():
                if file_path.is_file():
                    filename = file_path.name.lower()
                    
                    # Check if it's an audio file (not .crdownload)
                    is_audio = any(filename.endswith(ext) for ext in ['.mp3', '.aif', '.wav', '.m4a'])
                    is_recent = (time.time() - file_path.stat().st_mtime) < 300  # Less than 5 minutes old (more generous)
                    
                    # Check if it looks like a karaoke file - improved detection
                    filename_lower = filename  # filename is already lowercased above
                    might_be_karaoke = (
                        # Specific karaoke patterns (case-insensitive)
                        'custom_backing_track' in filename_lower or
                        'backing_track' in filename_lower or
                        'custom' in filename_lower or
                        'backing' in filename_lower or
                        'track' in filename_lower or
                        'karaoke' in filename_lower or
                        # Parenthetical patterns like (Custom_Backing_Track)
                        '(custom' in filename_lower or
                        # Long filenames typically indicate karaoke tracks
                        len(file_path.name) > 25 or
                        # Since we're in song folder during download window, trust any recent audio file
                        True  # Accept any recent audio file in the song folder
                    )
                    
                    # Enhanced logging for filename detection (INFO level to show in production)
                    if is_audio and is_recent:
                        logging.info(f"📁 Checking file: {file_path.name}")
                        logging.info(f"   Audio: {is_audio}, Recent: {is_recent}, Karaoke-like: {might_be_karaoke}")
                        if might_be_karaoke:
                            # Check which patterns matched
                            patterns_found = []
                            if 'custom_backing_track' in filename_lower: patterns_found.append('custom_backing_track')
                            if 'backing_track' in filename_lower: patterns_found.append('backing_track')
                            if 'custom' in filename_lower: patterns_found.append('custom')
                            if 'backing' in filename_lower: patterns_found.append('backing')
                            if 'track' in filename_lower: patterns_found.append('track')
                            if 'karaoke' in filename_lower: patterns_found.append('karaoke')
                            if '(custom' in filename_lower: patterns_found.append('parenthetical_custom')
                            if len(file_path.name) > 25: patterns_found.append('long_filename')
                            if not patterns_found: patterns_found.append('recent_audio_in_song_folder')
                            logging.info(f"   Patterns found: {patterns_found}")
                    
                    if is_audio and is_recent and might_be_karaoke:
                        # Make sure there's no corresponding .crdownload file
                        crdownload_path = file_path.with_suffix(file_path.suffix + '.crdownload')
                        if not crdownload_path.exists():
                            completed_files.append(file_path)
                            logging.info(f"✅ Found completed download: {file_path.name}")
            
            return completed_files
            
        except Exception as e:
            logging.debug(f"Error checking for completed downloads: {e}")
            return []
    
    def clean_downloaded_filename(self, file_path):
        """Remove '_Custom_Backing_Track' from downloaded filename"""
        try:
            original_name = file_path.name
            
            # Simple replacement: remove '_Custom_Backing_Track'
            if '_Custom_Backing_Track' in original_name:
                new_name = original_name.replace('_Custom_Backing_Track', '')
                new_path = file_path.parent / new_name
                
                # Avoid overwriting existing files
                if new_path.exists():
                    logging.warning(f"Target filename already exists, skipping cleanup: {new_name}")
                    return file_path
                
                # Rename the file
                file_path.rename(new_path)
                logging.info(f"📝 Cleaned filename: '{original_name}' → '{new_name}'")
                return new_path
            else:
                logging.debug(f"No cleanup needed for: {original_name}")
                return file_path
                
        except Exception as e:
            logging.warning(f"Could not clean filename for {file_path.name}: {e}")
            return file_path