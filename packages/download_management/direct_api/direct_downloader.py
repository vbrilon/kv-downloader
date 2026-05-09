"""DirectDownloader — replaces the per-track Selenium download flow with
three HTTP calls (basket.php → begin_download.html polling → MP3 fetch).

Lifecycle:
    dl = DirectDownloader(session, template_params, song_url)
    for pos in (1, 2, 3, ...):
        result = dl.download_track(pos, dest=Path(...), max_wait=60)

The instance maintains `_last_hash` across calls so repeat downloads only
need to wait for the CDN URL hash to flip — no extra round-trips.

See `tools/probe_direct_api.py` for the original end-to-end probe that
validated this flow.
"""

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlencode

from .trackslevels import build_trackslevels

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------


class BasketUpdateError(RuntimeError):
    """basket.php returned a non-200 response. Includes URL + body excerpt."""


class MixGenTimeout(TimeoutError):
    """begin_download.html never reported a fresh CDN URL hash within the
    allotted time. Means server-side mix-gen is stalled or never fired."""


class MP3FetchError(RuntimeError):
    """The CDN MP3 GET failed (network error or 5xx)."""


class InvalidMP3UrlError(ValueError):
    """A CDN URL was missing the expected /sl/<key>/<hash>/ shape — fail
    fast rather than silently hang the polling loop."""


# ----------------------------------------------------------------------
# Pure helpers (also used by callers/tests)
# ----------------------------------------------------------------------


_MP3_URL_RE = re.compile(
    r'https?://c\d+\.recis\.io/sl/[^"\'<>\s]+\.mp3[^"\'<>\s]*',
    re.IGNORECASE,
)

_HASH_RE = re.compile(r"/sl/[^/]+/([a-f0-9]+)/", re.IGNORECASE)


def extract_mp3_url(html: Optional[str]) -> Optional[str]:
    """Pull the first c*.recis.io MP3 URL out of begin_download.html
    response. Returns None if the response doesn't contain one."""
    if not html:
        return None
    m = _MP3_URL_RE.search(html)
    return m.group(0) if m else None


def url_hash(url: Optional[str]) -> str:
    """Extract the per-mix hash from a CDN URL.

    Real shape: https://c1.recis.io/sl/k/aca6624e80abc111/file.mp3 → 'aca6624e80abc111'

    Raises InvalidMP3UrlError on missing/malformed URL — see plan-review
    concern #4 (silent None would cause infinite-poll hangs).
    """
    if not url:
        raise InvalidMP3UrlError(f"empty/None URL: {url!r}")
    m = _HASH_RE.search(url)
    if not m:
        raise InvalidMP3UrlError(
            f"URL does not match expected /sl/<key>/<hash>/ shape: {url!r}"
        )
    return m.group(1)


# ----------------------------------------------------------------------
# DirectDownloader
# ----------------------------------------------------------------------


@dataclass
class DownloadResult:
    path: Path
    url: str
    size_bytes: int
    elapsed_s: float


class DirectDownloader:
    BASKET_URL = "https://www.karaoke-version.com/basket.php"
    BEGIN_URL = "https://www.karaoke-version.com/my/begin_download.html"

    def __init__(self, session, template_params: Dict[str, str], song_url: str):
        self.session = session
        self.template_params = dict(template_params)
        self.song_url = song_url
        self._last_hash: Optional[str] = None

    # -- public --------------------------------------------------------

    def download_track(
        self,
        target_pos: int,
        dest: Path,
        *,
        max_wait: float = 60.0,
        poll_interval: float = 2.0,
        level: int = 100,
    ) -> DownloadResult:
        """Solo position `target_pos` on the server, wait for the mix to
        render, fetch the MP3 to `dest`."""
        t0 = time.monotonic()

        # 1. Snapshot baseline hash on first call.
        if self._last_hash is None:
            snap_url = self._begin_download_url()
            self._last_hash = url_hash(snap_url) if snap_url else None

        # 2. Overwrite the server-side basket with our trackslevels.
        new_levels = build_trackslevels(
            self.template_params["trackslevels"], target_pos, level=level
        )
        self._call_basket(new_levels)

        # 3. Poll begin_download.html until the CDN hash flips.
        new_url = self._poll_for_fresh_url(max_wait, poll_interval)
        new_hash = url_hash(new_url)

        # 4. Fetch the MP3 to disk.
        size = self._fetch_mp3(new_url, dest)

        self._last_hash = new_hash
        return DownloadResult(
            path=dest,
            url=new_url,
            size_bytes=size,
            elapsed_s=time.monotonic() - t0,
        )

    # -- internals -----------------------------------------------------

    def _begin_download_url(self) -> Optional[str]:
        """One GET against begin_download.html; return the embedded MP3
        URL (or None if absent)."""
        url = self._build_begin_url()
        r = self.session.get(url, timeout=30)
        return extract_mp3_url(r.text)

    def _build_begin_url(self) -> str:
        prodid = self.template_params["prodid"]
        famid = self.template_params.get("famid", "5")
        return (
            f"{self.BEGIN_URL}?id={prodid}&famid={famid}"
            f"&produced=1&method=ajax"
        )

    def _call_basket(self, trackslevels: str) -> None:
        params = dict(self.template_params)
        params["trackslevels"] = trackslevels
        url = self.BASKET_URL + "?" + urlencode(params, safe=",.-")
        r = self.session.get(url, timeout=30)
        if r.status_code != 200:
            body = (r.text or "")[:200]
            raise BasketUpdateError(
                f"basket.php returned {r.status_code} for trackslevels="
                f"{trackslevels[:80]!r}; body: {body!r}"
            )

    def _poll_for_fresh_url(
        self, max_wait: float, poll_interval: float
    ) -> str:
        """Poll until extract_mp3_url returns a URL whose hash differs
        from `self._last_hash`."""
        deadline = time.monotonic() + max_wait
        attempt = 0
        last_seen_url = None
        while True:
            attempt += 1
            url = self._begin_download_url()
            if url:
                last_seen_url = url
                this_hash = url_hash(url)
                if self._last_hash is None or this_hash != self._last_hash:
                    return url
            if time.monotonic() >= deadline:
                raise MixGenTimeout(
                    f"begin_download.html did not return a fresh hash within "
                    f"{max_wait}s ({attempt} polls); last_url={last_seen_url!r}"
                )
            if poll_interval > 0:
                time.sleep(poll_interval)

    def _fetch_mp3(self, url: str, dest: Path) -> int:
        headers = {
            "Referer": "https://www.karaoke-version.com/",
            "Accept": "*/*",
        }
        try:
            with self.session.get(
                url, headers=headers, stream=True, timeout=180
            ) as r:
                if r.status_code != 200:
                    raise MP3FetchError(
                        f"CDN returned {r.status_code} for {url!r}"
                    )
                dest.parent.mkdir(parents=True, exist_ok=True)
                size = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
                        size += len(chunk)
                return size
        except MP3FetchError:
            raise
        except Exception as e:
            raise MP3FetchError(f"fetching {url!r} failed: {e}") from e
