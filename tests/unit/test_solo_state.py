"""Tests for the consolidated solo-button state detector."""


def test_is_active_with_canonical_class():
    from packages.utils.solo_state import is_solo_button_active

    class FakeButton:
        def get_attribute(self, name):
            return {'class': 'track__solo track__solo--active', 'aria-pressed': None, 'data-state': None}.get(name)
    assert is_solo_button_active(FakeButton()) is True


def test_inactive_does_not_match_via_substring():
    """The word 'active' inside 'inactive' must not match. This is the primary
    bug the token-based comparison was introduced to prevent."""
    from packages.utils.solo_state import is_solo_button_active

    class FakeButton:
        def get_attribute(self, name):
            return {'class': 'track__solo track__solo--inactive', 'aria-pressed': None, 'data-state': None}.get(name)
    assert is_solo_button_active(FakeButton()) is False


def test_aria_pressed_true_means_active():
    from packages.utils.solo_state import is_solo_button_active

    class FakeButton:
        def get_attribute(self, name):
            return {'class': 'track__solo', 'aria-pressed': 'true', 'data-state': None}.get(name)
    assert is_solo_button_active(FakeButton()) is True


def test_data_state_active_means_active():
    from packages.utils.solo_state import is_solo_button_active

    class FakeButton:
        def get_attribute(self, name):
            return {'class': 'track__solo', 'aria-pressed': None, 'data-state': 'active'}.get(name)
    assert is_solo_button_active(FakeButton()) is True
