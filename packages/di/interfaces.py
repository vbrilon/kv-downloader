"""Interface definitions for dependency injection"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class IProgressTracker(ABC):
    """Interface for progress tracking functionality"""
    
    @abstractmethod
    def update_track_status(self, track_index: int, status: str, progress: Optional[float] = None) -> None:
        pass
    
    @abstractmethod
    def increment_completed_tracks(self) -> None:
        pass


class IFileManager(ABC):
    """Interface for file management operations"""
    
    @abstractmethod
    def setup_song_folder(self, song_folder_name: str, clear_existing: bool = True) -> str:
        pass
    
    @abstractmethod
    def cleanup_partial_downloads(self, song_folder: str) -> None:
        pass
    
    @abstractmethod
    def verify_download_completion(self, expected_filename: str, song_folder: str) -> bool:
        pass


class IChromeManager(ABC):
    """Interface for Chrome browser management"""
    
    @abstractmethod
    def setup_driver(self) -> Any:
        pass
    
    @abstractmethod
    def set_download_path(self, path: str) -> None:
        pass
    
    @abstractmethod
    def quit_driver(self) -> None:
        pass


class IStatsReporter(ABC):
    """Interface for statistics reporting"""
    
    @abstractmethod
    def record_track_completion(self, song_name: str, track_name: str, success: bool, **kwargs) -> None:
        pass
    
    @abstractmethod
    def get_session_stats(self) -> Dict[str, Any]:
        pass


class IConfig(ABC):
    """Interface for configuration management"""
    
    @abstractmethod
    def get_download_folder(self) -> str:
        pass
    
    @abstractmethod
    def get_username(self) -> Optional[str]:
        pass
    
    @abstractmethod
    def get_password(self) -> Optional[str]:
        pass
    
    @abstractmethod
    def get_solo_activation_delay(self) -> float:
        pass