"""
Test the centralized YAML utilities to ensure they work correctly
and can replace duplicate YAML parsing logic across test files.
"""

import unittest
import tempfile
import os
import yaml
from unittest.mock import patch, mock_open

from tests.yaml_test_helpers import (
    YAMLTestHelper,
    StandardYAMLContent,
    YAMLTestDecorators,
    YAMLConfigTester,
    YAMLAssertions
)


class TestYAMLTestHelper(unittest.TestCase):
    """Test the YAMLTestHelper utility class"""
    
    def test_create_temp_yaml_file(self):
        """Test creating temporary YAML files"""
        content = {"test": "data", "number": 42}
        temp_file = YAMLTestHelper.create_temp_yaml_file(content)
        
        try:
            # Verify file exists
            self.assertTrue(os.path.exists(temp_file))
            
            # Verify content is correct
            with open(temp_file, 'r') as f:
                loaded_content = yaml.safe_load(f)
                self.assertEqual(loaded_content, content)
        finally:
            YAMLTestHelper.cleanup_temp_file(temp_file)
    
    def test_load_yaml_from_string(self):
        """Test loading YAML from string"""
        yaml_string = """
        songs:
          - url: "https://example.com"
            name: "Test Song"
        """
        
        result = YAMLTestHelper.load_yaml_from_string(yaml_string)
        
        self.assertIn('songs', result)
        self.assertEqual(len(result['songs']), 1)
        self.assertEqual(result['songs'][0]['name'], "Test Song")
    
    def test_load_yaml_from_invalid_string(self):
        """Test handling of invalid YAML strings"""
        invalid_yaml = "invalid: yaml: content: {"
        
        with self.assertRaises(ValueError):
            YAMLTestHelper.load_yaml_from_string(invalid_yaml)
    
    def test_create_mock_yaml_file(self):
        """Test creating mock file objects"""
        content = {"test": "data"}
        mock_file = YAMLTestHelper.create_mock_yaml_file(content)
        
        # Mock file should be usable with open()
        with patch('builtins.open', mock_file):
            with open('test.yaml', 'r') as f:
                loaded = yaml.safe_load(f)
                self.assertEqual(loaded, content)
    
    def test_cleanup_temp_file(self):
        """Test cleanup of temporary files"""
        # Create a real temp file
        content = {"test": "cleanup"}
        temp_file = YAMLTestHelper.create_temp_yaml_file(content)
        
        # Verify it exists
        self.assertTrue(os.path.exists(temp_file))
        
        # Clean it up
        YAMLTestHelper.cleanup_temp_file(temp_file)
        
        # Verify it's gone
        self.assertFalse(os.path.exists(temp_file))
    
    def test_cleanup_nonexistent_file(self):
        """Test cleanup handles nonexistent files gracefully"""
        # Should not raise exception
        YAMLTestHelper.cleanup_temp_file("/nonexistent/file.yaml")


class TestStandardYAMLContent(unittest.TestCase):
    """Test the StandardYAMLContent utility class"""
    
    def test_get_valid_songs_config(self):
        """Test valid songs configuration"""
        config = StandardYAMLContent.get_valid_songs_config()
        
        self.assertIn('songs', config)
        self.assertEqual(len(config['songs']), 2)
        
        # Check first song
        song1 = config['songs'][0]
        self.assertIn('url', song1)
        self.assertIn('name', song1)
        self.assertIn('key', song1)
        self.assertIn('karaoke-version.com', song1['url'])
    
    def test_get_minimal_songs_config(self):
        """Test minimal songs configuration"""
        config = StandardYAMLContent.get_minimal_songs_config()
        
        self.assertIn('songs', config)
        self.assertEqual(len(config['songs']), 1)
        
        # Minimal should have only URL
        song = config['songs'][0]
        self.assertIn('url', song)
        self.assertNotIn('name', song)
        self.assertNotIn('key', song)
    
    def test_get_key_format_test_config(self):
        """Test key format testing configuration"""
        config = StandardYAMLContent.get_key_format_test_config()
        
        self.assertIn('songs', config)
        self.assertEqual(len(config['songs']), 5)
        
        # Check various key formats
        songs = config['songs']
        self.assertEqual(songs[0]['key'], 2)          # Integer
        self.assertEqual(songs[1]['key'], '+3')       # Plus string
        self.assertEqual(songs[2]['key'], '-2')       # Negative string
        self.assertNotIn('key', songs[3])             # No key
        self.assertEqual(songs[4]['key'], "5")        # String number
    
    def test_get_invalid_songs_config(self):
        """Test invalid songs configuration"""
        config = StandardYAMLContent.get_invalid_songs_config()
        
        self.assertIn('songs', config)
        songs = config['songs']
        
        # Should have invalid elements for testing
        self.assertTrue(any('wrong-domain' in song.get('url', '') for song in songs))
        self.assertTrue(any(song.get('name') == '' for song in songs))
    
    def test_get_empty_config(self):
        """Test empty configuration"""
        config = StandardYAMLContent.get_empty_config()
        
        self.assertIn('songs', config)
        self.assertEqual(config['songs'], [])
    
    def test_get_missing_songs_key_config(self):
        """Test configuration missing songs key"""
        config = StandardYAMLContent.get_missing_songs_key_config()
        
        self.assertNotIn('songs', config)
        self.assertIn('other_data', config)


class TestYAMLConfigTester(unittest.TestCase):
    """Test the YAMLConfigTester utility class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock config loader function
        def mock_config_loader():
            # Return different results based on what's being tested
            return getattr(self, '_test_return_value', [])
        
        self.config_tester = YAMLConfigTester(mock_config_loader)
    
    def test_valid_config_loading_test(self):
        """Test the valid config loading test"""
        # Set up return value
        self._test_return_value = [{'url': 'test1'}, {'url': 'test2'}]
        
        result = self.config_tester.test_valid_config_loading()
        self.assertTrue(result)
    
    def test_empty_config_loading_test(self):
        """Test the empty config loading test"""
        self._test_return_value = []
        
        result = self.config_tester.test_empty_config_loading()
        self.assertTrue(result)
    
    def test_file_not_found_handling_test(self):
        """Test the file not found handling test"""
        self._test_return_value = []
        
        result = self.config_tester.test_file_not_found_handling()
        self.assertTrue(result)


class TestYAMLAssertions(unittest.TestCase):
    """Test the YAMLAssertions utility class"""
    
    def test_assert_valid_songs_structure_success(self):
        """Test valid songs structure assertion passes"""
        songs = [
            {'url': 'https://example.com/song1'},
            {'url': 'https://example.com/song2'}
        ]
        
        # Should not raise
        YAMLAssertions.assert_valid_songs_structure(songs)
    
    def test_assert_valid_songs_structure_failure(self):
        """Test valid songs structure assertion fails appropriately"""
        # Not a list
        with self.assertRaises(AssertionError):
            YAMLAssertions.assert_valid_songs_structure("not a list")
        
        # Contains non-dict
        with self.assertRaises(AssertionError):
            YAMLAssertions.assert_valid_songs_structure([{'url': 'test'}, "not a dict"])
        
        # Missing URL
        with self.assertRaises(AssertionError):
            YAMLAssertions.assert_valid_songs_structure([{'name': 'test'}])
        
        # Empty URL
        with self.assertRaises(AssertionError):
            YAMLAssertions.assert_valid_songs_structure([{'url': ''}])
    
    def test_assert_song_has_required_fields_success(self):
        """Test required fields assertion passes"""
        song = {'url': 'https://example.com', 'name': 'Test Song', 'key': 0}
        required = ['url', 'name']
        
        # Should not raise
        YAMLAssertions.assert_song_has_required_fields(song, required)
    
    def test_assert_song_has_required_fields_failure(self):
        """Test required fields assertion fails appropriately"""
        song = {'url': 'https://example.com'}
        
        # Missing field
        with self.assertRaises(AssertionError):
            YAMLAssertions.assert_song_has_required_fields(song, ['url', 'name'])
        
        # Null field
        song_with_null = {'url': 'https://example.com', 'name': None}
        with self.assertRaises(AssertionError):
            YAMLAssertions.assert_song_has_required_fields(song_with_null, ['url', 'name'])
    
    def test_assert_key_value_in_range_success(self):
        """Test key range assertion passes"""
        # Integer key
        song1 = {'key': 5}
        YAMLAssertions.assert_key_value_in_range(song1)
        
        # String key with plus
        song2 = {'key': '+3'}
        YAMLAssertions.assert_key_value_in_range(song2)
        
        # String key negative
        song3 = {'key': '-5'}
        YAMLAssertions.assert_key_value_in_range(song3)
        
        # No key (should pass)
        song4 = {'name': 'test'}
        YAMLAssertions.assert_key_value_in_range(song4)
    
    def test_assert_key_value_in_range_failure(self):
        """Test key range assertion fails appropriately"""
        # Out of range high
        song1 = {'key': 15}
        with self.assertRaises(AssertionError):
            YAMLAssertions.assert_key_value_in_range(song1)
        
        # Out of range low
        song2 = {'key': -15}
        with self.assertRaises(AssertionError):
            YAMLAssertions.assert_key_value_in_range(song2)
        
        # String out of range
        song3 = {'key': '+20'}
        with self.assertRaises(AssertionError):
            YAMLAssertions.assert_key_value_in_range(song3)


class TestYAMLDecorators(unittest.TestCase):
    """Test the YAML decorator functions"""
    
    def test_with_mock_yaml_file_decorator(self):
        """Test the mock YAML file decorator"""
        test_content = {'test': 'data'}
        
        @YAMLTestDecorators.with_mock_yaml_file(test_content)
        def decorated_test():
            # Inside the decorator, file operations should be mocked
            with open('test.yaml', 'r') as f:
                loaded = yaml.safe_load(f)
                return loaded
        
        result = decorated_test()
        self.assertEqual(result, test_content)
    
    def test_with_temp_yaml_file_decorator(self):
        """Test the temporary YAML file decorator"""
        test_content = {'test': 'temp_file'}
        
        @YAMLTestDecorators.with_temp_yaml_file(test_content)
        def decorated_test(temp_file_path):
            # Should receive temp file path as first argument
            self.assertTrue(os.path.exists(temp_file_path))
            
            with open(temp_file_path, 'r') as f:
                loaded = yaml.safe_load(f)
                return loaded
        
        result = decorated_test()
        self.assertEqual(result, test_content)
    
    def test_with_yaml_error_decorator(self):
        """Test the YAML error decorator"""
        @YAMLTestDecorators.with_yaml_error()
        def decorated_test():
            # yaml.safe_load should raise error
            with self.assertRaises(yaml.YAMLError):
                yaml.safe_load("test")
            return True
        
        result = decorated_test()
        self.assertTrue(result)


class TestIntegrationScenarios(unittest.TestCase):
    """Test common integration scenarios using the utilities"""
    
    def test_complete_yaml_test_workflow(self):
        """Test a complete YAML testing workflow"""
        # Get standard test content
        content = StandardYAMLContent.get_valid_songs_config()
        
        # Create temp file
        temp_file = YAMLTestHelper.create_temp_yaml_file(content)
        
        try:
            # Verify file was created correctly
            self.assertTrue(os.path.exists(temp_file))
            
            # Load and verify content
            with open(temp_file, 'r') as f:
                loaded = yaml.safe_load(f)
            
            # Use assertions to verify structure
            YAMLAssertions.assert_valid_songs_structure(loaded['songs'])
            
            for song in loaded['songs']:
                YAMLAssertions.assert_song_has_required_fields(song, ['url', 'name'])
                YAMLAssertions.assert_key_value_in_range(song)
        
        finally:
            # Clean up
            YAMLTestHelper.cleanup_temp_file(temp_file)
            self.assertFalse(os.path.exists(temp_file))
    
    def test_mock_vs_temp_file_consistency(self):
        """Test that mock and temp file approaches give same results"""
        content = StandardYAMLContent.get_minimal_songs_config()
        
        # Test with mock file
        with patch('builtins.open', YAMLTestHelper.create_mock_yaml_file(content)):
            with open('mock.yaml', 'r') as f:
                mock_result = yaml.safe_load(f)
        
        # Test with temp file
        temp_file = YAMLTestHelper.create_temp_yaml_file(content)
        try:
            with open(temp_file, 'r') as f:
                temp_result = yaml.safe_load(f)
        finally:
            YAMLTestHelper.cleanup_temp_file(temp_file)
        
        # Results should be identical
        self.assertEqual(mock_result, temp_result)
        self.assertEqual(mock_result, content)


if __name__ == '__main__':
    unittest.main()