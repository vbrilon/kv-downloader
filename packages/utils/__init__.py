"""Utility functions package for karaoke automation"""

from .logging_setup import setup_logging
from .click_handlers import safe_click, safe_click_with_scroll
from .error_handling import (
    selenium_safe, 
    validation_safe, 
    file_operation_safe, 
    retry_on_failure, 
    ErrorContext
)

__all__ = [
    'setup_logging', 
    'safe_click', 
    'safe_click_with_scroll',
    'selenium_safe',
    'validation_safe', 
    'file_operation_safe',
    'retry_on_failure',
    'ErrorContext'
]