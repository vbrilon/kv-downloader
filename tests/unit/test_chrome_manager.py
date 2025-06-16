"""Unit tests for Chrome browser management functionality"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import logging
from pathlib import Path

from packages.browser.chrome_manager import ChromeManager


class TestChromeManager(unittest.TestCase):
    """Test cases for ChromeManager functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.chrome_manager = ChromeManager(headless=True)

    def test_init_headless_mode(self):
        """Test ChromeManager initialization in headless mode"""
        manager = ChromeManager(headless=True)
        self.assertTrue(manager.headless)
        self.assertIsNone(manager.driver)
        self.assertIsNone(manager.wait)

    def test_init_visible_mode(self):
        """Test ChromeManager initialization in visible mode"""
        manager = ChromeManager(headless=False)
        self.assertFalse(manager.headless)
        self.assertIsNone(manager.driver)
        self.assertIsNone(manager.wait)

    @patch('packages.browser.chrome_manager.webdriver.Chrome')
    @patch('packages.browser.chrome_manager.WebDriverWait')
    @patch('packages.browser.chrome_manager.Service')
    def test_setup_driver_success(self, mock_service, mock_wait, mock_chrome):
        """Test successful driver setup"""
        # Mock the Chrome driver and wait objects
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance

        # Mock the service
        mock_service_instance = Mock()
        mock_service.return_value = mock_service_instance

        with patch.object(self.chrome_manager, '_configure_chrome_options') as mock_options, \
             patch.object(self.chrome_manager, '_get_chrome_service') as mock_get_service:
            
            mock_options.return_value = Mock()
            mock_get_service.return_value = mock_service_instance

            # Call the method
            self.chrome_manager.setup_driver()

            # Verify driver and wait were set correctly
            self.assertEqual(self.chrome_manager.driver, mock_driver)
            self.assertEqual(self.chrome_manager.wait, mock_wait_instance)

            # Verify Chrome was called with correct parameters
            mock_chrome.assert_called_once()
            mock_wait.assert_called_once_with(mock_driver, 10)

    @patch('packages.browser.chrome_manager.webdriver.Chrome')
    def test_setup_driver_failure(self, mock_chrome):
        """Test driver setup failure handling"""
        # Mock Chrome to raise an exception
        mock_chrome.side_effect = Exception("Chrome failed to start")

        with patch.object(self.chrome_manager, '_configure_chrome_options') as mock_options, \
             patch.object(self.chrome_manager, '_get_chrome_service') as mock_service, \
             patch.object(self.chrome_manager, '_log_troubleshooting_tips') as mock_tips:
            
            mock_options.return_value = Mock()
            mock_service.return_value = Mock()

            # Should raise the exception
            with self.assertRaises(Exception) as context:
                self.chrome_manager.setup_driver()

            self.assertIn("Chrome failed to start", str(context.exception))
            mock_tips.assert_called_once()

    def test_configure_chrome_options_headless(self):
        """Test Chrome options configuration for headless mode"""
        manager = ChromeManager(headless=True)
        
        with patch('packages.browser.chrome_manager.Options') as mock_options_class:
            mock_options = Mock()
            mock_options_class.return_value = mock_options

            options = manager._configure_chrome_options()

            # Verify headless arguments were added
            mock_options.add_argument.assert_any_call("--headless")
            mock_options.add_argument.assert_any_call("--no-sandbox")
            mock_options.add_argument.assert_any_call("--disable-dev-shm-usage")
            mock_options.add_argument.assert_any_call("--disable-gpu")

    def test_configure_chrome_options_visible(self):
        """Test Chrome options configuration for visible mode"""
        manager = ChromeManager(headless=False)
        
        with patch('packages.browser.chrome_manager.Options') as mock_options_class:
            mock_options = Mock()
            mock_options_class.return_value = mock_options

            options = manager._configure_chrome_options()

            # Verify headless arguments were NOT added
            mock_options.add_argument.assert_any_call("--disable-blink-features=AutomationControlled")
            # Should not have headless argument
            headless_calls = [call for call in mock_options.add_argument.call_args_list 
                            if '--headless' in str(call)]
            self.assertEqual(len(headless_calls), 0)

    @patch('packages.browser.chrome_manager.os.path.exists')
    def test_configure_chrome_options_with_chrome_binary(self, mock_exists):
        """Test Chrome options when Chrome binary exists"""
        mock_exists.return_value = True
        
        with patch('packages.browser.chrome_manager.Options') as mock_options_class:
            mock_options = Mock()
            mock_options_class.return_value = mock_options

            options = self.chrome_manager._configure_chrome_options()

            # Verify binary location was set
            expected_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            self.assertEqual(mock_options.binary_location, expected_path)

    @patch('packages.browser.chrome_manager.os.path.exists')
    def test_get_chrome_service_local_found(self, mock_exists):
        """Test Chrome service when local ChromeDriver is found"""
        # Mock that the first local path exists
        def exists_side_effect(path):
            return path == "/opt/homebrew/bin/chromedriver"
        
        mock_exists.side_effect = exists_side_effect

        with patch('packages.browser.chrome_manager.Service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance

            service = self.chrome_manager._get_chrome_service()

            mock_service.assert_called_once_with("/opt/homebrew/bin/chromedriver")
            self.assertEqual(service, mock_service_instance)

    @patch('packages.browser.chrome_manager.os.path.exists')
    @patch('packages.browser.chrome_manager.ChromeDriverManager')
    def test_get_chrome_service_download_fallback(self, mock_driver_manager, mock_exists):
        """Test Chrome service fallback to webdriver-manager download"""
        mock_exists.return_value = False  # No local ChromeDriver found
        
        mock_manager = Mock()
        mock_manager.install.return_value = "/downloaded/chromedriver"
        mock_driver_manager.return_value = mock_manager

        with patch('packages.browser.chrome_manager.Service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance

            service = self.chrome_manager._get_chrome_service()

            mock_manager.install.assert_called_once()
            mock_service.assert_called_once_with("/downloaded/chromedriver")

    @patch('packages.browser.chrome_manager.os.path.exists')
    @patch('packages.browser.chrome_manager.ChromeDriverManager')
    def test_get_chrome_service_download_failure(self, mock_driver_manager, mock_exists):
        """Test Chrome service when download also fails"""
        mock_exists.return_value = False  # No local ChromeDriver found
        
        mock_manager = Mock()
        mock_manager.install.side_effect = Exception("Download failed")
        mock_driver_manager.return_value = mock_manager

        with self.assertRaises(Exception) as context:
            self.chrome_manager._get_chrome_service()

        self.assertIn("ChromeDriver not available", str(context.exception))

    @patch('packages.browser.chrome_manager.Path')
    def test_setup_folders(self, mock_path):
        """Test folder setup functionality"""
        mock_download_path = Mock()
        mock_logs_path = Mock()
        mock_path.side_effect = [mock_download_path, mock_logs_path]

        self.chrome_manager.setup_folders()

        # Verify both folders were created
        mock_download_path.mkdir.assert_called_once_with(exist_ok=True)
        mock_logs_path.mkdir.assert_called_once_with(exist_ok=True)

    def test_set_download_path_with_driver(self):
        """Test setting download path when driver exists"""
        mock_driver = Mock()
        self.chrome_manager.driver = mock_driver

        test_path = "/test/download/path"
        self.chrome_manager.set_download_path(test_path)

        mock_driver.execute_cdp_cmd.assert_called_once_with(
            'Page.setDownloadBehavior',
            {
                'behavior': 'allow',
                'downloadPath': test_path
            }
        )

    def test_set_download_path_without_driver(self):
        """Test setting download path when no driver exists"""
        self.chrome_manager.driver = None

        # Should not raise an exception
        test_path = "/test/download/path"
        self.chrome_manager.set_download_path(test_path)
        # Just verify no exception was raised

    def test_quit_with_driver(self):
        """Test quitting when driver exists"""
        mock_driver = Mock()
        mock_wait = Mock()
        self.chrome_manager.driver = mock_driver
        self.chrome_manager.wait = mock_wait

        self.chrome_manager.quit()

        mock_driver.quit.assert_called_once()
        self.assertIsNone(self.chrome_manager.driver)
        self.assertIsNone(self.chrome_manager.wait)

    def test_quit_without_driver(self):
        """Test quitting when no driver exists"""
        self.chrome_manager.driver = None
        self.chrome_manager.wait = None

        # Should not raise an exception
        self.chrome_manager.quit()
        self.assertIsNone(self.chrome_manager.driver)
        self.assertIsNone(self.chrome_manager.wait)


if __name__ == '__main__':
    unittest.main()