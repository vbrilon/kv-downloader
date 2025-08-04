"""Adapters to make existing classes compatible with dependency injection interfaces"""

from typing import Optional, Dict, Any
from .interfaces import IProgressTracker, IFileManager, IChromeManager, IStatsReporter


class ProgressTrackerAdapter(IProgressTracker):
    """Adapter for existing progress tracker implementations"""
    
    def __init__(self, progress_tracker):
        self._progress_tracker = progress_tracker
    
    def update_track_status(self, track_index: int, status: str, progress: Optional[float] = None) -> None:
        if self._progress_tracker:
            self._progress_tracker.update_track_status(track_index, status, progress)
    
    def increment_completed_tracks(self) -> None:
        if self._progress_tracker and hasattr(self._progress_tracker, 'increment_completed_tracks'):
            self._progress_tracker.increment_completed_tracks()


class FileManagerAdapter(IFileManager):
    """Adapter for existing file manager implementations"""
    
    def __init__(self, file_manager):
        self._file_manager = file_manager
    
    def setup_song_folder(self, song_folder_name: str, clear_existing: bool = True) -> str:
        return self._file_manager.setup_song_folder(song_folder_name, clear_existing)
    
    def cleanup_partial_downloads(self, song_folder: str) -> None:
        if hasattr(self._file_manager, 'cleanup_partial_downloads'):
            self._file_manager.cleanup_partial_downloads(song_folder)
    
    def verify_download_completion(self, expected_filename: str, song_folder: str) -> bool:
        if hasattr(self._file_manager, 'verify_download_completion'):
            return self._file_manager.verify_download_completion(expected_filename, song_folder)
        return True  # Fallback for compatibility
    
    def wait_for_download_to_start(self, track_name: str, song_path, track_index=None):
        """Wait for download to start - forward to wrapped file manager"""
        return self._file_manager.wait_for_download_to_start(track_name, song_path, track_index)
    
    def clean_downloaded_filename(self, file_path, track_name):
        """Clean downloaded filename - forward to wrapped file manager"""
        if hasattr(self._file_manager, 'clean_downloaded_filename'):
            return self._file_manager.clean_downloaded_filename(file_path, track_name)
    
    def validate_audio_content(self, file_path, track_name):
        """Validate audio content - forward to wrapped file manager"""
        if hasattr(self._file_manager, 'validate_audio_content'):
            return self._file_manager.validate_audio_content(file_path, track_name)
        return True  # Fallback for compatibility


class ChromeManagerAdapter(IChromeManager):
    """Adapter for existing Chrome manager implementations"""
    
    def __init__(self, chrome_manager):
        self._chrome_manager = chrome_manager
    
    def setup_driver(self) -> Any:
        return self._chrome_manager.setup_driver()
    
    def set_download_path(self, path: str) -> None:
        self._chrome_manager.set_download_path(path)
    
    def quit_driver(self) -> None:
        if hasattr(self._chrome_manager, 'quit_driver'):
            self._chrome_manager.quit_driver()
        elif hasattr(self._chrome_manager, 'cleanup'):
            self._chrome_manager.cleanup()


class StatsReporterAdapter(IStatsReporter):
    """Adapter for existing stats reporter implementations"""
    
    def __init__(self, stats_reporter):
        self._stats_reporter = stats_reporter
    
    def record_track_completion(self, song_name: str, track_name: str, success: bool, **kwargs) -> None:
        if self._stats_reporter:
            self._stats_reporter.record_track_completion(song_name, track_name, success, **kwargs)
    
    def get_session_stats(self) -> Dict[str, Any]:
        if self._stats_reporter and hasattr(self._stats_reporter, 'get_session_stats'):
            return self._stats_reporter.get_session_stats()
        return {}


class NullProgressTracker(IProgressTracker):
    """Null object implementation for when progress tracking is disabled"""
    
    def update_track_status(self, track_index: int, status: str, progress: Optional[float] = None) -> None:
        pass  # No-op
    
    def increment_completed_tracks(self) -> None:
        pass  # No-op


class NullStatsReporter(IStatsReporter):
    """Null object implementation for when stats reporting is disabled"""
    
    def record_track_completion(self, song_name: str, track_name: str, success: bool, **kwargs) -> None:
        pass  # No-op
    
    def get_session_stats(self) -> Dict[str, Any]:
        return {}