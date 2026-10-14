"""After a basket.php 503 the rest of the song must use browser downloads.

2026-10-13: every fast-path track downloaded after a 503'd basket.php call
in the same song held the PREVIOUS track's audio, although the server's
filename label named the requested track. Browser downloads were correct.
"""
from unittest.mock import Mock, patch

from packages.download_management.direct_api.direct_downloader import (
    BasketTimeoutError,
)

SONG = {"name": "Heartbreaker", "url": "https://example.com/heartbreaker.html"}
TRACKS = [{"name": n, "index": str(i)} for i, n in enumerate(["Click", "Drum Kit", "Bass"])]


def _automator():
    with patch('karaoke_automator.ConfigurationManager'), \
         patch('karaoke_automator.ChromeManager'), \
         patch('karaoke_automator.LoginManager'), \
         patch('karaoke_automator.ProgressTracker'), \
         patch('karaoke_automator.StatsReporter'), \
         patch('karaoke_automator.FileManager'), \
         patch('karaoke_automator.TrackManager'), \
         patch('karaoke_automator.DownloadManager'):
        from karaoke_automator import KaraokeVersionAutomator
        a = KaraokeVersionAutomator(headless=True)
    a.driver, a.track_manager, a.file_manager = Mock(), Mock(), Mock()
    a._download_single_track = Mock()
    return a


def _run(a, direct_side_effect):
    a._download_single_track_direct_api = Mock(side_effect=direct_side_effect)
    ctx = Mock(template_params={"prodid": "1", "s": "2"}, cookies={}, ua="UA", mixer_tracks=[])
    with patch("packages.download_management.direct_api.session_capture.capture_session",
               return_value=ctx), \
         patch("packages.download_management.direct_api.direct_downloader.DirectDownloader") as dl_cls, \
         patch("karaoke_automator.time.sleep"):
        dl_cls.return_value.label_unverified = 0
        a._download_all_tracks_direct_api(SONG, TRACKS, 0)


def test_503_switches_that_track_and_rest_of_song_to_browser():
    a = _automator()
    _run(a, [True, BasketTimeoutError("503")])
    assert a._download_single_track_direct_api.call_count == 2
    assert [c.args[1]["name"] for c in a._download_single_track.call_args_list] == [
        "Drum Kit", "Bass"
    ]


def test_next_song_tries_the_fast_path_again():
    # The shift did not carry across songs (Living Loving Maid, right after
    # Rock And Roll's 503s, was clean), so the switch is per song.
    a = _automator()
    _run(a, [BasketTimeoutError("503")])
    assert a.direct_api is True
