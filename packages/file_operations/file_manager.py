"""File management for karaoke automation - folders, downloads, cleanup"""

import time
import logging
import shutil
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
    
    def clear_song_folder(self, song_folder_name):
        """Completely remove existing song folder and all its contents"""
        try:
            base_download_folder = Path(DOWNLOAD_FOLDER)
            song_path = base_download_folder / song_folder_name
            
            if song_path.exists() and song_path.is_dir():
                # Safety check: ensure we're only deleting song folders, not random directories
                if song_path.parent == base_download_folder:
                    logging.info(f"🗑️ Clearing existing song folder: {song_path}")
                    
                    # Count files before deletion for logging
                    file_count = len([f for f in song_path.rglob("*") if f.is_file()])
                    if file_count > 0:
                        logging.info(f"   Removing {file_count} existing files")
                    
                    # Remove the entire folder and its contents
                    shutil.rmtree(song_path)
                    logging.info(f"✅ Song folder cleared successfully")
                else:
                    logging.warning(f"⚠️ Safety check failed: {song_path} is not a direct child of downloads folder")
            else:
                logging.debug(f"No existing song folder to clear: {song_path}")
                
        except Exception as e:
            logging.warning(f"⚠️ Could not clear song folder {song_folder_name}: {e}")
            logging.info("Continuing with download - new files will be added to existing folder")

    def setup_song_folder(self, song_folder_name, clear_existing=True):
        """Create song-specific folder in downloads directory
        
        Args:
            song_folder_name (str): Name of the song folder to create
            clear_existing (bool): Whether to clear existing folder contents first (default: True)
        """
        try:
            base_download_folder = Path(DOWNLOAD_FOLDER)
            song_path = base_download_folder / song_folder_name
            
            # Clear existing folder if requested (default behavior)
            if clear_existing:
                self.clear_song_folder(song_folder_name)
            
            # Create the folder (will recreate if it was cleared)
            song_path.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"📁 Song folder ready: {song_path}")
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
        """Wait for download to actually start by monitoring song folder for new files AND file modifications"""
        try:
            if not song_path or not song_path.exists():
                logging.error(f"Song folder not available for monitoring: {song_path}")
                return False
            
            paths_to_monitor = [song_path]
            logging.info(f"🔍 Monitoring song folder: {song_path}")
            
            # Get initial file snapshots with names, sizes, and modification times
            initial_file_snapshots = {}
            
            for path in paths_to_monitor:
                path_snapshots = {}
                if path.exists():
                    initial_files = list(path.glob("*.mp3")) + list(path.glob("*.aif")) + list(path.glob("*.crdownload"))
                    for file_path in initial_files:
                        try:
                            stat = file_path.stat()
                            path_snapshots[file_path.name] = {
                                'size': stat.st_size,
                                'mtime': stat.st_mtime,
                                'path': file_path
                            }
                        except (OSError, FileNotFoundError):
                            # File might have been deleted/moved during enumeration
                            continue
                    
                    logging.debug(f"Initial files in {path}: {len(path_snapshots)} (names: {list(path_snapshots.keys())})")
                
                initial_file_snapshots[path] = path_snapshots
            
            max_wait = 30  # Reduced from 90s since we now detect overwrites quickly
            waited = 0
            check_interval = 1  # Check every 1 second for faster detection
            
            logging.info(f"⏳ Waiting for download to start for: {track_name}")
            
            while waited < max_wait:
                time.sleep(check_interval)
                waited += check_interval
                
                # Check all monitored paths for new files AND modified files
                for path in paths_to_monitor:
                    if not path.exists():
                        continue
                    
                    current_files = list(path.glob("*.mp3")) + list(path.glob("*.aif")) + list(path.glob("*.crdownload"))
                    initial_snapshots = initial_file_snapshots[path]
                    
                    new_or_modified_files = []
                    
                    for file_path in current_files:
                        try:
                            filename = file_path.name
                            stat = file_path.stat()
                            current_size = stat.st_size
                            current_mtime = stat.st_mtime
                            
                            # Check if this is a new file
                            if filename not in initial_snapshots:
                                new_or_modified_files.append(('new', filename, file_path))
                                logging.debug(f"New file detected: {filename}")
                            else:
                                # Check if existing file was modified
                                initial_snapshot = initial_snapshots[filename]
                                
                                # Consider file modified if size changed OR modification time is newer
                                size_changed = current_size != initial_snapshot['size']
                                time_changed = current_mtime > initial_snapshot['mtime']
                                
                                if size_changed or time_changed:
                                    new_or_modified_files.append(('modified', filename, file_path))
                                    logging.debug(f"Modified file detected: {filename} (size: {initial_snapshot['size']} → {current_size}, mtime: {initial_snapshot['mtime']:.1f} → {current_mtime:.1f})")
                        
                        except (OSError, FileNotFoundError):
                            # File might have been deleted/moved during check
                            continue
                    
                    if new_or_modified_files:
                        # Filter to those that look like karaoke downloads
                        relevant_files = []
                        for change_type, filename, file_path in new_or_modified_files:
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
                                relevant_files.append((change_type, filename))
                        
                        if relevant_files:
                            file_descriptions = [f"{filename} ({change_type})" for change_type, filename in relevant_files]
                            logging.info(f"✅ Download started! Files detected: {file_descriptions}")
                            logging.info(f"📁 Location: {path}")
                            return True
                        else:
                            logging.debug(f"Files changed but don't appear to be karaoke downloads: {[f[1] for f in new_or_modified_files]}")
                
                # Update progress every 5 seconds
                if waited % 5 == 0:
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
    
    def clean_downloaded_filename(self, file_path, track_name=None):
        """Remove '_Custom_Backing_Track' from downloaded filename and ensure single track identifier"""
        try:
            original_name = file_path.name
            new_name = original_name
            
            # Remove various forms of Custom_Backing_Track using regex for more robust matching
            import re
            
            # STEP 1: Remove all Custom_Backing_Track patterns
            # ORDER MATTERS: Most specific patterns first!
            patterns_to_remove = [
                r'\([^)]*_Custom_Backing_Track[^)]*\)',  # (Click_Custom_Backing_Track), (Drum_Kit_Custom_Backing_Track-1), etc.
                r'\(Custom_Backing_Track[^)]*\)',        # (Custom_Backing_Track), (Custom_Backing_Track-1), etc.
                r'_Custom_Backing_Track[^)]*\)',         # _Custom_Backing_Track), _Custom_Backing_Track-1)
                r'_Custom_Backing_Track',                # _Custom_Backing_Track
                r'Custom_Backing_Track',                 # Custom_Backing_Track
                r'\(Custom\)',                           # (Custom)
                r'_Custom'                               # _Custom
            ]
            
            # Apply all Custom_Backing_Track removal patterns
            for pattern in patterns_to_remove:
                if re.search(pattern, new_name):
                    new_name = re.sub(pattern, '', new_name)
                    logging.debug(f"Removed pattern '{pattern}' from filename")
            
            # STEP 2: Remove ALL existing track identifiers (parenthetical content)
            # This prevents accumulation of multiple track names like (Drum_Kit)(Bass)(Guitar)
            # Pattern explanation: \([^)]*\) matches any content within parentheses
            track_identifier_pattern = r'\([^)]*\)'
            
            # Find all existing track identifiers for logging
            existing_identifiers = re.findall(track_identifier_pattern, new_name)
            if existing_identifiers:
                logging.debug(f"Removing existing track identifiers: {existing_identifiers}")
                # Remove all parenthetical content (existing track identifiers)
                new_name = re.sub(track_identifier_pattern, '', new_name)
            
            # STEP 3: Create simplified filename with just track name (if provided)
            if track_name:
                # Clean track name for filename
                clean_track_name = track_name.replace('_', ' ').strip()
                
                # Get file extension from original file
                name_parts = new_name.rsplit('.', 1)
                if len(name_parts) == 2:
                    file_extension = name_parts[1]
                else:
                    file_extension = 'mp3'  # Default extension
                
                # Create simple filename with just track name
                new_name = f"{clean_track_name}.{file_extension}"
                
                logging.debug(f"Simplified filename to: {new_name}")
            
            # Clean up any double spaces or extra characters from the processing
            new_name = re.sub(r'\s+', ' ', new_name)  # Replace multiple spaces with single space
            new_name = new_name.replace(' .', '.')    # Fix spacing before file extension
            
            # Only rename if the name actually changed
            if new_name != original_name:
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
    
    def validate_audio_content(self, file_path, track_name, expected_properties=None):
        """Perform basic audio content validation to detect mismatched tracks
        
        Args:
            file_path (Path): Path to the downloaded audio file
            track_name (str): Expected track name for validation
            expected_properties (dict): Optional expected file properties
            
        Returns:
            dict: Validation results with status and details
        """
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'file_info': {}
        }
        
        try:
            if not file_path.exists():
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"File does not exist: {file_path}")
                return validation_result
            
            # Basic file validation
            file_size = file_path.stat().st_size
            file_ext = file_path.suffix.lower()
            
            validation_result['file_info'] = {
                'size_bytes': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'extension': file_ext,
                'name': file_path.name
            }
            
            # File size validation (typical karaoke tracks are 3-15 MB)
            if file_size < 1024 * 1024:  # Less than 1 MB
                validation_result['warnings'].append(
                    f"File size is unusually small ({validation_result['file_info']['size_mb']} MB) - "
                    "may be incomplete or corrupted"
                )
            elif file_size > 50 * 1024 * 1024:  # More than 50 MB
                validation_result['warnings'].append(
                    f"File size is unusually large ({validation_result['file_info']['size_mb']} MB) - "
                    "may contain full song or multiple tracks"
                )
            
            # File format validation
            valid_extensions = ['.mp3', '.aif', '.wav', '.m4a']
            if file_ext not in valid_extensions:
                validation_result['warnings'].append(
                    f"Unexpected file format: {file_ext}. Expected: {valid_extensions}"
                )
            
            # Check if file appears to be audio (basic magic number check for MP3)
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(4)
                    if file_ext == '.mp3':
                        # Check for MP3 magic numbers
                        if not (header.startswith(b'ID3') or header.startswith(b'\xff\xfb') or header.startswith(b'\xff\xf3')):
                            validation_result['warnings'].append(
                                "File may not be a valid MP3 audio file (unexpected header)"
                            )
            except Exception as e:
                validation_result['warnings'].append(f"Could not validate file header: {e}")
            
            # Track name correlation check
            filename_lower = file_path.name.lower()
            track_lower = track_name.lower()
            
            # Extract significant words from track name
            track_words = set(track_lower.replace('_', ' ').replace('-', ' ').split())
            skip_words = {'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'custom', 'backing', 'track'}
            significant_track_words = {word for word in track_words if word not in skip_words and len(word) > 2}
            
            if significant_track_words:
                # Check how many track words appear in filename
                matches = sum(1 for word in significant_track_words if word in filename_lower)
                match_ratio = matches / len(significant_track_words)
                
                if match_ratio < 0.3:  # Less than 30% of words match
                    validation_result['warnings'].append(
                        f"Filename may not match track name - only {matches}/{len(significant_track_words)} "
                        f"significant words found in filename"
                    )
                elif match_ratio >= 0.7:  # 70% or more words match
                    validation_result['file_info']['name_correlation'] = 'good'
                else:
                    validation_result['file_info']['name_correlation'] = 'partial'
            
            # Additional validation based on expected properties
            if expected_properties:
                if 'expected_size_range' in expected_properties:
                    min_size, max_size = expected_properties['expected_size_range']
                    if not (min_size <= file_size <= max_size):
                        validation_result['warnings'].append(
                            f"File size ({validation_result['file_info']['size_mb']} MB) outside expected range "
                            f"({min_size/(1024*1024):.1f}-{max_size/(1024*1024):.1f} MB)"
                        )
            
            # Log validation results
            if validation_result['errors']:
                logging.error(f"❌ Content validation failed for {track_name}: {validation_result['errors']}")
            elif validation_result['warnings']:
                logging.warning(f"⚠️ Content validation warnings for {track_name}: {validation_result['warnings']}")
            else:
                logging.info(f"✅ Content validation passed for {track_name} ({validation_result['file_info']['size_mb']} MB)")
            
            return validation_result
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
            logging.error(f"❌ Error during content validation for {track_name}: {e}")
            return validation_result