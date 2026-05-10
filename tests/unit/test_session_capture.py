"""Unit tests for direct_api.session_capture.

Two layers:
  1. parse_mixer_script(script_source: str) -> dict — pure function that
     extracts basket params from the inline mixer-init script. This is
     where the regex bug surface lives, so it gets dense coverage.
  2. capture_session(driver, song_url, log) -> SessionContext — the
     Selenium glue. Light coverage with a mocked driver.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from packages.download_management.direct_api.session_capture import (
    parse_mixer_script,
    capture_session,
    SessionContext,
    CaptureError,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "mixer_init_script.js"
)


@pytest.fixture(scope="module")
def real_script() -> str:
    return FIXTURE.read_text()


# ----------------------------------------------------------------------
# parse_mixer_script
# ----------------------------------------------------------------------


class TestParseMixerScript:
    def test_extracts_all_params_from_real_fixture(self, real_script):
        params = parse_mixer_script(real_script)

        # All literals from the captured script.
        assert params["prodid"] == "21279320"
        assert params["s"] == "40852"
        assert params["bkac"] == "editf"
        assert params["pitch"] == "0"
        assert params["precount"] == "1"
        assert params["famid"] == "5"
        assert (
            params["pannings"]
            == "1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,-100.12,0.13,0"
        )
        assert (
            params["trackslevels"]
            == "1,0.2,0.3,100.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,0.12,0.13,0"
        )
        # method is hardcoded to "ajax" — the existing flow always uses
        # method=ajax for AJAX-driven basket updates.
        assert params["method"] == "ajax"

    def test_missing_setlevels_raises(self):
        bad = "function foo() { return 42; }"
        with pytest.raises(CaptureError) as exc:
            parse_mixer_script(bad)
        assert "setLevels" in str(exc.value) or "trackslevels" in str(exc.value).lower()

    def test_missing_setpannings_raises(self):
        bad = '''
            mixer.setLevels("1,0.2,0.3,0.4,0");
            mixer.parameters.bkac = "editf";
            mixer.parameters.s = 40852;
            mixer.parameters.prodid = 21279320;
            mixer.uri = '/my/begin_download.html?id=21279320&famid=5';
            mixer.setPitch("0");
            mixer.setPrecount("1");
        '''
        with pytest.raises(CaptureError) as exc:
            parse_mixer_script(bad)
        assert "pannings" in str(exc.value).lower()

    def test_missing_prodid_raises(self):
        bad = '''
            mixer.setLevels("1,0.2,0.3,0.4,0");
            mixer.setPannings("1,0.2,0.3,0.4,0");
            mixer.setPitch("0");
            mixer.setPrecount("1");
            mixer.parameters.bkac = "editf";
            mixer.parameters.s = 40852;
            mixer.uri = '/my/begin_download.html?famid=5';
        '''
        with pytest.raises(CaptureError) as exc:
            parse_mixer_script(bad)
        assert "prodid" in str(exc.value).lower()

    def test_handles_no_space_around_equals(self):
        # The real fixture has `mixer.parameters.s =40852;` — note the space
        # BEFORE = but not after. The parser must accept both forms.
        snippet = '''
            mixer.setLevels("1,0.2,0.3,0.4,0");
            mixer.setPannings("1,0.2,0.3,0.4,0");
            mixer.setPitch("0");
            mixer.setPrecount("1");
            mixer.parameters.bkac = "editf";
            mixer.parameters.s=40852;
            mixer.parameters.prodid=21279320;
            mixer.uri = '/my/begin_download.html?id=21279320&famid=5';
        '''
        params = parse_mixer_script(snippet)
        assert params["s"] == "40852"
        assert params["prodid"] == "21279320"

    def test_extracts_famid_from_uri(self):
        snippet = '''
            mixer.setLevels("1,0.2,0.3,0.4,0");
            mixer.setPannings("1,0.2,0.3,0.4,0");
            mixer.setPitch("0");
            mixer.setPrecount("1");
            mixer.parameters.bkac = "editf";
            mixer.parameters.s = 40852;
            mixer.parameters.prodid = 21279320;
            mixer.uri = '/my/begin_download.html?id=21279320&famid=7';
        '''
        params = parse_mixer_script(snippet)
        assert params["famid"] == "7"

    def test_method_always_ajax(self, real_script):
        # method isn't in the script source — it's hardcoded based on the
        # existing AJAX-driven download flow. Confirm we always emit "ajax".
        params = parse_mixer_script(real_script)
        assert params["method"] == "ajax"


# ----------------------------------------------------------------------
# capture_session
# ----------------------------------------------------------------------


# Synthetic mixer.tracks payload matching the 18-til-i-die fixture
# (13 tracks: Click + 12 real). Returned by the mocked execute_script
# call that reads window.mixer.tracks.
FAKE_MIXER_TRACKS_JS_RESULT = [
    {"index": i,
     "src_id": i + 1,
     "is_click": (i == 0),
     "description": f"Track {i}"}
    for i in range(13)
]


def _make_driver_for_capture(real_script, cookies=None,
                             current_url=None,
                             mixer_tracks_result=None,
                             ua="UA/1.0"):
    """Build a MagicMock driver that returns the right values for each
    execute_script call capture_session makes. Order:
      1. _FIND_SCRIPT_JS → inline script source
      2. _READ_MIXER_TRACKS_JS → mixer.tracks list (or None if absent)
      3. navigator.userAgent → ua string
    """
    driver = MagicMock()
    driver.current_url = (
        current_url or
        "https://www.karaoke-version.com/custombackingtrack/"
        "bryan-adams/18-til-i-die.html"
    )
    driver.get_cookies.return_value = cookies or []
    if mixer_tracks_result is None:
        mixer_tracks_result = FAKE_MIXER_TRACKS_JS_RESULT
    driver.execute_script.side_effect = [
        real_script,
        mixer_tracks_result,
        ua,
    ]
    return driver


class TestCaptureSession:
    def test_returns_session_context_with_real_inputs(self, real_script, tmp_path):
        driver = _make_driver_for_capture(
            real_script,
            cookies=[
                {"name": "session_id", "value": "abc123"},
                {"name": "csrf", "value": "xyz789"},
            ],
        )

        ctx = capture_session(
            driver,
            song_url=driver.current_url,
            log=MagicMock(),
        )

        assert isinstance(ctx, SessionContext)
        assert ctx.cookies == {"session_id": "abc123", "csrf": "xyz789"}
        assert ctx.template_params["prodid"] == "21279320"
        assert ctx.template_params["trackslevels"].startswith("1,0.2")
        assert ctx.template_params["method"] == "ajax"
        assert ctx.ua == "UA/1.0"
        assert len(ctx.mixer_tracks) == 13
        assert ctx.mixer_tracks[0].is_click is True
        assert ctx.mixer_tracks[1].src_id == 2

    def test_navigates_when_not_on_song_page(self, real_script):
        driver = _make_driver_for_capture(
            real_script,
            current_url="https://www.karaoke-version.com/somewhere-else",
        )

        target_url = (
            "https://www.karaoke-version.com/custombackingtrack/"
            "bryan-adams/18-til-i-die.html"
        )
        capture_session(driver, song_url=target_url, log=MagicMock())

        driver.get.assert_called_with(target_url)

    def test_does_not_navigate_when_already_on_song_page(self, real_script):
        target_url = (
            "https://www.karaoke-version.com/custombackingtrack/"
            "bryan-adams/18-til-i-die.html"
        )
        driver = _make_driver_for_capture(real_script, current_url=target_url)

        capture_session(driver, song_url=target_url, log=MagicMock())
        driver.get.assert_not_called()

    def test_raises_when_inline_script_not_found(self):
        driver = MagicMock()
        driver.current_url = "https://www.karaoke-version.com/x"
        driver.execute_script.return_value = None  # no script found
        driver.get_cookies.return_value = []

        with pytest.raises(CaptureError):
            capture_session(driver, song_url="https://x", log=MagicMock())

    def test_raises_when_mixer_tracks_never_populates(self, real_script):
        # First call returns the inline script; subsequent reads return
        # None. _read_mixer_tracks should poll-then-give-up.
        driver = MagicMock()
        driver.current_url = (
            "https://www.karaoke-version.com/custombackingtrack/"
            "bryan-adams/18-til-i-die.html"
        )
        driver.get_cookies.return_value = []
        # Order: 1 script-source call, then unbounded mixer.tracks polls
        # (all None), no UA call (we never get there).
        driver.execute_script.side_effect = (
            [real_script] + [None] * 100
        )

        # Patch the polling deadline to 0 so the test is fast.
        from packages.download_management.direct_api import session_capture
        orig = session_capture._read_mixer_tracks
        try:
            session_capture._read_mixer_tracks = lambda d, l, max_wait=0.1: orig(
                d, l, max_wait=0.1
            )
            with pytest.raises(CaptureError) as exc:
                capture_session(
                    driver,
                    song_url=driver.current_url,
                    log=MagicMock(),
                )
            assert "mixer.tracks" in str(exc.value)
        finally:
            session_capture._read_mixer_tracks = orig
