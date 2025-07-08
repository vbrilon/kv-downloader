"""Utility functions package for karaoke automation"""

from .logging_setup import setup_logging
from .click_handlers import safe_click, safe_click_with_scroll

__all__ = ['setup_logging', 'safe_click', 'safe_click_with_scroll']