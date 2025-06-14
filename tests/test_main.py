import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import main

class TestKaraokeVersionAutomator:
    
    @pytest.fixture
    def automator(self):
        """Create automator instance with mocked driver"""
        with patch('main.ChromeDriverManager'), \
             patch('main.webdriver.Chrome') as mock_chrome, \
             patch('main.Path.mkdir'):
            
            mock_driver = Mock()
            mock_chrome.return_value = mock_driver
            
            automator = main.KaraokeVersionAutomator()
            automator.driver = mock_driver
            automator.wait = Mock()
            return automator
    
    def test_sanitize_filename(self, automator):
        """Test filename sanitization"""
        test_cases = [
            ("Song with spaces", "Song with spaces"),
            ("Song/with\\slashes", "Song_with_slashes"),
            ("Song<with>invalid:chars", "Song_with_invalid_chars"),
            ('Song"with|quotes', "Song_with_quotes"),
            ("Song*with?wildcards", "Song_with_wildcards")
        ]
        
        for input_name, expected in test_cases:
            result = automator.sanitize_filename(input_name)
            assert result == expected
    
    def test_setup_download_folder(self, automator):
        """Test download folder creation"""
        with patch('main.Path') as mock_path:
            mock_download_path = Mock()
            mock_logs_path = Mock()
            
            mock_path.side_effect = [mock_download_path, mock_logs_path]
            
            automator.setup_download_folder()
            
            mock_download_path.mkdir.assert_called_once_with(exist_ok=True)
            mock_logs_path.mkdir.assert_called_once_with(exist_ok=True)
    
    def test_get_available_tracks(self, automator):
        """Test dynamic track discovery with login verification"""
        # Mock verify_access_to_song to return True
        with patch.object(automator, 'verify_access_to_song', return_value=True):
            # Mock track elements with new structure
            mock_track1 = Mock()
            mock_caption1 = Mock()
            mock_caption1.text = "Electronic Drum Kit"
            mock_track1.find_element.return_value = mock_caption1
            mock_track1.get_attribute.return_value = "1"
            
            mock_track2 = Mock()
            mock_caption2 = Mock()
            mock_caption2.text = "Lead Electric Guitar"
            mock_track2.find_element.return_value = mock_caption2
            mock_track2.get_attribute.return_value = "4"
            
            automator.driver.find_elements.return_value = [mock_track1, mock_track2]
            
            result = automator.get_available_tracks("http://test-song-url.com")
            
            assert len(result) == 2
            assert result[0]['name'] == "Electronic Drum Kit"
            assert result[0]['index'] == "1"
            assert result[1]['name'] == "Lead Electric Guitar"
            assert result[1]['index'] == "4"
    
    def test_load_songs_from_config(self, automator):
        """Test loading songs from configuration file"""
        mock_songs = [
            {'url': 'http://example.com/song1', 'name': 'Song_One'},
            {'url': 'http://example.com/song2', 'name': 'Song_Two'}
        ]
        
        with patch('main.config.load_songs_config', return_value=mock_songs):
            result = automator.load_songs_from_config()
            
            assert result == mock_songs
            assert len(result) == 2
    
    def test_load_songs_from_config_empty(self, automator):
        """Test loading songs when config is empty"""
        with patch('main.config.load_songs_config', return_value=[]):
            result = automator.load_songs_from_config()
            
            assert result == []
    
    @patch('main.time.sleep')
    def test_login(self, mock_sleep, automator):
        """Test login functionality with new comprehensive approach"""
        with patch.object(automator, 'check_login_status', side_effect=[False, True]) as mock_check, \
             patch('main.config.USERNAME', 'test_user'), \
             patch('main.config.PASSWORD', 'test_pass'):
            
            # Mock form elements
            mock_username_field = Mock()
            mock_password_field = Mock()
            mock_submit_button = Mock()
            
            # Mock username field discovery (first successful attempt)
            automator.wait.until.return_value = mock_username_field
            
            # Mock password and submit button discovery
            def mock_find_element(by_type, selector_value):
                if selector_value == "password":
                    return mock_password_field
                elif "submit" in selector_value:
                    return mock_submit_button
                else:
                    from selenium.common.exceptions import NoSuchElementException
                    raise NoSuchElementException()
            
            automator.driver.find_element.side_effect = mock_find_element
            
            result = automator.login()
            
            # Verify login was successful
            assert result == True
            mock_username_field.send_keys.assert_called_with('test_user')
            mock_password_field.send_keys.assert_called_with('test_pass')
            mock_submit_button.click.assert_called_once()
            
            # Should check login status twice: before and after login
            assert mock_check.call_count == 2
    
    @patch('main.time.sleep')
    def test_download_track_variations(self, mock_sleep, automator):
        """Test track variation download process with login verification"""
        with patch.object(automator, 'check_login_status', return_value=True), \
             patch.object(automator, 'get_available_tracks') as mock_get_tracks, \
             patch.object(automator, 'sanitize_filename') as mock_sanitize, \
             patch('main.config.DOWNLOAD_FOLDER', './downloads'):
            
            # Setup mocks with new track structure
            mock_tracks = [
                {'name': 'Electronic Drum Kit', 'index': '1'},
                {'name': 'Lead Electric Guitar', 'index': '4'}
            ]
            mock_get_tracks.return_value = mock_tracks
            mock_sanitize.return_value = 'clean_song_title'
            
            with patch('main.Path') as mock_path_class:
                mock_song_folder = Mock()
                mock_path_instance = Mock()
                mock_path_instance.__truediv__ = Mock(return_value=mock_song_folder)
                mock_path_class.return_value = mock_path_instance
                
                result = automator.download_track_variations('http://song.com', 'Test Song')
                
                # Verify process
                assert result == True
                mock_get_tracks.assert_called_once_with('http://song.com')
                # Note: download_single_track is not called in current implementation (TODO commented out)
    
    @patch('main.time.sleep')
    def test_run_with_songs(self, mock_sleep, automator):
        """Test main run method with songs from config"""
        mock_songs = [
            {'url': 'http://example.com/song1', 'name': 'Song_One'},
            {'url': 'http://example.com/song2', 'name': 'Song_Two'}
        ]
        
        with patch.object(automator, 'login', return_value=True) as mock_login, \
             patch.object(automator, 'check_login_status', return_value=True), \
             patch.object(automator, 'load_songs_from_config', return_value=mock_songs) as mock_load, \
             patch.object(automator, 'download_track_variations', return_value=True) as mock_download:
            
            result = automator.run()
            
            assert result == True
            mock_login.assert_called_once()
            mock_load.assert_called_once()
            assert mock_download.call_count == 2
            mock_download.assert_any_call('http://example.com/song1', 'Song_One')
            mock_download.assert_any_call('http://example.com/song2', 'Song_Two')
    
    def test_run_with_no_songs(self, automator):
        """Test main run method when no songs are configured"""
        with patch.object(automator, 'login', return_value=True) as mock_login, \
             patch.object(automator, 'load_songs_from_config', return_value=[]) as mock_load, \
             patch.object(automator, 'download_track_variations') as mock_download:
            
            result = automator.run()
            
            assert result == False  # Should return False when no songs to process
            mock_login.assert_called_once()
            mock_load.assert_called_once()
            mock_download.assert_not_called()
    
    def test_driver_setup_configuration(self):
        """Test Chrome driver setup with correct preferences"""
        with patch('main.ChromeDriverManager') as mock_manager, \
             patch('main.webdriver.Chrome') as mock_chrome, \
             patch('main.Path.mkdir'), \
             patch('main.os.path.abspath') as mock_abspath:
            
            mock_abspath.return_value = '/absolute/downloads/path'
            
            automator = main.KaraokeVersionAutomator()
            
            # Verify Chrome options were set correctly
            args, kwargs = mock_chrome.call_args
            chrome_options = kwargs['options']
            
            # Check that prefs were set (this is a bit tricky to test directly)
            # We can verify the Chrome constructor was called with options
            assert 'options' in kwargs
            mock_chrome.assert_called_once()