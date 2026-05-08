#!/usr/bin/env python3
"""Regression tests for `_is_solo_button_active` token-vs-substring matching.

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

from packages.track_management import TrackManager
from packages.download_management.download_manager import DownloadManager


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


class TestTrackManagerSoloDetection(unittest.TestCase):
    def setUp(self):
        self.tm = TrackManager(Mock(), Mock())

    # ----- inactive states must NOT report active -------------------------

    def test_inactive_class_is_not_active(self):
        """`inactive` must not match the `active` needle (substring bug)."""
        btn = _button("track__solo inactive")
        self.assertFalse(self.tm._is_solo_button_active(btn))

    def test_track_solo_modifier_inactive_is_not_active(self):
        btn = _button("track__solo track__solo--inactive")
        self.assertFalse(self.tm._is_solo_button_active(btn))

    def test_button_class_is_not_active(self):
        """`button` ends in `on` and must not match the `on` needle."""
        btn = _button("track__solo button")
        self.assertFalse(self.tm._is_solo_button_active(btn))

    def test_icon_class_is_not_active(self):
        """`icon` ends in `on` and must not match the `on` needle."""
        btn = _button("track__solo icon icon-solo")
        self.assertFalse(self.tm._is_solo_button_active(btn))

    def test_bare_solo_button_is_not_active(self):
        btn = _button("track__solo")
        self.assertFalse(self.tm._is_solo_button_active(btn))

    def test_empty_class_is_not_active(self):
        btn = _button("")
        self.assertFalse(self.tm._is_solo_button_active(btn))

    def test_aria_pressed_false_is_not_active(self):
        btn = _button("track__solo", aria_pressed="false")
        self.assertFalse(self.tm._is_solo_button_active(btn))

    # ----- active states MUST report active -------------------------------

    def test_is_active_class_reports_active(self):
        btn = _button("track__solo is-active")
        self.assertTrue(self.tm._is_solo_button_active(btn))

    def test_active_token_reports_active(self):
        btn = _button("track__solo active")
        self.assertTrue(self.tm._is_solo_button_active(btn))

    def test_selected_token_reports_active(self):
        btn = _button("track__solo selected")
        self.assertTrue(self.tm._is_solo_button_active(btn))

    def test_modifier_active_token_reports_active(self):
        btn = _button("track__solo track__solo--active")
        self.assertTrue(self.tm._is_solo_button_active(btn))

    def test_aria_pressed_true_reports_active(self):
        btn = _button("track__solo", aria_pressed="true")
        self.assertTrue(self.tm._is_solo_button_active(btn))

    def test_data_state_active_reports_active(self):
        btn = _button("track__solo", data_state="active")
        self.assertTrue(self.tm._is_solo_button_active(btn))


class TestDownloadManagerSoloDetection(unittest.TestCase):
    """The download verifier carries an independent copy of the same logic."""

    def setUp(self):
        # DownloadManager has many dependencies; only `_is_solo_button_active`
        # is exercised here, so all collaborators can be Mocks.
        self.dm = DownloadManager(Mock(), Mock(), Mock(), Mock(), Mock(), Mock())

    def test_inactive_class_is_not_active(self):
        btn = _button("track__solo inactive")
        self.assertFalse(self.dm._is_solo_button_active_enhanced(btn))

    def test_button_class_is_not_active(self):
        btn = _button("track__solo button")
        self.assertFalse(self.dm._is_solo_button_active_enhanced(btn))

    def test_is_active_class_reports_active(self):
        btn = _button("track__solo is-active")
        self.assertTrue(self.dm._is_solo_button_active_enhanced(btn))


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
    handle string indices correctly (the prior int == str comparison silently failed)."""
    from packages.track_management.track_manager import TrackManager

    tm = mocker.Mock(spec=TrackManager)
    tm.driver = mocker.Mock()
    tm.driver.current_url = 'https://song-url'

    btn0 = mocker.Mock()
    btn3 = mocker.Mock()
    btn3.click = mocker.Mock()
    tm.driver.find_elements = mocker.Mock(return_value=[btn0, mocker.Mock(), mocker.Mock(), btn3])
    tm._is_solo_button_active = mocker.Mock(return_value=False)

    mocker.patch('packages.track_management.track_manager.WebDriverWait')

    result = TrackManager.ensure_only_track_active(tm, "3", "https://song-url")

    assert result is True
    btn3.click.assert_called_once()


if __name__ == "__main__":
    unittest.main()
