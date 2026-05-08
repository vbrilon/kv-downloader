"""Pinning tests for the A/B mixer-rendering defensive selectors.

Background (verified live 2026-05-08 via headless Selenium and Chrome MCP):
karaoke-version.com renders the mixer in TWO different markup variants and
hands a given session ONE of them based on a sticky bucket (likely cookie-
based, NOT UA-based). We must match either variant to survive an A/B flip:

    Legacy bucket  (mixer__inner container):
        .track[data-index="N"]
        .track__caption

    Modern bucket  (custom__mixer-container container):
        .custom__mixer-track-line[data-index="N"]
        .custom__mixer-track-caption-name

These tests pin the comma-list selectors so a future edit can't silently
narrow them back to one variant — that would make discover_tracks return
zero tracks the day the bucket flips.
"""
import unittest


class TestSelectorsCoverBothMixerVariants(unittest.TestCase):
    """Selectors must enumerate both the legacy and modern markup."""

    def test_track_element_selector_includes_legacy_and_modern(self):
        from packages.configuration.selectors import TRACK_ELEMENT_SELECTOR
        # Comma-list is the documented mechanism. Both variants must appear.
        parts = [s.strip() for s in TRACK_ELEMENT_SELECTOR.split(",")]
        self.assertIn(".track", parts, "Legacy '.track' selector must remain")
        self.assertIn(".custom__mixer-track-line", parts,
                      "Modern '.custom__mixer-track-line' selector must be present "
                      "so production survives the A/B flip.")

    def test_track_caption_selector_includes_legacy_and_modern(self):
        from packages.configuration.selectors import TRACK_CAPTION_SELECTOR
        parts = [s.strip() for s in TRACK_CAPTION_SELECTOR.split(",")]
        self.assertIn(".track__caption", parts, "Legacy '.track__caption' must remain")
        self.assertIn(".custom__mixer-track-caption-name", parts,
                      "Modern '.custom__mixer-track-caption-name' selector must be present "
                      "so the inner-track caption read survives the A/B flip.")


class TestFindTrackElementCompoundSelector(unittest.TestCase):
    """_find_track_element must apply the data-index='N' filter to EVERY part
    of the comma-list selector, not just one. A naive f"{SEL}[data-index='X']"
    would only filter the LAST selector in the list."""

    def test_find_track_element_builds_per_part_index_filter(self):
        # We test the helper that builds the selector. Production should
        # construct e.g.:
        #   .track[data-index='0'], .custom__mixer-track-line[data-index='0']
        from packages.track_management.track_manager import _build_indexed_track_selector
        result = _build_indexed_track_selector(".track, .custom__mixer-track-line", "0")
        parts = [p.strip() for p in result.split(",")]
        self.assertEqual(len(parts), 2)
        for p in parts:
            self.assertIn("[data-index='0']", p,
                          f"Selector part {p!r} missing the data-index filter")
        self.assertIn(".track[data-index='0']", parts)
        self.assertIn(".custom__mixer-track-line[data-index='0']", parts)

    def test_find_track_element_handles_single_selector(self):
        from packages.track_management.track_manager import _build_indexed_track_selector
        result = _build_indexed_track_selector(".track", "3")
        self.assertEqual(result, ".track[data-index='3']")

    def test_find_track_element_int_index(self):
        # data-index in the DOM is a string. Caller may pass int, str, or anything
        # str()able — accept all and stringify.
        from packages.track_management.track_manager import _build_indexed_track_selector
        result = _build_indexed_track_selector(".track, .custom__mixer-track-line", 2)
        self.assertIn(".track[data-index='2']", result)
        self.assertIn(".custom__mixer-track-line[data-index='2']", result)


if __name__ == "__main__":
    unittest.main()
