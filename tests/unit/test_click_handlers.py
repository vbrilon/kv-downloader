#!/usr/bin/env python3
"""
Unit Tests for Click Handlers

Tests click handling utilities including performance optimizations that replaced
hardcoded sleeps with WebDriverWait patterns to prevent regressions.
"""

import sys
import logging
from pathlib import Path
from unittest.mock import Mock, patch, call, MagicMock
from unittest import TestCase

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.utils.click_handlers import safe_click, safe_click_with_scroll
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
    WebDriverException
)


class TestSafeClick(TestCase):
    """Test safe_click function behavior"""
    
    def setUp(self):
        """Set up mock objects for tests"""
        self.mock_driver = Mock()
        self.mock_element = Mock()
        self.mock_element.click = Mock()
        
    @patch('packages.utils.click_handlers.logging.debug')
    def test_safe_click_success(self, mock_log_debug):
        """Test successful regular click"""
        # Setup
        self.mock_element.click.return_value = None
        
        # Execute
        result = safe_click(self.mock_driver, self.mock_element, "test button")
        
        # Verify
        self.assertTrue(result)
        self.mock_element.click.assert_called_once()
        mock_log_debug.assert_called_once_with("✅ test button clicked successfully")
    
    @patch('packages.utils.click_handlers.logging.error')
    @patch('packages.utils.click_handlers.logging.debug')
    @patch('packages.utils.click_handlers.logging.info')
    def test_safe_click_intercepted_javascript_success(self, mock_log_info, mock_log_debug, mock_log_error):
        """Test click interception with successful JavaScript fallback"""
        # Setup - Use Exception with intercepted text (how the actual code detects interception)
        self.mock_element.click.side_effect = Exception("element click intercepted: some details")
        self.mock_driver.execute_script.return_value = None
        
        # Execute
        result = safe_click(self.mock_driver, self.mock_element, "intercepted button")
        
        # Verify
        self.assertTrue(result)
        self.mock_element.click.assert_called_once()
        self.mock_driver.execute_script.assert_called_once_with("arguments[0].click();", self.mock_element)
        
        # Check logging
        mock_log_info.assert_called_once_with("Click intercepted on intercepted button, using JavaScript click")
        mock_log_debug.assert_called_once_with("✅ intercepted button clicked via JavaScript")
        mock_log_error.assert_not_called()
    
    @patch('packages.utils.click_handlers.logging.error')
    @patch('packages.utils.click_handlers.logging.info')
    def test_safe_click_intercepted_javascript_failure(self, mock_log_info, mock_log_error):
        """Test click interception with JavaScript fallback failure"""
        # Setup
        self.mock_element.click.side_effect = Exception("element click intercepted: some details")
        self.mock_driver.execute_script.side_effect = WebDriverException("JS execution failed")
        
        # Execute
        result = safe_click(self.mock_driver, self.mock_element, "failed button")
        
        # Verify
        self.assertFalse(result)
        self.mock_element.click.assert_called_once()
        self.mock_driver.execute_script.assert_called_once()
        
        # Check logging
        mock_log_info.assert_called_once_with("Click intercepted on failed button, using JavaScript click")
        # Check that error message contains the WebDriverException details (may have Message: prefix)
        mock_log_error.assert_called_once()
        error_call_args = mock_log_error.call_args[0][0]
        self.assertIn("JavaScript click also failed on failed button:", error_call_args)
        self.assertIn("JS execution failed", error_call_args)
    
    @patch('packages.utils.click_handlers.logging.error')
    @patch('packages.utils.click_handlers.logging.info')
    def test_safe_click_intercepted_generic_exception_message(self, mock_log_info, mock_log_error):
        """Test click interception detection with generic exception containing intercepted text"""
        # Setup - Generic exception with "element click intercepted" in message
        generic_exception = Exception("element click intercepted: some details")
        self.mock_element.click.side_effect = generic_exception
        self.mock_driver.execute_script.return_value = None
        
        # Execute
        result = safe_click(self.mock_driver, self.mock_element, "generic intercepted")
        
        # Verify
        self.assertTrue(result)
        mock_log_info.assert_called_once_with("Click intercepted on generic intercepted, using JavaScript click")
    
    def test_safe_click_non_interception_exception_reraise(self):
        """Test non-interception exceptions are re-raised"""
        # Setup
        self.mock_element.click.side_effect = WebDriverException("Non-interception error")
        
        # Execute & Verify
        with self.assertRaises(WebDriverException) as context:
            safe_click(self.mock_driver, self.mock_element, "error button")
        
        # WebDriverException may have "Message: " prefix
        self.assertIn("Non-interception error", str(context.exception))
        self.mock_element.click.assert_called_once()
        self.mock_driver.execute_script.assert_not_called()
    
    @patch('packages.utils.click_handlers.logging.debug')
    def test_safe_click_default_element_description(self, mock_log_debug):
        """Test default element description when none provided"""
        # Setup
        self.mock_element.click.return_value = None
        
        # Execute
        result = safe_click(self.mock_driver, self.mock_element)
        
        # Verify
        self.assertTrue(result)
        mock_log_debug.assert_called_once_with("✅ element clicked successfully")
    
    def test_safe_click_preserves_driver_and_element_references(self):
        """Test function uses the exact driver and element objects passed"""
        # Setup
        specific_driver = Mock()
        specific_element = Mock()
        specific_element.click.return_value = None
        
        # Execute
        safe_click(specific_driver, specific_element)
        
        # Verify exact objects were used
        specific_element.click.assert_called_once()


class TestSafeClickWithScroll(TestCase):
    """Test safe_click_with_scroll function behavior and performance optimizations"""
    
    def setUp(self):
        """Set up mock objects for tests"""
        self.mock_driver = Mock()
        self.mock_element = Mock()
        self.mock_element.click = Mock()
        
        # Mock WebDriverWait and expected conditions
        self.mock_wait = Mock()
        self.mock_wait.until = Mock()
        
    @patch('packages.utils.click_handlers.safe_click')
    @patch('packages.utils.click_handlers.WebDriverWait')
    @patch('packages.utils.click_handlers.EC.element_to_be_clickable')
    @patch('packages.utils.click_handlers.logging.debug')
    def test_safe_click_with_scroll_success(self, mock_log_debug, mock_clickable, mock_webdriver_wait, mock_safe_click):
        """Test successful scroll and click with WebDriverWait optimization"""
        # Setup
        mock_webdriver_wait.return_value.until.return_value = True
        mock_safe_click.return_value = True
        
        # Execute
        result = safe_click_with_scroll(self.mock_driver, self.mock_element, "scroll button")
        
        # Verify
        self.assertTrue(result)
        
        # Check scroll script execution
        self.mock_driver.execute_script.assert_called_with(
            "arguments[0].scrollIntoView({block: 'center'});", 
            self.mock_element
        )
        
        # Check WebDriverWait was used (performance optimization)
        mock_webdriver_wait.assert_called_once()
        mock_webdriver_wait.return_value.until.assert_called_once()
        mock_clickable.assert_called_once_with(self.mock_element)
        
        # Check safe_click was called
        mock_safe_click.assert_called_once_with(self.mock_driver, self.mock_element, "scroll button")
        
        # Check logging
        expected_log_calls = [
            call("Scrolled scroll button into view"),
            call("scroll button is clickable after scroll")
        ]
        mock_log_debug.assert_has_calls(expected_log_calls)
    
    @patch('packages.utils.click_handlers.safe_click')
    @patch('packages.utils.click_handlers.WebDriverWait')
    @patch('packages.utils.click_handlers.EC.element_to_be_clickable')
    @patch('packages.utils.click_handlers.logging.debug')
    def test_safe_click_with_scroll_webdriver_wait_timeout(self, mock_log_debug, mock_clickable, mock_webdriver_wait, mock_safe_click):
        """Test WebDriverWait timeout handling - should proceed with click attempt"""
        # Setup
        mock_webdriver_wait.return_value.until.side_effect = TimeoutException("Timeout waiting for clickable")
        mock_safe_click.return_value = True
        
        # Execute
        result = safe_click_with_scroll(self.mock_driver, self.mock_element, "timeout button")
        
        # Verify
        self.assertTrue(result)
        
        # Check that safe_click was still called despite timeout
        mock_safe_click.assert_called_once_with(self.mock_driver, self.mock_element, "timeout button")
        
        # Check timeout logging
        timeout_log_call = call("timeout button clickable timeout - proceeding with click attempt")
        mock_log_debug.assert_any_call(timeout_log_call.args[0])
    
    @patch('packages.utils.click_handlers.safe_click')
    @patch('packages.utils.click_handlers.WebDriverWait')
    @patch('packages.utils.click_handlers.logging.debug')
    def test_safe_click_with_scroll_uses_correct_timeout(self, mock_log_debug, mock_webdriver_wait, mock_safe_click):
        """Test WebDriverWait uses WEBDRIVER_BRIEF_TIMEOUT configuration"""
        # Setup
        mock_webdriver_wait.return_value.until.return_value = True
        mock_safe_click.return_value = True
        
        # Execute
        safe_click_with_scroll(self.mock_driver, self.mock_element)
        
        # Verify timeout value from config is used
        from packages.configuration.config import WEBDRIVER_BRIEF_TIMEOUT
        mock_webdriver_wait.assert_called_once_with(self.mock_driver, WEBDRIVER_BRIEF_TIMEOUT)
    
    @patch('packages.utils.click_handlers.safe_click')
    @patch('packages.utils.click_handlers.logging.error')
    def test_safe_click_with_scroll_scroll_failure(self, mock_log_error, mock_safe_click):
        """Test scroll failure exception handling"""
        # Setup
        self.mock_driver.execute_script.side_effect = WebDriverException("Scroll failed")
        
        # Execute & Verify
        with self.assertRaises(WebDriverException) as context:
            safe_click_with_scroll(self.mock_driver, self.mock_element, "scroll fail button")
        
        # WebDriverException may have "Message: " prefix
        self.assertIn("Scroll failed", str(context.exception))
        
        # Check error logging - also may have Message: prefix in logged exception
        mock_log_error.assert_called_once()
        error_call_args = mock_log_error.call_args[0][0]
        self.assertIn("Failed to scroll and click scroll fail button:", error_call_args)
        self.assertIn("Scroll failed", error_call_args)
        
        # safe_click should not be called if scroll fails
        mock_safe_click.assert_not_called()
    
    @patch('packages.utils.click_handlers.safe_click')
    @patch('packages.utils.click_handlers.WebDriverWait')
    @patch('packages.utils.click_handlers.logging.debug')
    def test_safe_click_with_scroll_default_element_description(self, mock_log_debug, mock_webdriver_wait, mock_safe_click):
        """Test default element description handling"""
        # Setup
        mock_webdriver_wait.return_value.until.return_value = True
        mock_safe_click.return_value = True
        
        # Execute
        result = safe_click_with_scroll(self.mock_driver, self.mock_element)
        
        # Verify
        self.assertTrue(result)
        mock_safe_click.assert_called_once_with(self.mock_driver, self.mock_element, "element")
    
    @patch('packages.utils.click_handlers.safe_click')
    @patch('packages.utils.click_handlers.WebDriverWait')
    def test_safe_click_with_scroll_propagates_safe_click_result(self, mock_webdriver_wait, mock_safe_click):
        """Test that safe_click_with_scroll returns the result from safe_click"""
        # Setup
        mock_webdriver_wait.return_value.until.return_value = True
        mock_safe_click.return_value = False  # safe_click fails
        
        # Execute
        result = safe_click_with_scroll(self.mock_driver, self.mock_element)
        
        # Verify
        self.assertFalse(result)  # Should propagate False from safe_click


class TestClickHandlersIntegration(TestCase):
    """Integration tests for click handler functions"""
    
    def setUp(self):
        """Set up realistic mock objects for integration tests"""
        self.mock_driver = Mock()
        self.mock_element = Mock()
        
    @patch('packages.utils.click_handlers.WebDriverWait')
    @patch('packages.utils.click_handlers.logging.debug')
    @patch('packages.utils.click_handlers.logging.info')
    def test_full_scroll_click_intercepted_flow(self, mock_log_info, mock_log_debug, mock_webdriver_wait):
        """Test complete flow: scroll -> wait -> click intercepted -> JS fallback"""
        # Setup
        mock_webdriver_wait.return_value.until.return_value = True
        self.mock_element.click.side_effect = Exception("element click intercepted: some details")
        
        # Execute
        result = safe_click_with_scroll(self.mock_driver, self.mock_element, "complex button")
        
        # Verify
        self.assertTrue(result)
        
        # Check complete flow was executed
        # 1. Scroll
        self.mock_driver.execute_script.assert_any_call(
            "arguments[0].scrollIntoView({block: 'center'});", 
            self.mock_element
        )
        
        # 2. WebDriverWait
        mock_webdriver_wait.assert_called_once()
        
        # 3. Regular click attempt
        self.mock_element.click.assert_called_once()
        
        # 4. JavaScript fallback
        self.mock_driver.execute_script.assert_any_call("arguments[0].click();", self.mock_element)
        
        # Check logging flow
        mock_log_info.assert_called_once_with("Click intercepted on complex button, using JavaScript click")
    
    @patch('packages.utils.click_handlers.WebDriverWait')
    def test_performance_optimization_webdriver_wait_replaces_sleep(self, mock_webdriver_wait):
        """Test that WebDriverWait is used instead of time.sleep for performance"""
        # Setup
        mock_webdriver_wait.return_value.until.return_value = True
        self.mock_element.click.return_value = None
        
        # Execute
        result = safe_click_with_scroll(self.mock_driver, self.mock_element)
        
        # Verify
        self.assertTrue(result)
        
        # Critical: Verify WebDriverWait was used (performance optimization)
        mock_webdriver_wait.assert_called_once()
        
        # Verify no time.sleep was used (this is the performance improvement)
        with patch('time.sleep') as mock_sleep:
            # Re-run to ensure no sleep is called
            safe_click_with_scroll(self.mock_driver, self.mock_element)
            mock_sleep.assert_not_called()


class TestClickHandlersConfiguration(TestCase):
    """Test click handlers use correct configuration values"""
    
    @patch('packages.utils.click_handlers.WebDriverWait')
    @patch('packages.utils.click_handlers.safe_click')
    def test_webdriver_brief_timeout_configuration(self, mock_safe_click, mock_webdriver_wait):
        """Test that WEBDRIVER_BRIEF_TIMEOUT is correctly imported and used"""
        # Setup
        mock_webdriver_wait.return_value.until.return_value = True
        mock_safe_click.return_value = True
        mock_driver = Mock()
        mock_element = Mock()
        
        # Execute
        safe_click_with_scroll(mock_driver, mock_element)
        
        # Verify correct timeout is used
        from packages.configuration.config import WEBDRIVER_BRIEF_TIMEOUT
        mock_webdriver_wait.assert_called_once_with(mock_driver, WEBDRIVER_BRIEF_TIMEOUT)
    
    def test_configuration_import_accessibility(self):
        """Test that required configuration constants are accessible"""
        # This ensures configuration imports don't break
        from packages.configuration.config import WEBDRIVER_BRIEF_TIMEOUT, CLICK_HANDLER_DELAY
        
        # Verify they are numeric values
        self.assertTrue(isinstance(WEBDRIVER_BRIEF_TIMEOUT, (int, float)))
        self.assertTrue(isinstance(CLICK_HANDLER_DELAY, (int, float)))
        
        # Verify reasonable timeout values
        self.assertGreater(WEBDRIVER_BRIEF_TIMEOUT, 0)
        self.assertLess(WEBDRIVER_BRIEF_TIMEOUT, 10)  # Should be brief


if __name__ == "__main__":
    # Setup basic logging for tests
    logging.basicConfig(level=logging.WARNING)
    
    import unittest
    unittest.main()