"""Fastly bot-challenge detection and handling.

Since 2026-10 karaoke-version.com sits behind Fastly bot management. Normal
browsers pass a silent check; the Selenium-driven browser is escalated to an
image CAPTCHA ("Client Challenge" page, assets under /_fs-ch-<id>/). Plain
HTTP clients get the same page as an HTTP 200 HTML body. A human solve sets
`_fs_ch_*` clearance cookies in chrome_profile/ that later headless runs
reuse (verified live 2026-10-13).
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from packages.download_management.direct_api.direct_downloader import (
    DirectDownloader,
)
from packages.download_management.direct_api.trackslevels import MixerTrack
from packages.track_management.track_manager import TrackManager
from packages.utils.bot_challenge import (
    BotChallengeError,
    is_challenge_html,
    is_challenge_page,
    wait_for_clearance,
)

# Trimmed from the live challenge page served 2026-10-13.
CHALLENGE_HTML = (
    '<!DOCTYPE html><html><head><title>Client Challenge</title>'
    '<script src="/_fs-ch-1T1wmsGaOgGaSxcX/errors.js"></script></head>'
    '<body><div id="captchaContainer"><p id="captchaTitle">Enter the '
    'characters seen in the image below:</p></div>'
    '<script src="/_fs-ch-1T1wmsGaOgGaSxcX/script.js?reload=true"></script>'
    '</body></html>'
)
SONG_URL = "https://www.karaoke-version.com/custombackingtrack/cream/white-room.html"


class TestDetection:
    def test_challenge_html_detected(self):
        assert is_challenge_html(CHALLENGE_HTML)

    def test_normal_html_not_detected(self):
        assert not is_challenge_html("<html><title>White Room</title></html>")

    def test_empty_or_none_not_detected(self):
        assert not is_challenge_html("")
        assert not is_challenge_html(None)

    def test_challenge_page_detected_by_title(self):
        driver = Mock()
        driver.title = "Client Challenge"
        assert is_challenge_page(driver)

    def test_song_page_not_detected(self):
        driver = Mock()
        driver.title = "White Room - Cream - Custom Backing Track - Karaoke Version"
        assert not is_challenge_page(driver)


class TestWaitForClearance:
    def test_returns_true_once_title_changes(self):
        driver = Mock()
        driver.title = "White Room - Cream"
        assert wait_for_clearance(driver, timeout=1, poll=0.01) is True

    def test_returns_false_on_timeout(self):
        driver = Mock()
        driver.title = "Client Challenge"
        assert wait_for_clearance(driver, timeout=0.05, poll=0.01) is False


def _challenged_driver():
    driver = Mock()
    driver.title = "Client Challenge"
    driver.current_url = SONG_URL
    driver.find_elements.return_value = []
    return driver


class TestVerifySongAccess:
    def test_headless_raises_with_instructions(self):
        tm = TrackManager(_challenged_driver(), Mock())
        with pytest.raises(BotChallengeError, match="--debug"):
            tm.verify_song_access(SONG_URL)

    def test_solver_clears_challenge_then_verifies(self):
        driver = _challenged_driver()

        def solve():
            driver.title = "White Room - Cream"
            driver.find_elements.return_value = [Mock(), Mock()]

        solver = Mock(side_effect=solve)
        tm = TrackManager(driver, Mock(), challenge_solver=solver)
        assert tm.verify_song_access(SONG_URL) is True
        solver.assert_called_once()

    def test_solver_error_propagates(self):
        solver = Mock(side_effect=BotChallengeError("not solved in time"))
        tm = TrackManager(_challenged_driver(), Mock(), challenge_solver=solver)
        with pytest.raises(BotChallengeError, match="not solved"):
            tm.verify_song_access(SONG_URL)

    def test_still_challenged_after_solver_raises(self):
        # Guards against a solve loop if the clearance doesn't carry over.
        tm = TrackManager(_challenged_driver(), Mock(), challenge_solver=Mock())
        with pytest.raises(BotChallengeError):
            tm.verify_song_access(SONG_URL)


def _challenge_response():
    r = MagicMock()
    r.status_code = 200
    r.text = CHALLENGE_HTML
    return r


def _make_dl(session):
    return DirectDownloader(
        session,
        {"prodid": "1", "s": "2", "famid": "5", "precount": "1", "pitch": "0"},
        [MixerTrack(index=0, src_id=1, is_click=True, description="Click"),
         MixerTrack(index=1, src_id=2, is_click=False, description="Bass")],
        SONG_URL,
    )


class TestDirectDownloaderChallenge:
    def test_challenged_begin_download_raises(self, tmp_path):
        session = MagicMock()
        session.get.return_value = _challenge_response()
        with pytest.raises(BotChallengeError):
            _make_dl(session).download_track(
                target_index=1, dest=tmp_path / "x.mp3", max_wait=1,
            )

    def test_challenged_basket_raises(self):
        session = MagicMock()
        session.get.return_value = _challenge_response()
        with pytest.raises(BotChallengeError):
            _make_dl(session)._call_basket("1,0.2,100")


class TestAutomatorChallengeHandling:
    def setup_method(self):
        with patch('karaoke_automator.ConfigurationManager'), \
             patch('karaoke_automator.ChromeManager'), \
             patch('karaoke_automator.LoginManager'), \
             patch('karaoke_automator.ProgressTracker'), \
             patch('karaoke_automator.StatsReporter'), \
             patch('karaoke_automator.FileManager'), \
             patch('karaoke_automator.TrackManager') as tm_cls, \
             patch('karaoke_automator.DownloadManager'):
            from karaoke_automator import KaraokeVersionAutomator
            self.tm_cls = tm_cls
            self.automator = KaraokeVersionAutomator(headless=False)
        self.automator.track_manager = Mock()
        self.automator.driver = Mock()
        self.automator.driver.get_cookies.return_value = [
            {"name": "_fs_ch_st_x", "value": "fresh"},
        ]
        self.song = {'name': 'White Room', 'url': SONG_URL}
        self.track = {'name': 'Bass', 'index': '1'}
        self.session = MagicMock()

    def _retry(self, download):
        self.automator._download_single_track_direct_api = download
        return self.automator._download_track_direct_api_clearing_challenge(
            self.song, self.track, 0, Mock(), Mock(), self.session,
            max_wait=25.0,
        )

    def test_track_manager_gets_the_automator_solver(self):
        assert (self.tm_cls.call_args.kwargs["challenge_solver"]
                == self.automator._solve_bot_challenge)

    def test_mid_song_challenge_reverifies_refreshes_cookies_and_retries(self):
        download = Mock(side_effect=[BotChallengeError("basket.php"), True])
        assert self._retry(download) is True
        self.automator.track_manager.verify_song_access.assert_called_once_with(SONG_URL)
        self.session.cookies.set.assert_called_once_with("_fs_ch_st_x", "fresh")
        assert download.call_count == 2

    def test_second_challenge_switches_run_to_browser_downloads(self):
        # Seen live 2026-10-13: once the ~1h Fastly clearance expired, the
        # browser was trusted but plain HTTP stayed challenged, with no
        # CAPTCHA anywhere for the user to solve.
        download = Mock(side_effect=BotChallengeError("basket.php"))
        self.automator._download_single_track = Mock()
        self._retry(download)
        assert download.call_count == 2
        self.automator._download_single_track.assert_called_once_with(
            self.song, self.track, 0
        )
        assert self.automator.direct_api is False

    def test_challenged_browser_still_stops_instead_of_falling_back(self):
        download = Mock(side_effect=BotChallengeError("basket.php"))
        self.automator.track_manager.verify_song_access.side_effect = (
            BotChallengeError("CAPTCHA not solved")
        )
        self.automator._download_single_track = Mock()
        with pytest.raises(BotChallengeError):
            self._retry(download)
        self.automator._download_single_track.assert_not_called()
        assert self.automator.direct_api is True

    def test_rest_of_song_uses_browser_after_switch(self):
        tracks = [{'name': n, 'index': str(i)} for i, n in enumerate(["Click", "Bass", "Drums"])]
        self.automator._download_single_track_direct_api = Mock(
            side_effect=BotChallengeError("basket.php")
        )
        self.automator._download_single_track = Mock()
        self.automator.file_manager = Mock()
        ctx = Mock(template_params={"prodid": "1", "s": "2"}, cookies={}, ua="UA",
                   mixer_tracks=[])
        with patch("packages.download_management.direct_api.session_capture.capture_session",
                   return_value=ctx), \
             patch("packages.download_management.direct_api.direct_downloader.DirectDownloader") as dl_cls, \
             patch("karaoke_automator.time.sleep"):
            dl_cls.return_value.label_unverified = 0
            self.automator._download_all_tracks_direct_api(self.song, tracks, 0)
        assert self.automator._download_single_track_direct_api.call_count == 2
        assert [c.args[1]['name'] for c in self.automator._download_single_track.call_args_list] == [
            "Click", "Bass", "Drums"
        ]

    def test_challenge_stops_the_batch(self):
        self.automator._setup_automation_session = Mock(return_value=True)
        self.automator.load_songs_config = Mock(return_value=[self.song, self.song])
        self.automator._process_single_song = Mock(
            side_effect=BotChallengeError("bot check")
        )
        self.automator._generate_final_reports = Mock()
        self.automator._display_failure_summary = Mock()
        assert self.automator.run_automation() is False
        assert self.automator._process_single_song.call_count == 1


class TestCaptchaPopup:
    """Headless runs pop up a visible window for the user to solve the CAPTCHA,
    then go back to headless; --debug runs solve in the existing window."""

    def _automator(self, headless):
        with patch('karaoke_automator.ConfigurationManager'), \
             patch('karaoke_automator.ChromeManager'), \
             patch('karaoke_automator.LoginManager'), \
             patch('karaoke_automator.ProgressTracker'), \
             patch('karaoke_automator.StatsReporter'), \
             patch('karaoke_automator.FileManager'), \
             patch('karaoke_automator.TrackManager'), \
             patch('karaoke_automator.DownloadManager'):
            from karaoke_automator import KaraokeVersionAutomator
            a = KaraokeVersionAutomator(headless=headless)
        a.driver = Mock(current_url=SONG_URL)
        a.chrome_manager = Mock(headless=headless)
        modes = []

        def setup_driver():
            modes.append(a.chrome_manager.headless)
            a.chrome_manager.driver = Mock(name=f"driver{len(modes)}")
            a.chrome_manager.wait = Mock()
        a.chrome_manager.setup_driver.side_effect = setup_driver
        a.login_handler, a.track_manager, a.download_manager = Mock(), Mock(), Mock()
        return a, modes

    def test_headless_pops_up_window_then_returns_to_headless(self):
        a, modes = self._automator(headless=True)
        with patch("karaoke_automator.wait_for_clearance", return_value=True) as wait, \
             patch("karaoke_automator.notify_user") as notify:
            a._solve_bot_challenge()
        assert modes == [False, True]
        notify.assert_called_once()
        wait.assert_called_once()
        assert a.chrome_manager.quit.call_count == 2
        for component in (a.login_handler, a.track_manager, a.download_manager):
            assert component.driver is a.driver
        a.driver.get.assert_called_once_with(SONG_URL)

    def test_unsolved_still_returns_to_headless_and_raises(self):
        a, modes = self._automator(headless=True)
        with patch("karaoke_automator.wait_for_clearance", return_value=False), \
             patch("karaoke_automator.notify_user"):
            with pytest.raises(BotChallengeError):
                a._solve_bot_challenge()
        assert modes == [False, True]

    def test_visible_run_solves_in_place(self):
        a, modes = self._automator(headless=False)
        with patch("karaoke_automator.wait_for_clearance", return_value=True) as wait, \
             patch("karaoke_automator.notify_user") as notify:
            a._solve_bot_challenge()
        assert modes == []
        notify.assert_called_once()
        wait.assert_called_once()
