"""Single source of truth for solo-button active-state detection.

Use this from both track_management (during activation) and download_management
(during pre-download verification). If the active class set ever changes, update
ACTIVE_SOLO_CLASS_TOKENS here — exactly once.

Class matching is by exact token (not substring): "active" appears inside
"inactive", and "on" appears inside "button"/"icon", so substring matching
produces false positives on every inactive solo button.
"""
import logging

# Exact CSS class tokens that signal an active solo button.
ACTIVE_SOLO_CLASS_TOKENS = frozenset({
    "is-active",
    "active",
    "selected",
    "track__solo--active",
})


def is_solo_button_active(solo_button) -> bool:
    """Detect active state via class tokens, ARIA, or data-state.

    Returns False on any error (caller handles retries)."""
    try:
        class_tokens = set((solo_button.get_attribute('class') or '').lower().split())
        if class_tokens & ACTIVE_SOLO_CLASS_TOKENS:
            return True

        aria_pressed = solo_button.get_attribute('aria-pressed')
        if aria_pressed == 'true':
            return True

        data_state = (solo_button.get_attribute('data-state') or '').lower()
        if data_state in ('active', 'on', 'selected'):
            return True

        return False
    except Exception as e:
        logging.debug(f"Error in solo button active detection: {e}")
        return False
