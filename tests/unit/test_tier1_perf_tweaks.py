"""Tier 1 performance tweaks — pinning tests for the constants and behaviors.

These changes were chosen to be low-risk and to avoid the race conditions
that earlier optimizations almost introduced. They are pinned here so a
future edit can't silently revert them.

Background: the dominant cost per track (~14s) is server-side audio mix
generation; that's unmovable. Tier 1 reclaims wasted client-side wall-time:
post-detection buffers and conservative polling intervals.
"""
import unittest
from unittest.mock import patch


class TestPollingIntervalShortened(unittest.TestCase):
    """DOWNLOAD_CHECK_INTERVAL gates how often we poll the song folder for
    a completed file after the readiness signal fires. The cost of a poll
    is one cached directory scan (2s TTL). Shorter polls = faster completion
    detection."""

    def test_download_check_interval_is_one_second(self):
        from packages.configuration.config import DOWNLOAD_CHECK_INTERVAL
        self.assertEqual(
            DOWNLOAD_CHECK_INTERVAL, 1,
            "DOWNLOAD_CHECK_INTERVAL must be 1s. The previous 3s value left "
            "up to 2s/track of completion-detection latency on the table."
        )


class TestBetweenTracksPause(unittest.TestCase):
    """BETWEEN_TRACKS_PAUSE = small delay between completing a download and
    soloing the next track. Required >0 to let UI events settle (close
    completes, button states update) but the previous 0.5s was overkill."""

    def test_between_tracks_pause_is_short_but_nonzero(self):
        from packages.configuration.config import BETWEEN_TRACKS_PAUSE
        # Must be small (<0.3s) — the optimization point — but NOT zero. A
        # zero pause races against UI event settling between tracks.
        self.assertGreater(BETWEEN_TRACKS_PAUSE, 0.0,
                           "Pause must remain > 0 to avoid UI-settling races.")
        self.assertLessEqual(BETWEEN_TRACKS_PAUSE, 0.25,
                             "Pause should be tightened from the old 0.5s value.")


class TestFinalizeSoloActivationNoEndBuffer(unittest.TestCase):
    """When _wait_for_audio_server_sync returns True we have already
    DETERMINISTICALLY detected that the solo button is active in the DOM. A
    further post-detection time.sleep(0.2) was pure padding — the next
    operation is a click on the SAME page, which goes through chromedriver's
    own state-readiness checks. Drop it.

    The fallback path (audio_server_ready=False) keeps its 1.0s buffer
    because there we DIDN'T confirm sync — the buffer is a real safety net.
    """

    def test_no_post_detection_sleep_when_audio_ready(self):
        from packages.track_management.track_manager import TrackManager
        from unittest.mock import MagicMock

        tm = MagicMock(spec=TrackManager)
        tm._wait_for_audio_server_sync = MagicMock(return_value=True)

        with patch('packages.track_management.track_manager.time.sleep') as mock_sleep:
            TrackManager._finalize_solo_activation(tm, "Bass", track_index=3)

        # Audio sync returned True — there must be NO sleep in the success path.
        # If a sleep is present, this assertion documents the regression.
        mock_sleep.assert_not_called()

    def test_fallback_sleep_remains_when_audio_not_ready(self):
        """The fallback safety buffer is the only protection when audio sync
        could not be confirmed. It must stay."""
        from packages.track_management.track_manager import TrackManager
        from unittest.mock import MagicMock

        tm = MagicMock(spec=TrackManager)
        tm._wait_for_audio_server_sync = MagicMock(return_value=False)

        with patch('packages.track_management.track_manager.time.sleep') as mock_sleep:
            TrackManager._finalize_solo_activation(tm, "Bass", track_index=3)

        # Should sleep ONCE for the fallback buffer
        mock_sleep.assert_called_once()
        # The fallback should be at least 0.5s — short enough not to dominate,
        # long enough to be a real safety net
        sleep_arg = mock_sleep.call_args[0][0]
        self.assertGreaterEqual(sleep_arg, 0.5)
        self.assertLessEqual(sleep_arg, 2.0)


if __name__ == "__main__":
    unittest.main()
