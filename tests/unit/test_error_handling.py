#!/usr/bin/env python3
"""
Unit Tests for Error Handling Decorators and Utilities

Tests all error handling decorators and the ErrorContext context manager
to prevent regressions in error handling logic across the codebase.
"""

import sys
import time
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, call
from unittest import TestCase

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.utils.error_handling import (
    selenium_safe,
    validation_safe, 
    file_operation_safe,
    retry_on_failure,
    ErrorContext
)
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
    WebDriverException
)


class TestSeleniumSafeDecorator(TestCase):
    """Test selenium_safe decorator behavior"""
    
    def setUp(self):
        self.log_mock = Mock()
        
    @patch('packages.utils.error_handling.logging.error')
    def test_selenium_safe_success_case(self, mock_log_error):
        """Test decorator allows successful execution"""
        
        @selenium_safe()
        def successful_function():
            return "success"
        
        result = successful_function()
        self.assertEqual(result, "success")
        mock_log_error.assert_not_called()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_selenium_safe_timeout_exception(self, mock_log_error):
        """Test decorator handles TimeoutException"""
        
        @selenium_safe(return_value="timeout_handled")
        def timeout_function():
            raise TimeoutException("Test timeout")
        
        result = timeout_function()
        self.assertEqual(result, "timeout_handled")
        mock_log_error.assert_called_once()
        
    @patch('packages.utils.error_handling.logging.error')
    def test_selenium_safe_no_such_element(self, mock_log_error):
        """Test decorator handles NoSuchElementException"""
        
        @selenium_safe(return_value=False)
        def missing_element_function():
            raise NoSuchElementException("Element not found")
        
        result = missing_element_function()
        self.assertEqual(result, False)
        mock_log_error.assert_called_once()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_selenium_safe_element_click_intercepted(self, mock_log_error):
        """Test decorator handles ElementClickInterceptedException"""
        
        @selenium_safe(return_value=None)
        def click_intercepted_function():
            raise ElementClickInterceptedException("Click intercepted")
        
        result = click_intercepted_function()
        self.assertIsNone(result)
        mock_log_error.assert_called_once()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_selenium_safe_webdriver_exception(self, mock_log_error):
        """Test decorator handles WebDriverException"""
        
        @selenium_safe(return_value="webdriver_error")
        def webdriver_error_function():
            raise WebDriverException("WebDriver error")
        
        result = webdriver_error_function()
        self.assertEqual(result, "webdriver_error")
        mock_log_error.assert_called_once()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_selenium_safe_generic_exception(self, mock_log_error):
        """Test decorator handles generic Exception"""
        
        @selenium_safe(return_value="generic_handled")
        def generic_error_function():
            raise ValueError("Generic error")
        
        result = generic_error_function()
        self.assertEqual(result, "generic_handled")
        mock_log_error.assert_called_once()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_selenium_safe_custom_operation_name(self, mock_log_error):
        """Test decorator uses custom operation name in logs"""
        
        @selenium_safe(operation_name="custom_operation")
        def test_function():
            raise TimeoutException("Test error")
        
        test_function()
        
        # Check that custom operation name is used in log message
        args, kwargs = mock_log_error.call_args
        self.assertIn("custom_operation", args[0])
    
    @patch('packages.utils.error_handling.logging.error')
    def test_selenium_safe_log_disabled(self, mock_log_error):
        """Test decorator respects log_error=False"""
        
        @selenium_safe(log_error=False)
        def no_log_function():
            raise TimeoutException("Test error")
        
        no_log_function()
        mock_log_error.assert_not_called()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_selenium_safe_custom_exceptions(self, mock_log_error):
        """Test decorator handles custom exception types"""
        
        class CustomError(Exception):
            pass
        
        @selenium_safe(suppress_exceptions=(CustomError,))
        def custom_error_function():
            raise CustomError("Custom error")
        
        result = custom_error_function()
        self.assertIsNone(result)
        mock_log_error.assert_called_once()
    
    def test_selenium_safe_preserves_function_metadata(self):
        """Test decorator preserves original function metadata"""
        
        @selenium_safe()
        def test_function():
            """Test docstring"""
            pass
        
        self.assertEqual(test_function.__name__, "test_function")
        self.assertEqual(test_function.__doc__, "Test docstring")


class TestValidationSafeDecorator(TestCase):
    """Test validation_safe decorator behavior"""
    
    @patch('packages.utils.error_handling.logging.error')
    def test_validation_safe_success_returns_true(self, mock_log_error):
        """Test validation function returns True on success"""
        
        @validation_safe()
        def valid_function():
            return True
        
        result = valid_function()
        self.assertTrue(result)
        mock_log_error.assert_not_called()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_validation_safe_exception_returns_false(self, mock_log_error):
        """Test validation function returns False on exception"""
        
        @validation_safe()
        def invalid_function():
            raise ValueError("Validation failed")
        
        result = invalid_function()
        self.assertFalse(result)
        mock_log_error.assert_called_once()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_validation_safe_custom_return_value(self, mock_log_error):
        """Test validation function with custom return value"""
        
        @validation_safe(return_value=None)
        def invalid_function():
            raise ValueError("Validation failed")
        
        result = invalid_function()
        self.assertIsNone(result)
        mock_log_error.assert_called_once()


class TestFileOperationSafeDecorator(TestCase):
    """Test file_operation_safe decorator behavior"""
    
    @patch('packages.utils.error_handling.logging.error')
    def test_file_operation_safe_success(self, mock_log_error):
        """Test decorator allows successful file operations"""
        
        @file_operation_safe()
        def successful_file_op():
            return "file_success"
        
        result = successful_file_op()
        self.assertEqual(result, "file_success")
        mock_log_error.assert_not_called()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_file_operation_safe_file_not_found(self, mock_log_error):
        """Test decorator handles FileNotFoundError"""
        
        @file_operation_safe(return_value="file_not_found")
        def missing_file_function():
            raise FileNotFoundError("File not found")
        
        result = missing_file_function()
        self.assertEqual(result, "file_not_found")
        mock_log_error.assert_called_once()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_file_operation_safe_permission_error(self, mock_log_error):
        """Test decorator handles PermissionError"""
        
        @file_operation_safe(return_value="permission_denied")
        def permission_error_function():
            raise PermissionError("Permission denied")
        
        result = permission_error_function()
        self.assertEqual(result, "permission_denied")
        mock_log_error.assert_called_once()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_file_operation_safe_io_error(self, mock_log_error):
        """Test decorator handles IOError"""
        
        @file_operation_safe(return_value="io_error")
        def io_error_function():
            raise IOError("IO error")
        
        result = io_error_function()
        self.assertEqual(result, "io_error")
        mock_log_error.assert_called_once()
    
    @patch('packages.utils.error_handling.logging.error')
    def test_file_operation_safe_os_error(self, mock_log_error):
        """Test decorator handles OSError"""
        
        @file_operation_safe(return_value="os_error")
        def os_error_function():
            raise OSError("OS error")
        
        result = os_error_function()
        self.assertEqual(result, "os_error")
        mock_log_error.assert_called_once()


class TestRetryOnFailureDecorator(TestCase):
    """Test retry_on_failure decorator behavior"""
    
    @patch('time.sleep')
    @patch('packages.utils.error_handling.logging.warning')
    def test_retry_success_on_first_attempt(self, mock_log_warning, mock_sleep):
        """Test function succeeds on first attempt (no retry)"""
        
        @retry_on_failure(max_attempts=3)
        def successful_function():
            return "success"
        
        result = successful_function()
        self.assertEqual(result, "success")
        mock_sleep.assert_not_called()
        mock_log_warning.assert_not_called()
    
    @patch('time.sleep')
    @patch('packages.utils.error_handling.logging.warning')
    def test_retry_success_on_second_attempt(self, mock_log_warning, mock_sleep):
        """Test function succeeds on second attempt"""
        
        call_count = 0
        
        @retry_on_failure(max_attempts=3, delay=1.0)
        def retry_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return "success_on_retry"
        
        result = retry_function()
        self.assertEqual(result, "success_on_retry")
        self.assertEqual(call_count, 2)
        mock_sleep.assert_called_once_with(1.0)
        mock_log_warning.assert_called_once()
    
    @patch('time.sleep')
    @patch('packages.utils.error_handling.logging.warning')
    def test_retry_exponential_backoff(self, mock_log_warning, mock_sleep):
        """Test exponential backoff delays"""
        
        call_count = 0
        
        @retry_on_failure(max_attempts=3, delay=1.0, backoff_multiplier=2.0)
        def retry_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} fails")
            return "success"
        
        result = retry_function()
        self.assertEqual(result, "success")
        
        # Check exponential backoff: 1.0, then 2.0
        expected_calls = [call(1.0), call(2.0)]
        mock_sleep.assert_has_calls(expected_calls)
    
    @patch('time.sleep')
    @patch('packages.utils.error_handling.logging.warning')
    def test_retry_max_attempts_exceeded(self, mock_log_warning, mock_sleep):
        """Test function fails after max attempts"""
        
        @retry_on_failure(max_attempts=2, delay=0.5)
        def always_fails_function():
            raise ValueError("Always fails")
        
        with self.assertRaises(ValueError) as context:
            always_fails_function()
        
        self.assertEqual(str(context.exception), "Always fails")
        
        # Should sleep once (between attempt 1 and 2, but not after final failure)
        mock_sleep.assert_called_once_with(0.5)
        mock_log_warning.assert_called_once()
    
    @patch('time.sleep')
    @patch('packages.utils.error_handling.logging.warning')
    def test_retry_custom_exceptions(self, mock_log_warning, mock_sleep):
        """Test retry only on specified exception types"""
        
        @retry_on_failure(max_attempts=3, exceptions=(ValueError,))
        def custom_exception_function():
            raise TypeError("Should not retry on TypeError")
        
        # Should raise immediately without retry since TypeError not in exceptions
        with self.assertRaises(TypeError):
            custom_exception_function()
        
        mock_sleep.assert_not_called()
        mock_log_warning.assert_not_called()
    
    @patch('time.sleep')
    @patch('packages.utils.error_handling.logging.warning')
    def test_retry_preserves_function_metadata(self, mock_log_warning, mock_sleep):
        """Test decorator preserves original function metadata"""
        
        @retry_on_failure()
        def test_function():
            """Test docstring"""
            return "test"
        
        self.assertEqual(test_function.__name__, "test_function")
        self.assertEqual(test_function.__doc__, "Test docstring")


class TestErrorContext(TestCase):
    """Test ErrorContext context manager behavior"""
    
    @patch('packages.utils.error_handling.logging.info')
    def test_error_context_success(self, mock_log_info):
        """Test context manager with successful operation"""
        
        with ErrorContext("test_operation") as ctx:
            result = "success"
        
        self.assertIsNone(ctx.exception)
        
        # Check logging calls
        expected_calls = [
            call("Starting test_operation"),
            call("Successfully completed test_operation")
        ]
        mock_log_info.assert_has_calls(expected_calls)
    
    @patch('packages.utils.error_handling.logging.error')
    @patch('packages.utils.error_handling.logging.info')
    def test_error_context_with_exception_reraise(self, mock_log_info, mock_log_error):
        """Test context manager with exception and reraise=True"""
        
        with self.assertRaises(ValueError) as exc_context:
            with ErrorContext("test_operation", reraise=True) as ctx:
                raise ValueError("Test error")
        
        self.assertEqual(str(exc_context.exception), "Test error")
        self.assertIsInstance(ctx.exception, ValueError)
        
        mock_log_info.assert_called_once_with("Starting test_operation")
        mock_log_error.assert_called_once_with("Error in test_operation: Test error")
    
    @patch('packages.utils.error_handling.logging.error')
    @patch('packages.utils.error_handling.logging.info')
    def test_error_context_suppress_exception(self, mock_log_info, mock_log_error):
        """Test context manager with exception and reraise=False"""
        
        with ErrorContext("test_operation", reraise=False) as ctx:
            raise ValueError("Test error")
        
        # Exception should be suppressed
        self.assertIsInstance(ctx.exception, ValueError)
        
        mock_log_info.assert_called_once_with("Starting test_operation")
        mock_log_error.assert_called_once_with("Error in test_operation: Test error")
    
    @patch('packages.utils.error_handling.logging.error')
    @patch('packages.utils.error_handling.logging.info')
    def test_error_context_with_cleanup_function(self, mock_log_info, mock_log_error):
        """Test context manager executes cleanup function on error"""
        
        cleanup_mock = Mock()
        
        with ErrorContext("test_operation", cleanup_func=cleanup_mock, reraise=False):
            raise ValueError("Test error")
        
        cleanup_mock.assert_called_once()
        mock_log_error.assert_called_once_with("Error in test_operation: Test error")
    
    @patch('packages.utils.error_handling.logging.error')
    @patch('packages.utils.error_handling.logging.info')
    def test_error_context_cleanup_function_error(self, mock_log_info, mock_log_error):
        """Test context manager handles cleanup function errors"""
        
        def failing_cleanup():
            raise RuntimeError("Cleanup failed")
        
        with ErrorContext("test_operation", cleanup_func=failing_cleanup, reraise=False):
            raise ValueError("Test error")
        
        # Should log both the original error and cleanup error
        expected_calls = [
            call("Error in test_operation: Test error"),
            call("Error during cleanup: Cleanup failed")
        ]
        mock_log_error.assert_has_calls(expected_calls)
    
    @patch('packages.utils.error_handling.logging.info')
    def test_error_context_no_cleanup_on_success(self, mock_log_info):
        """Test context manager doesn't call cleanup on success"""
        
        cleanup_mock = Mock()
        
        with ErrorContext("test_operation", cleanup_func=cleanup_mock):
            result = "success"
        
        cleanup_mock.assert_not_called()


class TestErrorHandlingIntegration(TestCase):
    """Integration tests for error handling decorators"""
    
    @patch('packages.utils.error_handling.logging.error')
    @patch('packages.utils.error_handling.logging.warning')
    @patch('time.sleep')
    def test_combined_decorators(self, mock_sleep, mock_log_warning, mock_log_error):
        """Test combining multiple error handling decorators"""
        
        call_count = 0
        
        @selenium_safe(return_value="fallback")
        @retry_on_failure(max_attempts=2, delay=0.1)
        def combined_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutException("First attempt timeout")
            return "success"
        
        result = combined_function()
        
        # Should succeed on retry, not fall back to selenium_safe
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)
        
        # Verify retry was attempted
        mock_sleep.assert_called_once_with(0.1)
        mock_log_warning.assert_called_once()
        
        # selenium_safe should not have logged error since retry succeeded
        mock_log_error.assert_not_called()


if __name__ == "__main__":
    # Setup basic logging for tests
    logging.basicConfig(level=logging.WARNING)
    
    import unittest
    unittest.main()