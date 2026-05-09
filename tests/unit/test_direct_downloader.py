"""Unit tests for direct_api.direct_downloader.DirectDownloader.

DirectDownloader replaces the per-track Selenium download flow with three
HTTP calls:

  1. GET /basket.php?...&trackslevels=<built>  (overwrites server basket)
  2. GET /my/begin_download.html?id=<prodid>&famid=5...
     (poll until the embedded MP3 URL's hash changes — that's the signal
     that server-side mix-gen finished)
  3. GET https://c*.recis.io/sl/.../<hash>/<filename>.mp3
     (stream MP3 to disk)

The downloader is constructed once per session with `template_params`
captured by `session_capture` and a `requests.Session` carrying the
authenticated cookies. Every call thereafter is just-HTTP — no Selenium.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from packages.download_management.direct_api.direct_downloader import (
    DirectDownloader,
    BasketUpdateError,
    MixGenTimeout,
    MP3FetchError,
    InvalidMP3UrlError,
    extract_mp3_url,
    url_hash,
)


# Real basket-template params captured 2026-05-08 from
# bryan-adams/18-til-i-die. trackslevels here is the TEMPLATE (carries
# the bare-numeric edges); per-track basket calls override it.
TEMPLATE_PARAMS = {
    "prodid": "21279320",
    "s": "40852",
    "bkac": "editf",
    "famid": "5",
    "method": "ajax",
    "pannings": "1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,-100.12,0.13,0",
    "pitch": "0",
    "precount": "1",
    "trackslevels": "1,0.2,0.3,100.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,0.12,0.13,0",
}
SONG_URL = "https://www.karaoke-version.com/custombackingtrack/bryan-adams/18-til-i-die.html"

CDN_URL_OLD = "https://c1.recis.io/sl/k/aca6624e80abc111/Bryan_Adams_18_til_I_Die.mp3"
CDN_URL_NEW = "https://c1.recis.io/sl/k/bbb1234567ffeedd/Bryan_Adams_18_til_I_Die.mp3"
HASH_OLD = "aca6624e80abc111"
HASH_NEW = "bbb1234567ffeedd"


# ----------------------------------------------------------------------
# Pure helpers
# ----------------------------------------------------------------------


class TestUrlHash:
    def test_extracts_hash_from_real_url(self):
        assert url_hash(CDN_URL_OLD) == HASH_OLD

    def test_extracts_from_url_with_query_string(self):
        url = CDN_URL_OLD + "?token=xyz"
        assert url_hash(url) == HASH_OLD

    def test_raises_on_url_without_hash(self):
        # Per concern #4 from plan review: fail fast, don't silently hang
        # the polling loop.
        with pytest.raises(InvalidMP3UrlError):
            url_hash("https://example.com/no-hash-here.mp3")

    def test_raises_on_empty(self):
        with pytest.raises(InvalidMP3UrlError):
            url_hash("")

    def test_raises_on_none(self):
        with pytest.raises(InvalidMP3UrlError):
            url_hash(None)


class TestExtractMp3Url:
    def test_extracts_from_modal_html(self):
        # Real shape from begin_download.html response (verbatim from
        # probe_direct_api logs).
        html = (
            '<div class="modal__content"><a class="begin-download" '
            f'href="{CDN_URL_OLD}">Click here to download</a></div>'
        )
        assert extract_mp3_url(html) == CDN_URL_OLD

    def test_returns_none_when_no_mp3_url(self):
        assert extract_mp3_url("<html>nothing</html>") is None

    def test_returns_none_for_empty(self):
        assert extract_mp3_url("") is None
        assert extract_mp3_url(None) is None


# ----------------------------------------------------------------------
# DirectDownloader integration with mocked Session
# ----------------------------------------------------------------------


def _mock_response(status_code=200, text="", content=b""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.content = content
    r.raise_for_status = (
        MagicMock(side_effect=Exception(f"HTTP {status_code}"))
        if status_code >= 400
        else MagicMock()
    )
    # Stream support
    r.iter_content = lambda chunk_size: iter([content])
    r.__enter__ = lambda self: self
    r.__exit__ = lambda self, *a: None
    return r


def _begin_download_html(cdn_url):
    return f'<div class="modal__content"><a href="{cdn_url}">DL</a></div>'


class TestDirectDownloaderHappyPath:
    def test_download_track_full_flow(self, tmp_path):
        session = MagicMock()
        # The downloader will:
        #   1. snapshot initial hash via begin_download (HASH_OLD)
        #   2. call basket.php → 200
        #   3. poll begin_download until hash flips (HASH_NEW)
        #   4. fetch the MP3 bytes
        # We stage responses in order using `side_effect`.
        mp3_bytes = b"\xff\xfb\x90\x00fake-mp3-data" * 100
        session.get.side_effect = [
            # Call 1: initial snapshot
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            # Call 2: basket.php overwrite
            _mock_response(200, "ok"),
            # Call 3: first poll — hash hasn't flipped yet
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            # Call 4: second poll — hash flipped
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            # Call 5: MP3 fetch
            _mock_response(200, content=mp3_bytes),
        ]

        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        dest = tmp_path / "track.mp3"
        result = dl.download_track(target_pos=3, dest=dest, poll_interval=0.0)

        assert result.path == dest
        assert dest.read_bytes() == mp3_bytes
        assert result.size_bytes == len(mp3_bytes)
        assert result.url == CDN_URL_NEW
        assert dl._last_hash == HASH_NEW

    def test_basket_url_includes_trackslevels(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            _mock_response(200, content=b"mp3"),
        ]
        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        dl.download_track(target_pos=3, dest=tmp_path / "t.mp3", poll_interval=0.0)

        # Find the basket.php call (call #2 — the second session.get).
        basket_call = session.get.call_args_list[1]
        url = basket_call.args[0] if basket_call.args else basket_call.kwargs.get("url", "")
        assert "basket.php" in url
        # pos 3 → id 4 at level 100 → segment "100.4" inside the
        # trackslevels= query value (which contains other segments too).
        assert "trackslevels=" in url
        assert "100.4" in url
        assert "prodid=21279320" in url

    def test_fetch_uses_referer_header(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            _mock_response(200, content=b"mp3"),
        ]
        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        dl.download_track(target_pos=3, dest=tmp_path / "t.mp3", poll_interval=0.0)

        # The MP3 fetch is the last call; CDN's c*.recis.io requires
        # Referer set to the karaoke-version.com domain.
        fetch_call = session.get.call_args_list[3]
        headers = fetch_call.kwargs.get("headers", {})
        assert "recis.io" in (fetch_call.args[0] or fetch_call.kwargs.get("url", ""))
        assert headers.get("Referer", "").startswith("https://www.karaoke-version.com")


# ----------------------------------------------------------------------
# Error paths
# ----------------------------------------------------------------------


class TestDirectDownloaderErrors:
    def test_basket_500_raises_basket_update_error(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),  # snapshot
            _mock_response(500, "Internal Server Error: bad trackslevels"),
        ]
        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        with pytest.raises(BasketUpdateError) as exc:
            dl.download_track(
                target_pos=3, dest=tmp_path / "t.mp3", poll_interval=0.0
            )
        # Error must include diagnostic info per plan's hardening table.
        assert "500" in str(exc.value)
        assert "trackslevels" in str(exc.value).lower()

    def test_basket_non_200_raises(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(403, "Forbidden"),
        ]
        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        with pytest.raises(BasketUpdateError):
            dl.download_track(
                target_pos=3, dest=tmp_path / "t.mp3", poll_interval=0.0
            )

    def test_polling_never_sees_new_hash_raises_timeout(self, tmp_path):
        session = MagicMock()
        # Snapshot, basket, then one poll that returns the SAME hash.
        # max_wait=0 forces the deadline check to trip after exactly one
        # poll iteration — deterministic and fast.
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),  # snapshot
            _mock_response(200, "ok"),                                # basket
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),  # poll
        ]

        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        with pytest.raises(MixGenTimeout) as exc:
            dl.download_track(
                target_pos=3,
                dest=tmp_path / "t.mp3",
                max_wait=0.0,
                poll_interval=0.0,
            )
        assert "did not return" in str(exc.value) or "timeout" in str(exc.value).lower()

    def test_polling_no_url_in_response_raises_timeout(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),  # snapshot
            _mock_response(200, "ok"),                                # basket
            _mock_response(200, "<html>no mp3 url here</html>"),     # poll
        ]
        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        with pytest.raises(MixGenTimeout):
            dl.download_track(
                target_pos=3,
                dest=tmp_path / "t.mp3",
                max_wait=0.0,
                poll_interval=0.0,
            )

    def test_fetch_network_error_raises_mp3_fetch_error(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            ConnectionError("connection reset"),
        ]
        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        with pytest.raises(MP3FetchError) as exc:
            dl.download_track(
                target_pos=3, dest=tmp_path / "t.mp3", poll_interval=0.0
            )
        assert "connection" in str(exc.value).lower()

    def test_fetch_returns_5xx_raises_mp3_fetch_error(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            _mock_response(503, "Service Unavailable"),
        ]
        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        with pytest.raises(MP3FetchError):
            dl.download_track(
                target_pos=3, dest=tmp_path / "t.mp3", poll_interval=0.0
            )


class TestStateAcrossCalls:
    def test_second_track_uses_first_tracks_hash_as_baseline(self, tmp_path):
        session = MagicMock()
        # Call sequence for two tracks back-to-back:
        # init: snapshot → HASH_OLD
        # track 1: basket, poll(=NEW), fetch
        # track 2: basket, poll(=NEWER), fetch
        HASH_NEWER = "ccc89abcdef01234"
        CDN_URL_NEWER = (
            f"https://c1.recis.io/sl/k/{HASH_NEWER}/Bryan_Adams_18_til_I_Die.mp3"
        )
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),    # snapshot
            _mock_response(200, "ok"),                                  # basket #1
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),    # poll #1
            _mock_response(200, content=b"mp3-1"),                     # fetch #1
            _mock_response(200, "ok"),                                  # basket #2
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),    # poll #2 (stale)
            _mock_response(200, _begin_download_html(CDN_URL_NEWER)),  # poll #2 (fresh)
            _mock_response(200, content=b"mp3-2"),                     # fetch #2
        ]

        dl = DirectDownloader(session, TEMPLATE_PARAMS, SONG_URL)
        dl.download_track(target_pos=3, dest=tmp_path / "t1.mp3", poll_interval=0.0)
        dl.download_track(target_pos=4, dest=tmp_path / "t2.mp3", poll_interval=0.0)

        assert (tmp_path / "t1.mp3").read_bytes() == b"mp3-1"
        assert (tmp_path / "t2.mp3").read_bytes() == b"mp3-2"
        assert dl._last_hash == HASH_NEWER
