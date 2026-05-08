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
#
# karaoke-version.com renders the mixer in TWO different markup variants and
# A/B-buckets each session into ONE of them (verified live 2026-05-08 — see
# tools/inspection/inspect_selectors.py and docs/validation/). We must match
# either variant so production survives an A/B flip:
#
#   Legacy bucket:  <div class="track" data-index="N"> ... .track__caption ...
#   Modern bucket:  <div class="custom__mixer-track-line" data-index="N">
#                       ... .custom__mixer-track-caption-name ...
#
# The comma-list is the union (CSS selectors-list grammar) — `find_elements`
# returns matches against either side. Only one side ever populates a given
# page; bucketing is per-session.
#
# Solo button stays on `button.track__solo` because the modern markup keeps
# the legacy `track__solo` class as a compatibility alias on the new button.
TRACK_ELEMENT_SELECTOR = ".track, .custom__mixer-track-line"
TRACK_CAPTION_SELECTOR = ".track__caption, .custom__mixer-track-caption-name"

# Solo button selectors within a track (primary → fallbacks)
SOLO_BUTTON_SELECTORS = [
    "button.track__solo",                 # Primary
    "button.track__controls.track__solo", # Variant with multiple classes
    ".track__solo",                        # Generic class
    "button[class*='solo']",              # Fallback by class name
]

# Download readiness modal — verified on the live site 2026-05-08.
# .modal is pre-rendered and always-visible; the activation signal is the
# overlay sibling getting the `is-open` class when mixer.getMix() resolves.
DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR = ".modal__overlay.is-open"

# The readiness text appears inside this populated content element.
DOWNLOAD_MODAL_CONTENT_SELECTOR = ".modal .modal__content"
