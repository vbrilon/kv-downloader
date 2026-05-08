import pytest
import os
from unittest.mock import patch, mock_open

from packages.configuration import config
from packages.configuration import config_manager

# Import centralized YAML utilities
from tests.yaml_test_helpers import (
    YAMLTestHelper,
    StandardYAMLContent,
    YAMLTestDecorators,
    YAMLConfigTester
)

class TestConfig:
    def test_config_loads_environment_variables(self):
        """Test that config properly loads environment variables.

        Patching `load_dotenv` to a no-op is required because the developer's
        `.env` file would otherwise re-set values during `importlib.reload`.
        """
        with patch.dict(os.environ, {
            'KV_USERNAME': 'test_user',
            'KV_PASSWORD': 'test_pass',
            'KV_LOGIN_URL': 'https://test.com/login'
        }), patch('dotenv.load_dotenv', lambda *a, **kw: False):
            import importlib
            importlib.reload(config)

            assert config.USERNAME == 'test_user'
            assert config.PASSWORD == 'test_pass'
            assert config.LOGIN_URL == 'https://test.com/login'

    def test_config_has_default_values(self):
        """Defaults must apply when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True), \
             patch('dotenv.load_dotenv', lambda *a, **kw: False):
            import importlib
            importlib.reload(config)

            assert config.DOWNLOAD_FOLDER == "./downloads"
            assert config.DELAY_BETWEEN_DOWNLOADS == 5
            assert config.MAX_RETRIES == 3
            assert "karaoke-version.com" in config.LOGIN_URL

    def test_config_missing_credentials_returns_none(self):
        """Test behavior when credentials are missing"""
        with patch.dict(os.environ, {}, clear=True), \
             patch('dotenv.load_dotenv', lambda *a, **kw: False):
            import importlib
            importlib.reload(config)

            assert config.USERNAME is None
            assert config.PASSWORD is None

    def test_load_songs_config_success(self):
        """Test successful loading of songs configuration"""
        mock_yaml_content = StandardYAMLContent.get_valid_songs_config()

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', YAMLTestHelper.create_mock_yaml_file(mock_yaml_content)), \
             patch('yaml.safe_load', return_value=mock_yaml_content):
            songs = config_manager.load_songs_config()

            assert len(songs) == 2
            assert songs[0]['url'] == mock_yaml_content['songs'][0]['url']
            assert songs[0]['name'] == mock_yaml_content['songs'][0]['name']
            assert songs[1]['url'] == mock_yaml_content['songs'][1]['url']
            assert songs[1]['name'] == mock_yaml_content['songs'][1]['name']

    def test_load_songs_config_file_not_found(self):
        """Test behavior when songs config file is not found"""
        with patch('pathlib.Path.exists', return_value=False):
            songs = config_manager.load_songs_config()
            assert songs == []

    def test_load_songs_config_yaml_error(self):
        """Test behavior when YAML file has syntax errors"""
        import yaml
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="invalid: yaml: content:")), \
             patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML")):
            songs = config_manager.load_songs_config()
            assert songs == []

    def test_load_songs_config_empty_songs(self):
        """Test behavior when config file has no songs"""
        mock_yaml_content = StandardYAMLContent.get_missing_songs_key_config()

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', YAMLTestHelper.create_mock_yaml_file(mock_yaml_content)), \
             patch('yaml.safe_load', return_value=mock_yaml_content):
            songs = config_manager.load_songs_config()
            assert songs == []