"""Capture an authenticated `requests.Session` view of a karaoke-version
song page — cookies, UA, basket.php template params, AND the page's
canonical mixer.tracks list — by reading inline scripts and probing
window.mixer (no UI download click needed).

See docs/plans/2026-05-08-direct-api-rewrite.md (Phase 2, Q1 resolved)
for the basket-template capture rationale, and 2026-05-09-track-mapping-fix.md
for the mixer.tracks addition (closes the off-by-one position bug).
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .trackslevels import MixerTrack


class CaptureError(RuntimeError):
    """The mixer init script could not be located or parsed, or
    window.mixer.tracks did not populate. Caller should fall back to
    legacy Selenium download path."""


@dataclass
class SessionContext:
    cookies: Dict[str, str]
    template_params: Dict[str, str]
    mixer_tracks: List[MixerTrack] = field(default_factory=list)
    ua: Optional[str] = None


# ----------------------------------------------------------------------
# Pure parser (static inline-script scrape)
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


# Reads window.mixer.tracks (the page's canonical track list, populated
# by the Mixer JS class once the page initializes). For each track,
# returns its DOM index, the source-track id (extracted from the per-
# track audio URL like ".../2.mp3" → src_id=2), the isClick flag, and
# a cleaned text description.
_READ_MIXER_TRACKS_JS = r"""
const m = window.mixer;
if (!m || !m.tracks || m.tracks.length === 0) return null;
return m.tracks.map(t => {
  let srcId = -1;
  if (t.url) {
    const match = t.url.match(/\/(\d+)\.mp3/);
    if (match) srcId = parseInt(match[1], 10);
  }
  return {
    index: t.index,
    src_id: srcId,
    is_click: !!t.isClick,
    description: typeof t.description === 'string'
      ? t.description.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
      : '',
  };
});
"""


def _read_mixer_tracks(driver, log, max_wait: float = 10.0) -> List[MixerTrack]:
    """Poll window.mixer.tracks until populated. The Mixer JS class
    builds the tracks array asynchronously after the inline init script
    runs — usually within ~100ms but allow up to max_wait for slow
    pages."""
    deadline = time.monotonic() + max_wait
    last_err: Optional[str] = None
    while time.monotonic() < deadline:
        try:
            result = driver.execute_script(_READ_MIXER_TRACKS_JS)
        except Exception as e:
            last_err = str(e)
            result = None
        if result:
            tracks = [MixerTrack(**r) for r in result]
            invalid = [t for t in tracks if t.src_id < 0]
            if invalid:
                raise CaptureError(
                    f"mixer.tracks contained {len(invalid)} entries with "
                    f"unparseable src_id (URLs missing /<N>.mp3 pattern); "
                    f"first: index={invalid[0].index} desc={invalid[0].description!r}"
                )
            log.info(
                f"capture_session: read {len(tracks)} mixer.tracks "
                f"(src_ids={[t.src_id for t in tracks]})"
            )
            return tracks
        time.sleep(0.2)
    raise CaptureError(
        f"window.mixer.tracks not populated within {max_wait}s "
        f"(last_err={last_err!r}) — page structure may have changed"
    )


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

    mixer_tracks = _read_mixer_tracks(driver, log)

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
        mixer_tracks=mixer_tracks,
        ua=ua,
    )
