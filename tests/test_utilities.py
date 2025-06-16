"""
Test utilities and helper functions for Karaoke Automation tests

This module provides common utilities, fixtures, and helper functions
used across multiple test files to reduce duplication and ensure consistency.
"""

import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from typing import Dict, Any, List


class TestHelpers:
    """Common test helper functions"""
    
    @staticmethod
    def create_temp_file(content: str = "", suffix: str = ".tmp") -> str:
        """Create a temporary file with optional content"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name
    
    @staticmethod
    def create_temp_dir() -> str:
        """Create a temporary directory"""
        return tempfile.mkdtemp()
    
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """Clean up a temporary file"""
        try:
            os.unlink(file_path)
        except (OSError, FileNotFoundError):
            pass
    
    @staticmethod
    def cleanup_temp_dir(dir_path: str):
        """Clean up a temporary directory"""
        try:
            import shutil
            shutil.rmtree(dir_path)
        except (OSError, FileNotFoundError):
            pass


class MockFactory:
    """Factory for creating standardized mock objects"""
    
    @staticmethod
    def create_driver_mock(current_url: str = "https://example.com") -> Mock:
        """Create a standardized WebDriver mock"""
        mock_driver = Mock()
        mock_driver.current_url = current_url
        mock_driver.window_handles = ["handle1"]
        mock_driver.current_window_handle = "handle1"
        mock_driver.get_cookies.return_value = []
        mock_driver.execute_script.return_value = {}
        mock_driver.find_elements.return_value = []
        mock_driver.find_element.return_value = Mock()
        mock_driver.page_source = "<html></html>"
        return mock_driver
    
    @staticmethod
    def create_wait_mock() -> Mock:
        """Create a standardized WebDriverWait mock"""
        mock_wait = Mock()
        mock_wait.until.return_value = Mock()
        return mock_wait
    
    @staticmethod
    def create_element_mock(text: str = "", tag_name: str = "div") -> Mock:
        """Create a standardized WebElement mock"""
        mock_element = Mock()
        mock_element.text = text
        mock_element.tag_name = tag_name
        mock_element.get_attribute.return_value = ""
        mock_element.is_displayed.return_value = True
        mock_element.is_enabled.return_value = True
        return mock_element
    
    @staticmethod
    def create_config_mock(songs: List[Dict] = None, download_folder: str = "/tmp") -> Mock:
        """Create a standardized configuration mock"""
        mock_config = Mock()
        mock_config.songs = songs or []
        mock_config.download_folder = download_folder
        return mock_config
    
    @staticmethod
    def create_track_list_mock(count: int = 3) -> List[Dict[str, Any]]:
        """Create a standardized track list for testing"""
        tracks = []
        track_names = ["Electronic Drum Kit", "Lead Electric Guitar", "Lead Vocal"]
        
        for i in range(count):
            tracks.append({
                'name': track_names[i % len(track_names)],
                'index': i,
                'data-index': str(i)
            })
        
        return tracks


class YAMLTestData:
    """Standard YAML test data for configuration testing"""
    
    VALID_CONFIG = """
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song1.html"
    name: "Test Song 1"
    description: "Test description"
    key: 2
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song2.html" 
    name: "Test Song 2"
    key: -1
"""
    
    INVALID_CONFIG = """
songs:
  - url: "not-a-valid-url"
    name: ""
    key: 999
"""
    
    MINIMAL_CONFIG = """
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song.html"
"""


class AssertionHelpers:
    """Common assertion helpers for tests"""
    
    @staticmethod
    def assert_mock_called_with_pattern(mock_obj: Mock, pattern: str):
        """Assert that mock was called with argument containing pattern"""
        for call in mock_obj.call_args_list:
            if any(pattern in str(arg) for arg in call[0]):
                return True
        raise AssertionError(f"Mock was not called with pattern: {pattern}")
    
    @staticmethod
    def assert_file_contains(file_path: str, content: str):
        """Assert that file contains specific content"""
        with open(file_path, 'r') as f:
            file_content = f.read()
            if content not in file_content:
                raise AssertionError(f"File {file_path} does not contain: {content}")
    
    @staticmethod
    def assert_dict_subset(subset: Dict, full_dict: Dict):
        """Assert that subset is contained in full_dict"""
        for key, value in subset.items():
            if key not in full_dict:
                raise AssertionError(f"Key '{key}' not found in dict")
            if full_dict[key] != value:
                raise AssertionError(f"Value mismatch for key '{key}': expected {value}, got {full_dict[key]}")


# Commonly used mock decorators and patterns
def patch_time(return_value: float = 1000.0):
    """Decorator to patch time.time() with a fixed return value"""
    return patch('time.time', return_value=return_value)


def patch_sleep():
    """Decorator to patch time.sleep() to speed up tests"""
    return patch('time.sleep')


def patch_file_operations():
    """Decorator to patch common file operations"""
    return patch('builtins.open', mock_open())


# Standard test configuration
class TestConfig:
    """Standard configuration values for tests"""
    
    DEFAULT_TIMEOUT = 1.0
    TEST_URLS = [
        "https://www.karaoke-version.com/custombackingtrack/artist/song1.html",
        "https://www.karaoke-version.com/custombackingtrack/artist/song2.html"
    ]
    TEST_TRACK_NAMES = [
        "Electronic Drum Kit",
        "Lead Electric Guitar", 
        "Piano",
        "Lead Vocal",
        "Backing Vocals"
    ]
    
    @classmethod
    def get_sample_song_data(cls) -> Dict[str, Any]:
        """Get standard sample song data for testing"""
        return {
            'name': 'Test Song',
            'url': cls.TEST_URLS[0],
            'description': 'Test song description',
            'key': 0
        }