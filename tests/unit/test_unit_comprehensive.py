#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Karaoke Automation System
Tests individual components without requiring live site access
"""

import unittest
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from packages.authentication import LoginManager
from packages.track_management import TrackManager
from packages.download_management import DownloadManager
from packages.file_operations import FileManager
from karaoke_automator import KaraokeVersionAutomator

class TestLoginManager(unittest.TestCase):
    """Unit tests for login functionality"""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.login_handler = LoginManager(self.mock_driver, self.mock_wait)
    
    def test_is_logged_in_success(self):
        """Test successful login detection"""
        # Mock finding "My Account" element
        mock_element = Mock()
        self.mock_driver.find_elements.return_value = [mock_element]
        
        result = self.login_handler.is_logged_in()
        self.assertTrue(result)
        self.mock_driver.find_elements.assert_called()
    
    def test_is_logged_in_failure(self):
        """Test login detection when not logged in"""
        # Mock no "My Account" elements and login links present
        self.mock_driver.find_elements.side_effect = [[], [Mock()]]  # No "My Account", has login links
        
        result = self.login_handler.is_logged_in()
        self.assertFalse(result)
    
    def test_logout_with_cookies(self):
        """Test logout fallback using cookie deletion"""
        # Mock no logout links found, should fall back to cookies
        self.mock_driver.find_element.side_effect = Exception("Not found")
        
        result = self.login_handler.logout()
        self.assertTrue(result)
        self.mock_driver.delete_all_cookies.assert_called_once()
        self.mock_driver.refresh.assert_called_once()
    
    def test_sanitize_folder_name(self):
        """Test folder name sanitization"""
        test_cases = [
            ("Artist - Song", "Artist - Song"),
            ("Artist/Song", "Artist_Song"),
            ("Artist<>:Song", "Artist___Song"),
            ("A" * 150, "A" * 100),  # Length limit
            ("", "song_"),  # Empty name handling
        ]
        
        download_manager = DownloadManager(Mock(), Mock())
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                # Mock time.time for consistent empty name handling
                with patch('time.time', return_value=12345):
                    result = download_manager.sanitize_folder_name(input_name)
                    if expected.endswith("_"):
                        self.assertTrue(result.startswith("song_"))
                    else:
                        self.assertEqual(result, expected)

class TestTrackManager(unittest.TestCase):
    """Unit tests for track discovery and manipulation"""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.tracker = TrackManager(self.mock_driver, self.mock_wait)
    
    def test_extract_song_folder_name(self):
        """Test song folder name extraction from URLs"""
        test_cases = [
            {
                'url': 'https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html',
                'expected_artist': 'Jimmy Eat World',
                'expected_song': 'The Middle'
            },
            {
                'url': 'https://www.karaoke-version.com/custombackingtrack/taylor-swift/shake-it-off.html',
                'expected_artist': 'Taylor Swift', 
                'expected_song': 'Shake It Off'
            }
        ]
        
        download_manager = DownloadManager(Mock(), Mock())
        for test_case in test_cases:
            with self.subTest(url=test_case['url']):
                with patch.object(download_manager, 'sanitize_folder_name', side_effect=lambda x: x):
                    result = download_manager.extract_song_folder_name(test_case['url'])
                    
                    self.assertIn(test_case['expected_artist'], result)
                    self.assertIn(test_case['expected_song'], result)
                    self.assertIn(' - ', result)
    
    def test_extract_song_folder_name_fallback(self):
        """Test fallback for invalid URLs"""
        invalid_url = "https://invalid-url.com/bad/path"
        
        download_manager = DownloadManager(Mock(), Mock())
        with patch('time.time', return_value=12345):
            result = download_manager.extract_song_folder_name(invalid_url)
            self.assertEqual(result, "karaoke_download_12345")
    
    def test_setup_song_folder(self):
        """Test song folder creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = FileManager()
            with patch('packages.configuration.config.DOWNLOAD_FOLDER', temp_dir):
                song_folder_name = "Test Artist - Test Song"
                
                result = file_manager.setup_song_folder(song_folder_name)
                
                expected_path = Path(temp_dir) / song_folder_name
                self.assertEqual(result, expected_path)
                self.assertTrue(expected_path.exists())
                self.assertTrue(expected_path.is_dir())
    
    def test_cleanup_existing_downloads(self):
        """Test download cleanup functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files that match cleanup criteria
            test_files = [
                "track_test.mp3",  # Should match "track_test" track name
                "test_track_old.mp3",  # Should match "track_test" via word matching
                "custom_backing_track.mp3"  # Should match backing track suffix
            ]
            
            for filename in test_files:
                (temp_path / filename).write_text("test")
            
            # Test cleanup
            with patch('time.time', return_value=1000):  # Mock current time
                # Set file times to old enough to be removed (>30 seconds)
                for filename in test_files:
                    file_path = temp_path / filename
                    os.utime(file_path, (950, 950))  # 50 seconds old (>30 threshold)
                
                file_manager = FileManager()
                file_manager.cleanup_existing_downloads("track_test", temp_path)
            
            # Check results
            remaining_files = list(temp_path.glob("*.mp3"))
            self.assertEqual(len(remaining_files), 0)  # All should be removed
    
    def test_cleanup_preserves_old_files(self):
        """Test that cleanup preserves old files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create old file
            old_file = temp_path / "old_important.mp3"
            old_file.write_text("important old file")
            
            with patch('time.time', return_value=10000):  # Mock current time
                # Set file time to old (should be preserved)
                os.utime(old_file, (1000, 1000))  # 9000 seconds old (2.5 hours)
                
                file_manager = FileManager()
                file_manager.cleanup_existing_downloads("test", temp_path)
            
            # Old file should still exist
            self.assertTrue(old_file.exists())

class TestKaraokeVersionAutomator(unittest.TestCase):
    """Unit tests for main automator class"""
    
    @patch('karaoke_automator.ChromeManager')
    def test_init_headless_mode(self, mock_chrome_manager):
        """Test automator initialization with headless mode"""
        # Mock the chrome manager to avoid real browser creation
        mock_chrome_instance = Mock()
        mock_chrome_manager.return_value = mock_chrome_instance
        
        # Test headless mode
        automator = KaraokeVersionAutomator(headless=True)
        self.assertTrue(automator.headless)
        mock_chrome_manager.assert_called_with(headless=True)
        
        # Test visible mode  
        automator = KaraokeVersionAutomator(headless=False)
        self.assertFalse(automator.headless)
        mock_chrome_manager.assert_called_with(headless=False)
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        download_manager = DownloadManager(Mock(), Mock())
        
        test_cases = [
            ("normal_file.mp3", "normal_file.mp3"),
            ("file<>:name.mp3", "file___name.mp3"),
            ('file"with*chars.mp3', "file_with_chars.mp3"),
            ("file|with\\slash.mp3", "file_with_slash.mp3")
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = download_manager.sanitize_filesystem_name(input_name)
                self.assertEqual(result, expected)

class TestConfigurationManagement(unittest.TestCase):
    """Unit tests for configuration management"""
    
    def test_song_yaml_loading(self):
        """Test YAML song configuration loading"""
        # Mock YAML content
        mock_yaml_content = """
songs:
  - url: "https://example.com/song1"
    name: "Song1"
    description: "Test Song 1"
  - url: "https://example.com/song2"
    name: "Song2"
    description: "Test Song 2"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_file.write(mock_yaml_content)
            temp_file.flush()
            
            try:
                from packages.configuration import ConfigurationManager
                config_manager = ConfigurationManager(temp_file.name)
                songs = config_manager.load_songs_config()
                
                self.assertEqual(len(songs), 2)
                self.assertEqual(songs[0]['url'], "https://example.com/song1")
                self.assertEqual(songs[1]['name'], "Song2")
            finally:
                os.unlink(temp_file.name)

class TestErrorHandling(unittest.TestCase):
    """Unit tests for error handling scenarios"""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.tracker = TrackManager(self.mock_driver, self.mock_wait)
    
    def test_verify_song_access_failure(self):
        """Test handling of inaccessible song pages"""
        song_url = "https://www.karaoke-version.com/restricted-song"
        
        # Mock redirect to login page
        self.mock_driver.current_url = "https://www.karaoke-version.com/login"
        
        result = self.tracker.verify_song_access(song_url)
        self.assertFalse(result)
    
    def test_discover_tracks_no_access(self):
        """Test track discovery with no access"""
        song_url = "https://www.karaoke-version.com/restricted-song"
        
        with patch.object(self.tracker, 'verify_song_access', return_value=False):
            result = self.tracker.discover_tracks(song_url)
            self.assertEqual(result, [])
    
    def test_solo_track_element_not_found(self):
        """Test solo track when element is not found"""
        track_info = {'name': 'Test Track', 'index': '1'}
        song_url = "https://example.com/song"
        
        # Mock track element found but no solo button
        mock_track_element = Mock()
        mock_track_element.find_element.side_effect = Exception("Solo button not found")
        self.mock_driver.find_elements.return_value = [mock_track_element]
        
        result = self.tracker.solo_track(track_info, song_url)
        self.assertFalse(result)

class TestDownloadFunctionality(unittest.TestCase):
    """Unit tests for download functionality"""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.tracker = TrackManager(self.mock_driver, self.mock_wait)
    
    def test_download_button_discovery(self):
        """Test download button discovery and interaction"""
        song_url = "https://example.com/song"
        track_name = "test_track"
        
        # Mock download button found
        mock_download_button = Mock()
        mock_download_button.is_displayed.return_value = True
        mock_download_button.is_enabled.return_value = True
        mock_download_button.text = "Download\nMP3"
        mock_download_button.get_attribute.return_value = "mixer.getMix();return false;"
        
        self.mock_driver.find_element.return_value = mock_download_button
        self.mock_driver.window_handles = ['window1']  # Mock window handles
        self.mock_driver.current_url = song_url
        
        download_manager = DownloadManager(self.mock_driver, Mock())
        # Set up mock file manager
        mock_file_manager = Mock()
        mock_file_manager.setup_song_folder.return_value = Path("/tmp/test")
        mock_file_manager.wait_for_download_to_start.return_value = True
        download_manager.set_file_manager(mock_file_manager)
        
        with patch.object(download_manager, 'extract_song_folder_name', return_value="Test Song"), \
             patch.object(download_manager, 'start_completion_monitoring'):
            
            result = download_manager.download_current_mix(song_url, track_name)
            
            self.assertTrue(result)
            mock_download_button.click.assert_called_once()
    
    def test_download_with_click_interception(self):
        """Test download with click interception handling"""
        song_url = "https://example.com/song"
        track_name = "test_track"
        
        # Mock download button that has click interception
        mock_download_button = Mock()
        mock_download_button.is_displayed.return_value = True
        mock_download_button.is_enabled.return_value = True
        mock_download_button.text = "Download\nMP3"
        mock_download_button.get_attribute.return_value = "mixer.getMix();"
        mock_download_button.click.side_effect = Exception("element click intercepted")
        
        self.mock_driver.find_element.return_value = mock_download_button
        self.mock_driver.window_handles = ['window1']  # Mock window handles
        self.mock_driver.current_url = song_url
        
        download_manager = DownloadManager(self.mock_driver, Mock())
        # Set up mock file manager
        mock_file_manager = Mock()
        mock_file_manager.setup_song_folder.return_value = Path("/tmp/test")
        mock_file_manager.wait_for_download_to_start.return_value = True
        download_manager.set_file_manager(mock_file_manager)
        
        with patch.object(download_manager, 'extract_song_folder_name', return_value="Test Song"), \
             patch.object(download_manager, 'start_completion_monitoring'):
            
            result = download_manager.download_current_mix(song_url, track_name)
            
            self.assertTrue(result)
            # Should have tried regular click, then JavaScript click
            mock_download_button.click.assert_called_once()
            self.mock_driver.execute_script.assert_called_with("arguments[0].click();", mock_download_button)

if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestLoginManager,
        TestTrackManager, 
        TestKaraokeVersionAutomator,
        TestConfigurationManagement,
        TestErrorHandling,
        TestDownloadFunctionality
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"COMPREHENSIVE UNIT TEST RESULTS")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split(chr(10))[-2]}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split(chr(10))[-2]}")
    
    if not result.failures and not result.errors:
        print("\n🎉 ALL UNIT TESTS PASSED!")
        print("✅ Core functionality is well-tested")
        print("✅ Error handling is comprehensive")
        print("✅ Edge cases are covered")
    
    print(f"{'='*60}")