"""
YAML testing utilities for Karaoke Automation tests

This module provides centralized YAML handling for tests to eliminate
duplicate YAML parsing logic across multiple test files.
"""

import yaml
import tempfile
import os
from typing import Dict, List, Any, Optional
from unittest.mock import mock_open, patch
from pathlib import Path


class YAMLTestHelper:
    """Helper class for YAML operations in tests"""
    
    @staticmethod
    def create_temp_yaml_file(content: Dict[str, Any], suffix: str = '.yaml') -> str:
        """Create a temporary YAML file with given content"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as temp_file:
            yaml.dump(content, temp_file, default_flow_style=False)
            return temp_file.name
    
    @staticmethod
    def load_yaml_from_string(yaml_string: str) -> Dict[str, Any]:
        """Load YAML content from string"""
        try:
            return yaml.safe_load(yaml_string)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML content: {e}")
    
    @staticmethod
    def create_mock_yaml_file(content: Dict[str, Any]):
        """Create a mock file object for YAML content"""
        yaml_string = yaml.dump(content, default_flow_style=False)
        return mock_open(read_data=yaml_string)
    
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """Clean up a temporary YAML file"""
        try:
            os.unlink(file_path)
        except (OSError, FileNotFoundError):
            pass


class StandardYAMLContent:
    """Standard YAML content for testing"""
    
    @staticmethod
    def get_valid_songs_config() -> Dict[str, Any]:
        """Get a valid songs configuration for testing"""
        return {
            'songs': [
                {
                    'url': 'https://www.karaoke-version.com/custombackingtrack/artist/song1.html',
                    'name': 'Test_Song_One',
                    'description': 'First test song',
                    'key': 2
                },
                {
                    'url': 'https://www.karaoke-version.com/custombackingtrack/artist/song2.html', 
                    'name': 'Test_Song_Two',
                    'description': 'Second test song',
                    'key': -1
                }
            ]
        }
    
    @staticmethod
    def get_minimal_songs_config() -> Dict[str, Any]:
        """Get a minimal songs configuration for testing"""
        return {
            'songs': [
                {
                    'url': 'https://www.karaoke-version.com/custombackingtrack/artist/minimal.html'
                }
            ]
        }
    
    @staticmethod
    def get_key_format_test_config() -> Dict[str, Any]:
        """Get songs config with various key formats for testing"""
        return {
            'songs': [
                {
                    'url': 'https://www.karaoke-version.com/custombackingtrack/test/song1.html',
                    'name': 'Song_With_Integer_Key',
                    'key': 2
                },
                {
                    'url': 'https://www.karaoke-version.com/custombackingtrack/test/song2.html',
                    'name': 'Song_With_Plus_String_Key', 
                    'key': '+3'
                },
                {
                    'url': 'https://www.karaoke-version.com/custombackingtrack/test/song3.html',
                    'name': 'Song_With_Negative_String_Key',
                    'key': '-2'
                },
                {
                    'url': 'https://www.karaoke-version.com/custombackingtrack/test/song4.html',
                    'name': 'Song_With_No_Key'
                    # No key field - should default to 0
                },
                {
                    'url': 'https://www.karaoke-version.com/custombackingtrack/test/song5.html',
                    'name': 'Song_With_String_Number_Key',
                    'key': "5"
                }
            ]
        }
    
    @staticmethod
    def get_invalid_songs_config() -> Dict[str, Any]:
        """Get invalid songs configuration for error testing"""
        return {
            'songs': [
                {
                    'url': 'not-a-valid-url',
                    'name': '',  # Empty name
                    'key': 999   # Out of range key
                },
                {
                    'url': 'https://wrong-domain.com/song.html',  # Wrong domain
                    'key': 'invalid'  # Invalid key type
                }
            ]
        }
    
    @staticmethod
    def get_empty_config() -> Dict[str, Any]:
        """Get empty configuration for testing"""
        return {'songs': []}
    
    @staticmethod
    def get_missing_songs_key_config() -> Dict[str, Any]:
        """Get configuration missing the 'songs' key"""
        return {'other_data': 'value'}


class YAMLTestDecorators:
    """Decorators for common YAML testing patterns"""
    
    @staticmethod
    def with_mock_yaml_file(content: Dict[str, Any]):
        """Decorator to mock a YAML file with given content"""
        def decorator(test_func):
            def wrapper(*args, **kwargs):
                yaml_string = yaml.dump(content, default_flow_style=False)
                with patch('builtins.open', mock_open(read_data=yaml_string)):
                    with patch('yaml.safe_load', return_value=content):
                        return test_func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def with_temp_yaml_file(content: Dict[str, Any]):
        """Decorator to create a temporary YAML file for the test"""
        def decorator(test_func):
            def wrapper(*args, **kwargs):
                temp_file = YAMLTestHelper.create_temp_yaml_file(content)
                try:
                    # Pass the temp file path as first argument
                    return test_func(temp_file, *args, **kwargs)
                finally:
                    YAMLTestHelper.cleanup_temp_file(temp_file)
            return wrapper
        return decorator
    
    @staticmethod
    def with_yaml_error():
        """Decorator to simulate YAML parsing errors"""
        def decorator(test_func):
            def wrapper(*args, **kwargs):
                with patch('yaml.safe_load', side_effect=yaml.YAMLError("Test YAML error")):
                    return test_func(*args, **kwargs)
            return wrapper
        return decorator


class YAMLConfigTester:
    """Helper class for testing YAML configuration loading"""
    
    def __init__(self, config_loader_func):
        """Initialize with a config loading function"""
        self.load_config = config_loader_func
    
    def test_valid_config_loading(self) -> bool:
        """Test loading valid configuration"""
        content = StandardYAMLContent.get_valid_songs_config()
        with patch('builtins.open', YAMLTestHelper.create_mock_yaml_file(content)):
            with patch('yaml.safe_load', return_value=content):
                songs = self.load_config()
                return len(songs) == 2 and all('url' in song for song in songs)
    
    def test_empty_config_loading(self) -> bool:
        """Test loading empty configuration"""
        content = StandardYAMLContent.get_empty_config()
        with patch('builtins.open', YAMLTestHelper.create_mock_yaml_file(content)):
            with patch('yaml.safe_load', return_value=content):
                songs = self.load_config()
                return songs == []
    
    def test_file_not_found_handling(self) -> bool:
        """Test file not found error handling"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            songs = self.load_config()
            return songs == []
    
    def test_yaml_error_handling(self) -> bool:
        """Test YAML parsing error handling"""
        with patch('builtins.open', mock_open(read_data="invalid: yaml: content:")):
            with patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML")):
                songs = self.load_config()
                return songs == []
    
    def test_missing_songs_key_handling(self) -> bool:
        """Test missing 'songs' key handling"""
        content = StandardYAMLContent.get_missing_songs_key_config()
        with patch('builtins.open', YAMLTestHelper.create_mock_yaml_file(content)):
            with patch('yaml.safe_load', return_value=content):
                songs = self.load_config()
                return songs == []
    
    def run_all_tests(self) -> bool:
        """Run all standard YAML config tests"""
        tests = [
            ("Valid config loading", self.test_valid_config_loading),
            ("Empty config loading", self.test_empty_config_loading),
            ("File not found handling", self.test_file_not_found_handling),
            ("YAML error handling", self.test_yaml_error_handling),
            ("Missing songs key handling", self.test_missing_songs_key_handling)
        ]
        
        passed = 0
        for test_name, test_func in tests:
            try:
                if test_func():
                    print(f"✅ {test_name}")
                    passed += 1
                else:
                    print(f"❌ {test_name}")
            except Exception as e:
                print(f"❌ {test_name} - Exception: {e}")
        
        return passed == len(tests)


# Common YAML assertion helpers
class YAMLAssertions:
    """Common assertions for YAML testing"""
    
    @staticmethod
    def assert_valid_songs_structure(songs: List[Dict[str, Any]]):
        """Assert that songs list has valid structure"""
        assert isinstance(songs, list), "Songs should be a list"
        for song in songs:
            assert isinstance(song, dict), "Each song should be a dict"
            assert 'url' in song, "Each song should have a URL"
            assert song['url'], "Song URL should not be empty"
    
    @staticmethod
    def assert_song_has_required_fields(song: Dict[str, Any], required_fields: List[str]):
        """Assert that song has all required fields"""
        for field in required_fields:
            assert field in song, f"Song missing required field: {field}"
            assert song[field] is not None, f"Song field {field} should not be None"
    
    @staticmethod
    def assert_key_value_in_range(song: Dict[str, Any], min_val: int = -12, max_val: int = 12):
        """Assert that song key value is in valid range"""
        if 'key' in song:
            key_val = song['key']
            if isinstance(key_val, str):
                key_val = int(key_val.replace('+', ''))
            assert min_val <= key_val <= max_val, f"Key value {key_val} out of range [{min_val}, {max_val}]"


# Export commonly used constants
VALID_KARAOKE_DOMAIN = "karaoke-version.com"
VALID_URL_PATTERN = r"https://www\.karaoke-version\.com/custombackingtrack/"

# Standard test file names
TEST_YAML_FILES = {
    'valid': 'test_songs_valid.yaml',
    'invalid': 'test_songs_invalid.yaml', 
    'empty': 'test_songs_empty.yaml',
    'minimal': 'test_songs_minimal.yaml'
}