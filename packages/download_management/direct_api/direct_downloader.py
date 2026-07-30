"""DirectDownloader — replaces the per-track Selenium download flow with
three HTTP calls (basket.php → begin_download.html polling → MP3 fetch).

Lifecycle:
    dl = DirectDownloader(session, template_params, mixer_tracks, song_url)
    for K in range(len(mixer_tracks)):
        result = dl.download_track(target_index=K, dest=Path(...), max_wait=60)

The instance maintains `_last_hash` across calls so repeat downloads only
need to wait for the CDN URL hash to flip — no extra round-trips.

A render is accepted only when it is BOTH fresh (hash differs from the last
download) AND identified as the requested track by the server's own filename
label. Hash-freshness alone is not sufficient: under server congestion the
site can return a NEW hash carrying the PREVIOUS track's audio, which used to
be saved silently under the requested track's name (2026-07-30; see
docs/plans/2026-07-30-verify-track-identity.md). When the label cannot be
resolved the downloader falls back to hash-only and counts the track in
`label_unverified` rather than failing.

`target_index` is the DOM data-index (== position in mixer.tracks); the
trackslevels position used internally is target_index + 1 (the Mixer JS
class uses N positions for N tracks, with a leading bare flag at pos 0).
This off-by-one mapping was verified empirically — see
docs/site-flow/trackslevels-format.md.
"""

import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote, urlencode

from .trackslevels import MixerTrack, build_trackslevels

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


class TrackMismatchError(RuntimeError):
    """The server rendered a track other than the one requested, and kept
    doing so until the deadline. Distinct from MixGenTimeout (server
    stalled) so logs and stats can tell the two apart."""


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


# The server names each rendered MP3 after the track it soloed:
#   Toto_Hold_the_Line(Lead_Electric_Guitar_Custom_Backing_Track).mp3
# This is the server's authoritative statement of what it rendered — see
# docs/investigations/2026-05-09-direct-api-mapping-precount-cascade.md §1.
_LABEL_SUFFIX = "_custom_backing_track)"


def extract_filename(url: Optional[str]) -> Optional[str]:
    """Return the URL-decoded filename component of a CDN URL."""
    if not url:
        return None
    return unquote(url.split("?")[0].rsplit("/", 1)[-1])


def extract_track_label(url: Optional[str]) -> Optional[str]:
    """Pull the server's track label out of a CDN URL filename.

    Returns None when the filename carries no label — callers must treat
    that as "unknown", never as a mismatch.

    Anchors on the fixed `_Custom_Backing_Track)` suffix and walks BACKWARD
    with a paren-depth counter to find the balancing '('. A regex anchored
    on the leftmost '(' would capture garbage for songs whose *title*
    contains parentheses, e.g.
    `Ricky_Livin_la_Vida_Loca_(Radio_Edit)(Bass_Custom_Backing_Track).mp3`.
    """
    fname = extract_filename(url)
    if not fname or not fname.lower().endswith(".mp3"):
        return None

    stem = fname[:-4]
    if not stem.lower().endswith(_LABEL_SUFFIX):
        return None

    end = len(stem) - len(_LABEL_SUFFIX)
    depth = 0
    for i in range(end - 1, -1, -1):
        char = stem[i]
        if char == ")":
            depth += 1
        elif char == "(":
            if depth == 0:
                return stem[i + 1:end].replace("_", " ").strip() or None
            depth -= 1
    return None


def normalize_label(text: Optional[str]) -> str:
    """Fold a track name to a comparable form: accents stripped to ASCII,
    lowercased, non-alphanumerics removed. Makes '_' vs ' ' vs '()' and
    server-side transliteration irrelevant."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return "".join(c for c in stripped.lower() if c.isalnum())


def identify_track(
    label: Optional[str], mixer_tracks: List[MixerTrack]
) -> Optional[int]:
    """Resolve a server track label to a DOM index, or None if it cannot be
    resolved *unambiguously*.

    Exact match first, then containment — each accepted only when exactly
    one track matches. Both steps are needed:

    - Exact-only fails the click track: the server says "Click" while
      mixer.tracks[0].description is "Intro count Click".
    - Containment-only picks the wrong track when one name contains
      another ("Lead Vocal" vs "Lead Vocal (ad lib)"); the exact pass
      claims those first.

    None means "don't know" — the caller falls back rather than rejecting.
    """
    needle = normalize_label(label)
    if not needle:
        return None

    exact = [t.index for t in mixer_tracks
             if normalize_label(t.description) == needle]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return None  # duplicate descriptions — ambiguous

    partial = [t.index for t in mixer_tracks
               if needle in normalize_label(t.description)]
    return partial[0] if len(partial) == 1 else None


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
    # The server's own label for what it rendered, or None when the
    # filename carried no resolvable label (hash-only fallback).
    server_label: Optional[str] = None


class DirectDownloader:
    BASKET_URL = "https://www.karaoke-version.com/basket.php"
    BEGIN_URL = "https://www.karaoke-version.com/my/begin_download.html"

    def __init__(
        self,
        session,
        template_params: Dict[str, str],
        mixer_tracks: List[MixerTrack],
        song_url: str,
    ):
        self.session = session
        self.template_params = dict(template_params)
        self.mixer_tracks = mixer_tracks
        self.song_url = song_url
        self._last_hash: Optional[str] = None
        self._last_filename: Optional[str] = None
        # Per-session tallies so a run can report how many tracks were
        # actually identity-verified vs accepted on the hash-only fallback.
        self.label_verified = 0
        self.label_unverified = 0

    # -- public --------------------------------------------------------

    def download_track(
        self,
        target_index: int,
        dest: Path,
        *,
        max_wait: float = 60.0,
        poll_interval: float = 2.0,
        level: int = 100,
        fetch_max_attempts: int = 3,
        fetch_retry_backoff: float = 1.0,
    ) -> DownloadResult:
        """Solo `mixer_tracks[target_index]` on the server, wait for the
        mix to render, fetch the MP3 to `dest`. Transient CDN failures
        are retried up to `fetch_max_attempts` times with exponential
        backoff (`fetch_retry_backoff` * 2**attempt)."""
        t0 = time.monotonic()

        # 1. Snapshot baseline hash on first call.
        if self._last_hash is None:
            snap_url = self._begin_download_url()
            self._last_hash = url_hash(snap_url) if snap_url else None

        # 2. Overwrite the server-side basket with our trackslevels.
        new_levels = build_trackslevels(
            self.mixer_tracks, target_index=target_index, level=level
        )
        self._call_basket(new_levels)

        # 3. Poll begin_download.html until the server reports a fresh
        #    render that it identifies as the track we asked for.
        new_url = self._poll_for_fresh_url(
            max_wait, poll_interval, target_index, new_levels
        )
        new_hash = url_hash(new_url)

        # 4. Fetch the MP3 to disk (with transient-failure retries).
        size = self._fetch_mp3_with_retry(
            new_url, dest, fetch_max_attempts, fetch_retry_backoff
        )

        self._last_hash = new_hash
        self._last_filename = extract_filename(new_url)
        return DownloadResult(
            path=dest,
            url=new_url,
            size_bytes=size,
            elapsed_s=time.monotonic() - t0,
            server_label=extract_track_label(new_url),
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
        self,
        max_wait: float,
        poll_interval: float,
        target_index: int,
        trackslevels: str,
    ) -> str:
        """Poll until the server reports a render that is BOTH fresh (hash
        differs from the last download) AND identified as `target_index`.

        Freshness and identity are orthogonal gates and both are required:
        the hash stops a *stale* render being taken, the label stops a
        *fresh render of the wrong track* — the defect this method exists
        to close.

        Classification happens only on fresh-hash sightings. During normal
        polling the cart still holds the PREVIOUS track's render; judging
        those by label would flag every ordinary slow render as a mismatch
        and destroy the stall/mismatch distinction.
        """
        deadline = time.monotonic() + max_wait
        attempt = 0
        last_seen_url = None
        mismatch_label = None
        rebasket_sent = False
        warned_unknown = False

        while True:
            attempt += 1
            url = self._begin_download_url()
            if url:
                last_seen_url = url
                this_hash = url_hash(url)
                is_fresh = (
                    self._last_hash is None or this_hash != self._last_hash
                )
                if is_fresh:
                    label = extract_track_label(url)
                    identified = identify_track(label, self.mixer_tracks)

                    if identified == target_index:
                        self.label_verified += 1
                        return url

                    if identified is not None:
                        # Fresh render of a DIFFERENT track — the bug.
                        mismatch_label = label
                        if not rebasket_sent:
                            logger.warning(
                                f"server rendered {label!r} but "
                                f"{self._target_name(target_index)!r} was "
                                f"requested — re-issuing basket.php"
                            )
                            self._call_basket(trackslevels)
                            rebasket_sent = True
                    elif label is not None:
                        # Parsed, but names no known track: format drift.
                        # An identical filename means identical cart
                        # content, so keep waiting.
                        if extract_filename(url) != self._last_filename:
                            self._warn_unverified(warned_unknown, label)
                            warned_unknown = True
                            self.label_unverified += 1
                            return url
                    else:
                        # No label at all — legacy/unknown filename shape.
                        # Fall back to hash-only (previous behaviour).
                        self._warn_unverified(warned_unknown, None)
                        warned_unknown = True
                        self.label_unverified += 1
                        return url

            if time.monotonic() >= deadline:
                # Record what we last saw, so the NEXT track cannot mistake
                # this render for a fresh one on the fallback path.
                if last_seen_url:
                    self._last_hash = url_hash(last_seen_url)
                if mismatch_label:
                    raise TrackMismatchError(
                        f"server kept rendering {mismatch_label!r} when "
                        f"{self._target_name(target_index)!r} was requested "
                        f"({attempt} polls, {max_wait}s); refusing to save "
                        f"wrong-track audio"
                    )
                raise MixGenTimeout(
                    f"begin_download.html did not return a fresh hash within "
                    f"{max_wait}s ({attempt} polls); last_url={last_seen_url!r}"
                )
            if poll_interval > 0:
                time.sleep(poll_interval)

    def _target_name(self, target_index: int) -> str:
        for track in self.mixer_tracks:
            if track.index == target_index:
                return track.description
        return f"index {target_index}"

    def _warn_unverified(self, already_warned: bool, label: Optional[str]) -> None:
        if already_warned:
            return
        detail = (
            f"label {label!r} matches no known track"
            if label else "filename carries no track label"
        )
        logger.warning(
            f"track identity unverified ({detail}) — falling back to "
            f"hash-only freshness check"
        )

    def _fetch_mp3_with_retry(
        self,
        url: str,
        dest: Path,
        max_attempts: int,
        backoff: float,
    ) -> int:
        last_err: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                return self._fetch_mp3(url, dest)
            except MP3FetchError as e:
                last_err = e
                if attempt < max_attempts:
                    sleep_s = backoff * (2 ** (attempt - 1))
                    logger.warning(
                        f"MP3 fetch attempt {attempt}/{max_attempts} failed: "
                        f"{e}; retrying in {sleep_s:.1f}s"
                    )
                    if sleep_s > 0:
                        time.sleep(sleep_s)
        raise MP3FetchError(
            f"MP3 fetch failed after {max_attempts} attempts: {last_err}"
        ) from last_err

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
