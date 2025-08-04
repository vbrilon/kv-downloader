"""Configuration implementation for dependency injection"""

from typing import Optional
from .interfaces import IConfig


class Config(IConfig):
    """Configuration implementation that can be injected"""
    
    def __init__(self, 
                 download_folder: str = "./downloads",
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 solo_activation_delay: float = 2.0):
        self._download_folder = download_folder
        self._username = username
        self._password = password
        self._solo_activation_delay = solo_activation_delay
    
    def get_download_folder(self) -> str:
        return self._download_folder
    
    def get_username(self) -> Optional[str]:
        return self._username
    
    def get_password(self) -> Optional[str]:
        return self._password
    
    def get_solo_activation_delay(self) -> float:
        return self._solo_activation_delay
    
    @classmethod
    def from_existing_config(cls) -> 'Config':
        """Create config from existing configuration module"""
        try:
            from packages.configuration import DOWNLOAD_FOLDER, USERNAME, PASSWORD, SOLO_ACTIVATION_DELAY
            return cls(
                download_folder=DOWNLOAD_FOLDER,
                username=USERNAME,
                password=PASSWORD,
                solo_activation_delay=SOLO_ACTIVATION_DELAY
            )
        except ImportError:
            # Fallback values if configuration module is not available
            return cls()