"""
Standardized error handling decorators and utilities.

Provides consistent error handling patterns across the codebase to reduce
duplication and improve maintainability.
"""

import logging
import functools
from typing import Any, Callable, Optional, Type
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    ElementClickInterceptedException,
    WebDriverException
)


def selenium_safe(
    return_value: Any = None,
    log_error: bool = True,
    operation_name: Optional[str] = None,
    suppress_exceptions: tuple = None
) -> Callable:
    """
    Decorator for safe Selenium operations with standardized error handling.
    
    Args:
        return_value: Value to return on error (default: None)
        log_error: Whether to log errors (default: True)
        operation_name: Custom name for operation in logs
        suppress_exceptions: Additional exception types to catch
    
    Returns:
        Decorated function with error handling
    """
    if suppress_exceptions is None:
        suppress_exceptions = ()
    
    # Standard Selenium exceptions to catch
    selenium_exceptions = (
        TimeoutException,
        NoSuchElementException,
        ElementNotInteractableException,
        ElementClickInterceptedException,
        WebDriverException,
        Exception  # Catch-all for unexpected errors
    )
    
    # Combine standard and custom exceptions
    all_exceptions = selenium_exceptions + suppress_exceptions
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except all_exceptions as e:
                if log_error:
                    func_name = operation_name or func.__name__
                    logging.error(f"Error in {func_name}: {e}")
                return return_value
        return wrapper
    return decorator


def validation_safe(
    return_value: bool = False,
    log_error: bool = True,
    operation_name: Optional[str] = None
) -> Callable:
    """
    Decorator specifically for validation operations that should return boolean.
    
    Args:
        return_value: Boolean to return on error (default: False)
        log_error: Whether to log errors (default: True)
        operation_name: Custom name for operation in logs
    
    Returns:
        Decorated function with validation-specific error handling
    """
    return selenium_safe(
        return_value=return_value,
        log_error=log_error,
        operation_name=operation_name
    )


def file_operation_safe(
    return_value: Any = None,
    log_error: bool = True,
    operation_name: Optional[str] = None
) -> Callable:
    """
    Decorator for safe file operations.
    
    Args:
        return_value: Value to return on error (default: None)
        log_error: Whether to log errors (default: True)
        operation_name: Custom name for operation in logs
    
    Returns:
        Decorated function with file operation error handling
    """
    file_exceptions = (
        OSError,
        FileNotFoundError,
        PermissionError,
        IOError
    )
    
    return selenium_safe(
        return_value=return_value,
        log_error=log_error,
        operation_name=operation_name,
        suppress_exceptions=file_exceptions
    )


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = None,
    backoff_multiplier: float = 1.5
) -> Callable:
    """
    Decorator to retry operations on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        exceptions: Exception types to retry on (default: all)
        backoff_multiplier: Factor to increase delay between retries
    
    Returns:
        Decorated function with retry logic
    """
    import time
    
    if exceptions is None:
        exceptions = (Exception,)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:  # Last attempt
                        raise e
                    
                    logging.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff_multiplier
            
        return wrapper
    return decorator


class ErrorContext:
    """Context manager for standardized error handling in complex operations."""
    
    def __init__(
        self,
        operation_name: str,
        cleanup_func: Optional[Callable] = None,
        reraise: bool = True,
        return_value: Any = None
    ):
        self.operation_name = operation_name
        self.cleanup_func = cleanup_func
        self.reraise = reraise
        self.return_value = return_value
        self.exception = None
    
    def __enter__(self):
        logging.info(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.exception = exc_val
            logging.error(f"Error in {self.operation_name}: {exc_val}")
            
            if self.cleanup_func:
                try:
                    self.cleanup_func()
                except Exception as cleanup_error:
                    logging.error(f"Error during cleanup: {cleanup_error}")
            
            if not self.reraise:
                return True  # Suppress the exception
        else:
            logging.info(f"Successfully completed {self.operation_name}")
        
        return False  # Re-raise exception if reraise=True