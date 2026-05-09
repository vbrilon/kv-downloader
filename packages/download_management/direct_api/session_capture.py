"""Capture an authenticated `requests.Session` view of a karaoke-version
song page — cookies, UA, and the basket.php template params — by reading
the inline mixer-init script (no UI download click needed).

See docs/plans/2026-05-08-direct-api-rewrite.md (Phase 2, Q1 resolved)
for design rationale.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class CaptureError(RuntimeError):
    """The mixer init script could not be located or parsed. Caller
    should fall back to legacy Selenium download path."""


@dataclass
class SessionContext:
    cookies: Dict[str, str]
    template_params: Dict[str, str]
    ua: Optional[str] = None


# ----------------------------------------------------------------------
# Pure parser
# ----------------------------------------------------------------------


# All regexes are written for the verified shape captured 2026-05-08
# from bryan-adams/18-til-i-die. They tolerate variations in whitespace
# but not structural changes — if the site changes how it embeds these
# values, we fail loudly via CaptureError.
_RE_SETLEVELS = re.compile(r'mixer\.setLevels\(\s*"([^"]+)"\s*\)')
_RE_SETPANNINGS = re.compile(r'mixer\.setPannings\(\s*"([^"]+)"\s*\)')
_RE_SETPITCH = re.compile(r'mixer\.setPitch\(\s*"([^"]+)"\s*\)')
_RE_SETPRECOUNT = re.compile(r'mixer\.setPrecount\(\s*"([^"]+)"\s*\)')
_RE_BKAC = re.compile(r'mixer\.parameters\.bkac\s*=\s*"([^"]+)"')
_RE_S = re.compile(r'mixer\.parameters\.s\s*=\s*(\d+)')
_RE_PRODID = re.compile(r'mixer\.parameters\.prodid\s*=\s*(\d+)')
_RE_FAMID_IN_URI = re.compile(r'famid=(\d+)')


def parse_mixer_script(source: str) -> Dict[str, str]:
    """Extract basket.php template params from the inline mixer init
    script. Raises CaptureError on any missing field."""
    if not source:
        raise CaptureError("mixer init script source is empty")

    out: Dict[str, str] = {"method": "ajax"}

    fields = [
        ("trackslevels", _RE_SETLEVELS, "mixer.setLevels(...)"),
        ("pannings", _RE_SETPANNINGS, "mixer.setPannings(...)"),
        ("pitch", _RE_SETPITCH, "mixer.setPitch(...)"),
        ("precount", _RE_SETPRECOUNT, "mixer.setPrecount(...)"),
        ("bkac", _RE_BKAC, "mixer.parameters.bkac"),
        ("s", _RE_S, "mixer.parameters.s"),
        ("prodid", _RE_PRODID, "mixer.parameters.prodid"),
        ("famid", _RE_FAMID_IN_URI, "famid=N inside mixer.uri"),
    ]
    for key, regex, hint in fields:
        m = regex.search(source)
        if not m:
            raise CaptureError(
                f"could not extract {key!r} from mixer script "
                f"(expected pattern: {hint})"
            )
        out[key] = m.group(1)

    return out


# ----------------------------------------------------------------------
# Selenium glue
# ----------------------------------------------------------------------


# Returns the full text content of every inline <script> that contains
# `mixer.setLevels` (the marker for the per-page mixer init script).
# Joining with a newline keeps line numbers approximately right for any
# diagnostic output.
_FIND_SCRIPT_JS = """
const scripts = Array.from(document.querySelectorAll('script:not([src])'));
const matches = scripts.map(s => s.textContent || '')
                       .filter(t => t.includes('mixer.setLevels'));
return matches.length ? matches.join('\\n') : null;
"""


def capture_session(
    driver,
    song_url: str,
    log: Optional[logging.Logger] = None,
) -> SessionContext:
    """Read everything DirectDownloader needs from the song page.

    Pre-condition: `driver` is logged in (via LoginManager). Navigation
    to `song_url` happens here if not already on that page.
    """
    log = log or logging.getLogger(__name__)

    if driver.current_url != song_url:
        log.info(f"capture_session: navigating to {song_url}")
        driver.get(song_url)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".track"))
            )
        except Exception:
            # If track elements never appear we won't find the mixer
            # script either — let the next step raise CaptureError with
            # a clearer message.
            log.warning("capture_session: .track element never appeared")

    script_source = driver.execute_script(_FIND_SCRIPT_JS)
    if not script_source:
        raise CaptureError(
            "no inline <script> on page contains 'mixer.setLevels' — "
            "site structure may have changed"
        )

    template_params = parse_mixer_script(script_source)
    log.info(
        f"capture_session: parsed template_params keys="
        f"{sorted(template_params.keys())}"
    )

    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    log.info(f"capture_session: snapshotted {len(cookies)} cookies")

    try:
        ua = driver.execute_script("return navigator.userAgent;")
    except Exception as e:
        log.warning(f"capture_session: could not read userAgent: {e}")
        ua = None

    return SessionContext(
        cookies=cookies,
        template_params=template_params,
        ua=ua,
    )
