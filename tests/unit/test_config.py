import pytest
import os
from unittest.mock import patch, mock_open
import config

# Import centralized YAML utilities
from tests.yaml_test_helpers import (
    YAMLTestHelper, 
    StandardYAMLContent, 
    YAMLTestDecorators,
    YAMLConfigTester
)

class TestConfig:
    def test_config_loads_environment_variables(self):
        """Test that config properly loads environment variables"""
        with patch.dict(os.environ, {
            'KV_USERNAME': 'test_user',
            'KV_PASSWORD': 'test_pass',
            'KV_LOGIN_URL': 'https://test.com/login'
        }):
            # Reload config to pick up new env vars
            import importlib
            importlib.reload(config)
            
            assert config.USERNAME == 'test_user'
            assert config.PASSWORD == 'test_pass'
            assert config.LOGIN_URL == 'https://test.com/login'
    
    def test_config_has_default_values(self):
        """Test that config has sensible defaults"""
        # Clear env and reload to test defaults
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            importlib.reload(config)
            
            assert config.DOWNLOAD_FOLDER == "./downloads"
            assert config.DELAY_BETWEEN_DOWNLOADS == 3
            assert config.MAX_RETRIES == 3
            assert "karaoke-version.com" in config.LOGIN_URL
    
    def test_config_missing_credentials_returns_none(self):
        """Test behavior when credentials are missing"""
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = None
            import importlib
            importlib.reload(config)
            
            assert config.USERNAME is None
            assert config.PASSWORD is None
    
    def test_load_songs_config_success(self):
        """Test successful loading of songs configuration"""
        mock_yaml_content = StandardYAMLContent.get_valid_songs_config()
        
        with patch('builtins.open', YAMLTestHelper.create_mock_yaml_file(mock_yaml_content)):
            with patch('yaml.safe_load', return_value=mock_yaml_content):
                songs = config.load_songs_config()
                
                assert len(songs) == 2
                assert songs[0]['url'] == mock_yaml_content['songs'][0]['url']
                assert songs[0]['name'] == mock_yaml_content['songs'][0]['name']
                assert songs[1]['url'] == mock_yaml_content['songs'][1]['url']
                assert songs[1]['name'] == mock_yaml_content['songs'][1]['name']
    
    def test_load_songs_config_file_not_found(self):
        """Test behavior when songs config file is not found"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            songs = config.load_songs_config()
            assert songs == []
    
    def test_load_songs_config_yaml_error(self):
        """Test behavior when YAML file has syntax errors"""
        import yaml
        with patch('builtins.open', mock_open(read_data="invalid: yaml: content:")):
            with patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML")):
                songs = config.load_songs_config()
                assert songs == []
    
    def test_load_songs_config_empty_songs(self):
        """Test behavior when config file has no songs"""
        mock_yaml_content = StandardYAMLContent.get_missing_songs_key_config()
        
        with patch('builtins.open', YAMLTestHelper.create_mock_yaml_file(mock_yaml_content)):
            with patch('yaml.safe_load', return_value=mock_yaml_content):
                songs = config.load_songs_config()
                assert songs == []