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


class TestCaptureSession:
    def test_returns_session_context_with_real_inputs(self, real_script, tmp_path):
        # Mock the driver: returns the real script for execute_script,
        # cookies, and userAgent.
        driver = MagicMock()
        driver.current_url = (
            "https://www.karaoke-version.com/custombackingtrack/"
            "bryan-adams/18-til-i-die.html"
        )

        def fake_execute_script(js, *args):
            # capture_session calls execute_script to find the mixer init
            # script source (we don't care about exact JS string; just
            # return the fixture).
            return real_script

        driver.execute_script.side_effect = fake_execute_script
        driver.get_cookies.return_value = [
            {"name": "session_id", "value": "abc123"},
            {"name": "csrf", "value": "xyz789"},
        ]

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
        # User-agent comes from `navigator.userAgent` on the second
        # execute_script call. Mock returns the same fixture for both
        # calls; document this as a known mock simplification rather
        # than asserting on the value.
        assert ctx.ua is not None

    def test_navigates_when_not_on_song_page(self, real_script):
        driver = MagicMock()
        driver.current_url = "https://www.karaoke-version.com/somewhere-else"
        driver.execute_script.return_value = real_script
        driver.get_cookies.return_value = []

        target_url = (
            "https://www.karaoke-version.com/custombackingtrack/"
            "bryan-adams/18-til-i-die.html"
        )
        capture_session(driver, song_url=target_url, log=MagicMock())

        # Must navigate to the song page before reading the script.
        driver.get.assert_called_with(target_url)

    def test_does_not_navigate_when_already_on_song_page(self, real_script):
        driver = MagicMock()
        target_url = (
            "https://www.karaoke-version.com/custombackingtrack/"
            "bryan-adams/18-til-i-die.html"
        )
        driver.current_url = target_url
        driver.execute_script.return_value = real_script
        driver.get_cookies.return_value = []

        capture_session(driver, song_url=target_url, log=MagicMock())
        driver.get.assert_not_called()

    def test_raises_when_inline_script_not_found(self):
        driver = MagicMock()
        driver.current_url = "https://www.karaoke-version.com/x"
        driver.execute_script.return_value = None  # no script found
        driver.get_cookies.return_value = []

        with pytest.raises(CaptureError):
            capture_session(driver, song_url="https://x", log=MagicMock())
