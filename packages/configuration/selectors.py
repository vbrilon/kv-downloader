"""Centralized CSS/XPath selectors with primary and fallbacks.

This module centralizes selectors used across the app to reduce drift and
ease maintenance. Keep lists ordered by preference; earlier entries are
considered higher confidence.
"""

# Download button selectors (primary → fallbacks)
DOWNLOAD_BUTTON_SELECTORS = [
    "a.download",                      # Primary discovered selector
    "a[class*='download']",           # Fallback: class contains download
    "//a[contains(@class, 'download')]",  # XPath fallback
    "//a[contains(text(), 'Download')]",  # Text fallback
    "//a[contains(text(), 'MP3')]",       # Last-resort text
]

# Login-related selectors (kept for future migrations)
LOGIN_STATUS_SELECTORS = [
    ("xpath", "//a[contains(text(), 'Log out')]"),
    ("xpath", "//a[contains(text(), 'Log in')]")
]

# Track/mixer selectors
TRACK_ELEMENT_SELECTOR = ".track"

# Solo button selectors within a track (primary → fallbacks)
SOLO_BUTTON_SELECTORS = [
    "button.track__solo",                 # Primary
    "button.track__controls.track__solo", # Variant with multiple classes
    ".track__solo",                        # Generic class
    "button[class*='solo']",              # Fallback by class name
]
