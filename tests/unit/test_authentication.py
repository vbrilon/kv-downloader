#!/usr/bin/env python3
"""
Unit Tests for Authentication System

Tests the LoginManager class including login flows, session persistence,
logout fallbacks, form field discovery, and cookie management to prevent
regressions in the critical authentication system.
"""

import sys
import pickle
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, call, MagicMock
from unittest import TestCase

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.authentication.login_manager import LoginManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class TestLoginManagerInitialization(TestCase):
    """Test LoginManager initialization and setup"""
    
    def setUp(self):
        """Set up mock driver and wait objects"""
        self.mock_driver = Mock()
        self.mock_wait = Mock()
    
    def test_initialization_with_default_session_file(self):
        """Test LoginManager initializes with default session file path"""
        manager = LoginManager(self.mock_driver, self.mock_wait)
        
        self.assertEqual(manager.driver, self.mock_driver)
        self.assertEqual(manager.wait, self.mock_wait)
        self.assertEqual(str(manager.session_file), ".cache/session_data.pkl")
    
    def test_initialization_with_custom_session_file(self):
        """Test LoginManager initializes with custom session file path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = f"{temp_dir}/session.pkl"
            manager = LoginManager(self.mock_driver, self.mock_wait, custom_path)
            
            self.assertEqual(str(manager.session_file), custom_path)
    
    @patch('pathlib.Path.mkdir')
    def test_initialization_creates_session_directory(self, mock_mkdir):
        """Test LoginManager creates session directory on initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_file = f"{temp_dir}/cache/session.pkl"
            LoginManager(self.mock_driver, self.mock_wait, session_file)
            
            # Verify directory creation was attempted
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestLoginStatusChecking(TestCase):
    """Test login status detection methods"""
    
    def setUp(self):
        """Set up LoginManager with mock dependencies"""
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.manager = LoginManager(self.mock_driver, self.mock_wait)
    
    def test_is_logged_in_finds_my_account(self):
        """Test login detection via 'My Account' element"""
        # Mock finding 'My Account' element
        mock_element = Mock()
        self.mock_driver.find_elements.return_value = [mock_element]
        
        result = self.manager.is_logged_in()
        
        self.assertTrue(result)
        self.mock_driver.find_elements.assert_called_with(
            By.XPATH, "//*[contains(text(), 'My Account')]"
        )
    
    def test_is_logged_in_no_login_links_fallback(self):
        """Test login detection via absence of login links"""
        # Mock no 'My Account' but also no login links
        self.mock_driver.find_elements.side_effect = [
            [],  # No 'My Account' elements
            []   # No login links
        ]
        
        result = self.manager.is_logged_in()
        
        self.assertTrue(result)
        
        # Verify both checks were made
        expected_calls = [
            call(By.XPATH, "//*[contains(text(), 'My Account')]"),
            call(By.XPATH, "//a[contains(text(), 'Log in')]")
        ]
        self.mock_driver.find_elements.assert_has_calls(expected_calls)
    
    def test_is_logged_in_login_links_present(self):
        """Test login detection when login links are present (not logged in)"""
        # Mock no 'My Account' but login links present
        mock_login_link = Mock()
        self.mock_driver.find_elements.side_effect = [
            [],  # No 'My Account' elements
            [mock_login_link]  # Login links present
        ]
        
        result = self.manager.is_logged_in()
        
        self.assertFalse(result)
    
    @patch('packages.authentication.login_manager.logging.info')
    def test_is_logged_in_logging_behavior(self, mock_log):
        """Test is_logged_in logs appropriate messages"""
        # Test logged in scenario
        mock_element = Mock()
        self.mock_driver.find_elements.return_value = [mock_element]
        
        self.manager.is_logged_in()
        
        mock_log.assert_called_with("✅ User is logged in: Found 'My Account' in header")


class TestLogoutFunctionality(TestCase):
    """Test logout methods and fallback strategies"""
    
    def setUp(self):
        """Set up LoginManager with mock dependencies"""
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.manager = LoginManager(self.mock_driver, self.mock_wait)
    
    @patch.object(LoginManager, '_attempt_direct_logout')
    @patch.object(LoginManager, '_fallback_cookie_logout')
    def test_logout_direct_success(self, mock_cookie_logout, mock_direct_logout):
        """Test logout succeeds with direct logout"""
        mock_direct_logout.return_value = True
        
        result = self.manager.logout()
        
        self.assertTrue(result)
        mock_direct_logout.assert_called_once()
        mock_cookie_logout.assert_not_called()
    
    @patch.object(LoginManager, '_attempt_direct_logout')
    @patch.object(LoginManager, '_fallback_cookie_logout')
    def test_logout_fallback_to_cookies(self, mock_cookie_logout, mock_direct_logout):
        """Test logout falls back to cookie logout when direct fails"""
        mock_direct_logout.return_value = False
        mock_cookie_logout.return_value = True
        
        result = self.manager.logout()
        
        self.assertTrue(result)
        mock_direct_logout.assert_called_once()
        mock_cookie_logout.assert_called_once()
    
    def test_attempt_direct_logout_finds_logout_link(self):
        """Test direct logout finds and clicks logout link"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_element.text = "Log out"
        
        self.mock_driver.find_element.return_value = mock_element
        
        with patch.object(self.manager, '_direct_logout_click', return_value=True):
            result = self.manager._attempt_direct_logout()
            
            self.assertTrue(result)
    
    def test_attempt_direct_logout_handles_my_account_menu(self):
        """Test direct logout handles 'My Account' menu navigation"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_element.text = "My Account"
        
        self.mock_driver.find_element.return_value = mock_element
        
        with patch.object(self.manager, '_logout_via_account_menu', return_value=True) as mock_account_menu:
            result = self.manager._attempt_direct_logout()
            
            self.assertTrue(result)
            mock_account_menu.assert_called_once_with(mock_element)
    
    def test_attempt_direct_logout_no_elements_found(self):
        """Test direct logout when no logout elements are found"""
        self.mock_driver.find_element.side_effect = NoSuchElementException("Not found")
        
        result = self.manager._attempt_direct_logout()
        
        # Should return None (falsy) when no elements found
        self.assertIsNone(result)


class TestFormFieldDiscovery(TestCase):
    """Test form field discovery and filling logic"""
    
    def setUp(self):
        """Set up LoginManager with mock dependencies"""
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.manager = LoginManager(self.mock_driver, self.mock_wait)
    
    def test_find_username_field_by_name(self):
        """Test finding username field by name attribute"""
        mock_field = Mock()
        self.mock_wait.until.return_value = mock_field
        
        result = self.manager._find_username_field()
        
        self.assertEqual(result, mock_field)
        self.mock_wait.until.assert_called_once()
    
    def test_find_password_field_by_name(self):
        """Test finding password field by name attribute"""
        mock_field = Mock()
        self.mock_wait.until.return_value = mock_field
        
        result = self.manager._find_password_field()
        
        self.assertEqual(result, mock_field)
        self.mock_wait.until.assert_called_once()
    
    def test_find_submit_button_multiple_selectors(self):
        """Test finding submit button tries multiple selectors"""
        mock_button = Mock()
        
        # Mock first selector fails, second succeeds
        self.mock_driver.find_element.side_effect = [
            NoSuchElementException("First not found"),
            mock_button
        ]
        
        result = self.manager._find_submit_button()
        
        self.assertEqual(result, mock_button)
        self.assertEqual(self.mock_driver.find_element.call_count, 2)
    
    def test_find_submit_button_no_button_found(self):
        """Test submit button search when no button exists"""
        self.mock_driver.find_element.side_effect = NoSuchElementException("Not found")
        
        result = self.manager._find_submit_button()
        
        self.assertIsNone(result)
    
    def test_fill_credentials(self):
        """Test filling username and password fields"""
        mock_username_field = Mock()
        mock_password_field = Mock()
        
        self.manager._fill_credentials(
            mock_username_field, "test_user",
            mock_password_field, "test_pass"
        )
        
        # Verify fields are cleared and filled
        mock_username_field.clear.assert_called_once()
        mock_username_field.send_keys.assert_called_once_with("test_user")
        mock_password_field.clear.assert_called_once()
        mock_password_field.send_keys.assert_called_once_with("test_pass")


class TestLoginFlow(TestCase):
    """Test complete login workflow"""
    
    def setUp(self):
        """Set up LoginManager with mock dependencies"""
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.manager = LoginManager(self.mock_driver, self.mock_wait)
    
    @patch.object(LoginManager, 'is_logged_in')
    @patch.object(LoginManager, 'load_session')
    @patch.object(LoginManager, 'save_session')
    def test_login_already_logged_in(self, mock_save, mock_load, mock_is_logged_in):
        """Test login when already logged in"""
        mock_is_logged_in.return_value = True
        mock_load.return_value = True
        
        result = self.manager.login("user", "pass")
        
        self.assertTrue(result)
        mock_save.assert_called_once()  # Should save session even if already logged in
    
    @patch.object(LoginManager, 'is_logged_in')
    @patch.object(LoginManager, 'load_session')
    @patch.object(LoginManager, 'click_login_link')
    @patch.object(LoginManager, 'fill_login_form')
    def test_login_success_flow(self, mock_fill_form, mock_click_link, mock_load, mock_is_logged_in):
        """Test successful login flow"""
        # Not logged in initially, then logged in after form submission
        mock_is_logged_in.side_effect = [False, True]
        mock_load.return_value = False
        mock_click_link.return_value = True
        mock_fill_form.return_value = True
        
        with patch.object(self.manager, 'save_session'):
            result = self.manager.login("user", "pass")
            
            self.assertTrue(result)
            mock_click_link.assert_called_once()
            mock_fill_form.assert_called_once_with("user", "pass")
    
    @patch.object(LoginManager, 'is_logged_in')
    @patch.object(LoginManager, 'load_session')
    @patch.object(LoginManager, 'click_login_link')
    def test_login_click_link_failure(self, mock_click_link, mock_load, mock_is_logged_in):
        """Test login failure when clicking login link fails"""
        mock_is_logged_in.return_value = False
        mock_load.return_value = False
        mock_click_link.return_value = False
        
        result = self.manager.login("user", "pass")
        
        self.assertFalse(result)
    
    @patch.object(LoginManager, 'is_logged_in')
    @patch.object(LoginManager, 'load_session')
    def test_login_force_relogin(self, mock_load, mock_is_logged_in):
        """Test force relogin ignores existing session"""
        mock_is_logged_in.return_value = True
        
        with patch.object(self.manager, 'click_login_link', return_value=True):
            with patch.object(self.manager, 'fill_login_form', return_value=True):
                with patch.object(self.manager, 'save_session'):
                    result = self.manager.login("user", "pass", force_relogin=True)
                    
                    self.assertTrue(result)
                    mock_load.assert_not_called()  # Should not load session when forcing relogin


class TestSessionPersistence(TestCase):
    """Test session saving and loading functionality"""
    
    def setUp(self):
        """Set up LoginManager with temporary session file"""
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.temp_dir = tempfile.mkdtemp()
        self.session_file = Path(self.temp_dir) / "test_session.pkl"
        self.manager = LoginManager(self.mock_driver, self.mock_wait, str(self.session_file))
    
    def tearDown(self):
        """Clean up temporary files"""
        if self.session_file.exists():
            self.session_file.unlink()
        Path(self.temp_dir).rmdir()
    
    def test_save_session_creates_file(self):
        """Test save_session creates session file with cookies"""
        # Use simple dict data that can be pickled, not Mock objects
        simple_cookies = [
            {"name": "session_id", "value": "abc123"},
            {"name": "user_pref", "value": "dark_mode"}
        ]
        self.mock_driver.get_cookies.return_value = simple_cookies
        
        result = self.manager.save_session()
        
        self.assertTrue(result)
        self.assertTrue(self.session_file.exists())
        
        # Verify session data was saved
        with open(self.session_file, 'rb') as f:
            saved_data = pickle.load(f)
            
        self.assertIn('cookies', saved_data)
        self.assertIn('timestamp', saved_data)
        self.assertEqual(saved_data['cookies'], simple_cookies)
    
    @patch('packages.authentication.login_manager.logging.info')
    def test_save_session_logging(self, mock_log):
        """Test save_session logs success message"""
        self.mock_driver.get_cookies.return_value = []
        
        self.manager.save_session()
        
        mock_log.assert_called_with(f"💾 Session saved to {self.session_file}")
    
    def test_load_session_file_not_exists(self):
        """Test load_session when session file doesn't exist"""
        result = self.manager.load_session()
        
        self.assertFalse(result)
    
    def test_load_session_success(self):
        """Test successful session loading"""
        # Create a session file
        import time
        session_data = {
            'cookies': [{"name": "test", "value": "123"}],
            'timestamp': time.time()
        }
        
        with open(self.session_file, 'wb') as f:
            pickle.dump(session_data, f)
        
        result = self.manager.load_session()
        
        self.assertTrue(result)
        self.mock_driver.delete_all_cookies.assert_called_once()
        self.mock_driver.add_cookie.assert_called_once_with({"name": "test", "value": "123"})
    
    def test_load_session_expired(self):
        """Test loading expired session (older than 24 hours)"""
        import time
        
        # Create expired session (25 hours old)
        old_timestamp = time.time() - (25 * 60 * 60)
        session_data = {
            'cookies': [{"name": "test", "value": "123"}],
            'timestamp': old_timestamp
        }
        
        with open(self.session_file, 'wb') as f:
            pickle.dump(session_data, f)
        
        result = self.manager.load_session()
        
        self.assertFalse(result)
        # Expired session file should be removed
        self.assertFalse(self.session_file.exists())
    
    @patch('packages.authentication.login_manager.logging.error')
    def test_load_session_corrupted_file(self, mock_log_error):
        """Test loading corrupted session file"""
        # Create corrupted file
        with open(self.session_file, 'w') as f:
            f.write("corrupted data")
        
        result = self.manager.load_session()
        
        self.assertFalse(result)
        mock_log_error.assert_called_once()
        # Corrupted file should be removed
        self.assertFalse(self.session_file.exists())


class TestCookieManagement(TestCase):
    """Test cookie-based logout and management"""
    
    def setUp(self):
        """Set up LoginManager with mock dependencies"""
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.manager = LoginManager(self.mock_driver, self.mock_wait)
    
    @patch.object(LoginManager, '_emergency_cookie_fallback')
    def test_fallback_cookie_logout(self, mock_emergency):
        """Test fallback cookie logout clears cookies"""
        mock_emergency.return_value = True
        
        result = self.manager._fallback_cookie_logout()
        
        self.assertTrue(result)
        self.mock_driver.delete_all_cookies.assert_called_once()
        mock_emergency.assert_called_once()
    
    def test_emergency_cookie_fallback_refresh_check(self):
        """Test emergency cookie fallback refreshes and checks login status"""
        with patch.object(self.manager, 'is_logged_in', return_value=False) as mock_is_logged_in:
            result = self.manager._emergency_cookie_fallback()
            
            self.assertTrue(result)
            self.mock_driver.refresh.assert_called_once()
            mock_is_logged_in.assert_called_once()


class TestLoginFormInteraction(TestCase):
    """Test login form interaction and submission"""
    
    def setUp(self):
        """Set up LoginManager with mock dependencies"""
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.manager = LoginManager(self.mock_driver, self.mock_wait)
    
    @patch('packages.authentication.login_manager.logging.info')
    def test_click_login_link_success(self, mock_log):
        """Test successful login link clicking"""
        mock_element = Mock()
        mock_element.text = "Log in"
        mock_element.is_displayed.return_value = True
        self.mock_driver.find_element.return_value = mock_element
        
        result = self.manager.click_login_link()
        
        self.assertTrue(result)
        mock_element.click.assert_called_once()
        # Check that log message contains the element text
        mock_log.assert_called_with("Clicking login link: 'Log in'")
    
    def test_click_login_link_not_found(self):
        """Test login link clicking when element not found"""
        self.mock_driver.find_element.side_effect = NoSuchElementException("Not found")
        
        result = self.manager.click_login_link()
        
        self.assertFalse(result)
    
    def test_fill_login_form_success(self):
        """Test successful login form filling"""
        mock_username_field = Mock()
        mock_password_field = Mock()
        mock_submit_button = Mock()
        
        with patch.object(self.manager, '_find_username_field', return_value=mock_username_field):
            with patch.object(self.manager, '_find_password_field', return_value=mock_password_field):
                with patch.object(self.manager, '_find_submit_button', return_value=mock_submit_button):
                    with patch.object(self.manager, '_submit_form', return_value=True):
                        result = self.manager.fill_login_form("user", "pass")
                        
                        self.assertTrue(result)
    
    def test_fill_login_form_missing_username_field(self):
        """Test login form filling when username field is missing"""
        with patch.object(self.manager, '_find_username_field', return_value=None):
            result = self.manager.fill_login_form("user", "pass")
            
            self.assertFalse(result)
    
    def test_fill_login_form_missing_password_field(self):
        """Test login form filling when password field is missing"""
        mock_username_field = Mock()
        
        with patch.object(self.manager, '_find_username_field', return_value=mock_username_field):
            with patch.object(self.manager, '_find_password_field', return_value=None):
                result = self.manager.fill_login_form("user", "pass")
                
                self.assertFalse(result)


class TestAuthenticationIntegration(TestCase):
    """Integration tests for authentication system"""
    
    def setUp(self):
        """Set up LoginManager with mock dependencies"""
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.temp_dir = tempfile.mkdtemp()
        self.session_file = Path(self.temp_dir) / "integration_session.pkl"
        self.manager = LoginManager(self.mock_driver, self.mock_wait, str(self.session_file))
    
    def tearDown(self):
        """Clean up temporary files"""
        if self.session_file.exists():
            self.session_file.unlink()
        Path(self.temp_dir).rmdir()
    
    def test_complete_login_logout_cycle(self):
        """Test complete login followed by logout"""
        # Mock successful login
        with patch.object(self.manager, 'is_logged_in', side_effect=[False, True, False]):
            with patch.object(self.manager, 'load_session', return_value=False):
                with patch.object(self.manager, 'click_login_link', return_value=True):
                    with patch.object(self.manager, 'fill_login_form', return_value=True):
                        # Login
                        login_result = self.manager.login("user", "pass")
                        self.assertTrue(login_result)
                        
                        # Logout
                        with patch.object(self.manager, '_attempt_direct_logout', return_value=True):
                            logout_result = self.manager.logout()
                            self.assertTrue(logout_result)
    
    def test_session_persistence_across_instances(self):
        """Test session persists across LoginManager instances"""
        # First instance saves session
        simple_cookies = [{"name": "test_session", "value": "abc123"}]
        self.mock_driver.get_cookies.return_value = simple_cookies
        
        self.manager.save_session()
        
        # Second instance loads session
        mock_driver2 = Mock()
        manager2 = LoginManager(mock_driver2, Mock(), str(self.session_file))
        
        result = manager2.load_session()
        
        self.assertTrue(result)
        mock_driver2.delete_all_cookies.assert_called_once()
        mock_driver2.add_cookie.assert_called_once_with({"name": "test_session", "value": "abc123"})


if __name__ == "__main__":
    import unittest
    unittest.main()