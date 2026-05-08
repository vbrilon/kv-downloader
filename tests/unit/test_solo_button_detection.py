#!/usr/bin/env python3
"""Regression tests for `is_solo_button_active` token-vs-substring matching.

Background: an earlier implementation used Python `in` against the raw class
string, treating "active" / "on" / "selected" / "is-active" as substrings. That
caused two false-positive families:

  * "active"  is a substring of "inactive"
  * "on"      is a substring of common BEM/utility classes ("button", "icon")

Either misfire makes every solo button report as already-active, which in turn
drives `ensure_only_track_active()` to "deactivate" all 15 buttons by clicking
each one — visible to the user as the mixer briefly soloing every track before
landing on the intended one.

These tests pin the detector to exact CSS-class token matching so that
regression cannot return.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.utils import is_solo_button_active


def _button(class_attr, *, aria_pressed=None, data_state=None, style=""):
    """Build a Selenium-WebElement-like mock that returns the supplied attrs."""
    btn = Mock()

    def get_attribute(name):
        return {
            "class": class_attr,
            "aria-pressed": aria_pressed,
            "data-state": data_state,
            "style": style,
        }.get(name)

    btn.get_attribute.side_effect = get_attribute
    return btn


class TestSoloDetection(unittest.TestCase):
    """The canonical predicate is `packages.utils.is_solo_button_active`.

    Both track activation and download verification call into this single
    function — see packages/utils/solo_state.py for the source of truth.
    """

    # ----- inactive states must NOT report active -------------------------

    def test_inactive_class_is_not_active(self):
        """`inactive` must not match the `active` needle (substring bug)."""
        btn = _button("track__solo inactive")
        self.assertFalse(is_solo_button_active(btn))

    def test_track_solo_modifier_inactive_is_not_active(self):
        btn = _button("track__solo track__solo--inactive")
        self.assertFalse(is_solo_button_active(btn))

    def test_button_class_is_not_active(self):
        """`button` ends in `on` and must not match the `on` needle."""
        btn = _button("track__solo button")
        self.assertFalse(is_solo_button_active(btn))

    def test_icon_class_is_not_active(self):
        """`icon` ends in `on` and must not match the `on` needle."""
        btn = _button("track__solo icon icon-solo")
        self.assertFalse(is_solo_button_active(btn))

    def test_bare_solo_button_is_not_active(self):
        btn = _button("track__solo")
        self.assertFalse(is_solo_button_active(btn))

    def test_empty_class_is_not_active(self):
        btn = _button("")
        self.assertFalse(is_solo_button_active(btn))

    def test_aria_pressed_false_is_not_active(self):
        btn = _button("track__solo", aria_pressed="false")
        self.assertFalse(is_solo_button_active(btn))

    # ----- active states MUST report active -------------------------------

    def test_is_active_class_reports_active(self):
        btn = _button("track__solo is-active")
        self.assertTrue(is_solo_button_active(btn))

    def test_active_token_reports_active(self):
        btn = _button("track__solo active")
        self.assertTrue(is_solo_button_active(btn))

    def test_selected_token_reports_active(self):
        btn = _button("track__solo selected")
        self.assertTrue(is_solo_button_active(btn))

    def test_modifier_active_token_reports_active(self):
        btn = _button("track__solo track__solo--active")
        self.assertTrue(is_solo_button_active(btn))

    def test_aria_pressed_true_reports_active(self):
        btn = _button("track__solo", aria_pressed="true")
        self.assertTrue(is_solo_button_active(btn))

    def test_data_state_active_reports_active(self):
        btn = _button("track__solo", data_state="active")
        self.assertTrue(is_solo_button_active(btn))


def test_finalize_solo_activation_does_not_call_phase3_validation(mocker):
    """_finalize_solo_activation should not call _validate_audio_mix_state anymore."""
    from packages.track_management.track_manager import TrackManager

    tm = mocker.Mock(spec=TrackManager)
    tm._wait_for_audio_server_sync = mocker.Mock(return_value=True)
    tm._validate_audio_mix_state = mocker.Mock(return_value={'audio_mix_validated': True})

    TrackManager._finalize_solo_activation(tm, "Bass", 3)

    tm._validate_audio_mix_state.assert_not_called()


def test_finalize_solo_activation_does_not_call_mixer_state_check(mocker):
    from packages.track_management.track_manager import TrackManager

    tm = mocker.Mock(spec=TrackManager)
    tm._wait_for_audio_server_sync = mocker.Mock(return_value=True)
    tm._verify_mixer_state_configuration = mocker.Mock(return_value=True)

    TrackManager._finalize_solo_activation(tm, "Bass", 3)

    tm._verify_mixer_state_configuration.assert_not_called()


def test_ensure_only_track_active_finds_target_with_string_index(mocker):
    """data-index comes from the DOM as a string. ensure_only_track_active must
    handle string indices correctly (the prior int == str comparison silently failed).

    The activation goes through js_click_with_scroll (so off-screen targets are
    scroll-into-view'd then JS-clicked) — verify it's invoked with the target button.
    """
    from packages.track_management.track_manager import TrackManager

    tm = mocker.Mock(spec=TrackManager)
    tm.driver = mocker.Mock()
    tm.driver.current_url = 'https://song-url'

    btn0 = mocker.Mock()
    btn3 = mocker.Mock()
    tm.driver.find_elements = mocker.Mock(return_value=[btn0, mocker.Mock(), mocker.Mock(), btn3])
    # Production code now uses the module-level is_solo_button_active, not a
    # method on TrackManager — patch it at the module where it's looked up.
    mocker.patch('packages.track_management.track_manager.is_solo_button_active', return_value=False)

    mocker.patch('packages.track_management.track_manager.WebDriverWait')
    mock_js_click = mocker.patch('packages.track_management.track_manager.js_click_with_scroll', return_value=True)

    result = TrackManager.ensure_only_track_active(tm, "3", "https://song-url")

    assert result is True
    # The target button (btn3) must have been the click target.
    mock_js_click.assert_called_once()
    args, _ = mock_js_click.call_args
    assert args[1] is btn3, f"Expected target button (btn3) to be clicked, got {args[1]}"


# ---------------------------------------------------------------------------
# Click-track 12s timeout fix (2026-05-08)
# ---------------------------------------------------------------------------
# Root cause (verified via Chrome DevTools trace on 2026-05-08):
# `ensure_only_track_active` already activates the target solo button. Then
# `solo_track` reads `is_solo_button_active(solo_button)` — which can return
# False as a transient race on track 0 of a fresh page — and clicks AGAIN.
# That second click TOGGLES THE BUTTON OFF. Polling for active fails for 10–12s.
# The retry path's `_perform_aggressive_clicks` fires 3 clicks (ON-OFF-ON,
# odd count) which lands the button back ON. The 12s SOLO_ACTIVATION_DELAY_CLICK
# constant was just absorbing this self-inflicted toggle-off; the right fix is
# to stop clicking redundantly in `solo_track`.
#
# After the fix:
#   * `ensure_only_track_active` is the single source of activation clicks.
#   * `solo_track` is verify-only — polls until active (or times out into retry).
#   * The retry safety net (3 aggressive clicks at an inactive button → ACTIVE)
#     stays for the rare case `ensure_only_track_active` never activated.
#   * Click tracks fall through to the standard adaptive timeout.

def test_solo_track_does_not_click_redundantly(mocker):
    """solo_track must NOT click the solo button. ensure_only_track_active
    already clicks it; a redundant click TOGGLES the button OFF (verified
    on the live mixer 2026-05-08), which is what the 12s click-track timeout
    was masking.

    The retry path (`_perform_aggressive_clicks`) remains as the safety net
    if `ensure_only_track_active` ever fails to activate.
    """
    from packages.track_management.track_manager import TrackManager

    tm = mocker.Mock(spec=TrackManager)
    tm.driver = mocker.Mock()
    tm.driver.current_url = 'https://song-url'
    tm.progress_tracker = None

    track_element = mocker.Mock()
    solo_button = mocker.Mock()
    tm._navigate_to_song_if_needed = mocker.Mock()
    tm._find_track_element = mocker.Mock(return_value=track_element)
    tm._find_solo_button = mocker.Mock(return_value=solo_button)
    tm._activate_solo_button_verify_only = mocker.Mock(return_value=True)

    mock_js_click = mocker.patch('packages.track_management.track_manager.js_click_with_scroll', return_value=True)

    # Whether is_solo_button_active reads True or False does not matter —
    # solo_track must not click in either case. Cover both to lock that in.
    for transient_state in (True, False):
        mocker.patch(
            'packages.track_management.track_manager.is_solo_button_active',
            return_value=transient_state,
        )
        mock_js_click.reset_mock()

        result = TrackManager.solo_track(tm, {'index': '0', 'name': 'Intro count Click'}, 'https://song-url')

        assert result is True
        mock_js_click.assert_not_called(), (
            f"solo_track must not click (is_solo_button_active read {transient_state}); "
            "ensure_only_track_active is the single source of activation clicks."
        )

    # safe_click was the original click helper here; it is no longer needed.
    import packages.track_management.track_manager as tm_mod
    assert not hasattr(tm_mod, 'safe_click'), (
        "track_manager should no longer import safe_click; the redundant click "
        "in solo_track was removed entirely."
    )


def test_get_track_type_timeout_uses_adaptive_for_click_tracks(mocker):
    """Click tracks must use the standard adaptive timeout, not a hard-coded
    12s constant. The 12s value masked the silent-native-click bug; removing
    that mask is the whole point of this fix.
    """
    from packages.track_management.track_manager import TrackManager
    from packages.configuration.config import (
        SOLO_ACTIVATION_DELAY_SIMPLE,
        SOLO_ACTIVATION_DELAY_COMPLEX,
    )

    tm = mocker.Mock(spec=TrackManager)
    tm.track_complexity = "complex"
    tm._detect_track_type = lambda name: "click"
    tm._get_adaptive_timeout = lambda: SOLO_ACTIVATION_DELAY_COMPLEX

    timeout = TrackManager._get_track_type_timeout(tm, "Intro count Click")

    assert timeout == SOLO_ACTIVATION_DELAY_COMPLEX, (
        f"Click tracks should use adaptive timeout ({SOLO_ACTIVATION_DELAY_COMPLEX}s), "
        f"not the deleted 12s constant. Got {timeout}."
    )

    tm.track_complexity = "simple"
    tm._get_adaptive_timeout = lambda: SOLO_ACTIVATION_DELAY_SIMPLE
    timeout_simple = TrackManager._get_track_type_timeout(tm, "Intro count Click")
    assert timeout_simple == SOLO_ACTIVATION_DELAY_SIMPLE


def test_solo_activation_delay_click_constant_is_removed():
    """The SOLO_ACTIVATION_DELAY_CLICK constant must be deleted from config.

    Why: leaving it in place invites future "let's tune it" attempts that
    re-introduce the click-specific path that the rest of the system
    no longer needs.
    """
    from packages.configuration import config
    assert not hasattr(config, 'SOLO_ACTIVATION_DELAY_CLICK'), (
        "SOLO_ACTIVATION_DELAY_CLICK should be removed; click tracks now use "
        "the standard adaptive timeout via _get_adaptive_timeout()."
    )


if __name__ == "__main__":
    unittest.main()
