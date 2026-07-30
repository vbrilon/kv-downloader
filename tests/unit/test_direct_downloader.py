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
captured from the inline mixer init script, `mixer_tracks` read from
window.mixer.tracks, and a `requests.Session` carrying the authenticated
cookies. Every call thereafter is just-HTTP — no Selenium.
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
from packages.download_management.direct_api.trackslevels import MixerTrack


# Real basket-template params captured 2026-05-08 from
# bryan-adams/18-til-i-die. trackslevels here is the static-script
# value; the runtime path no longer uses it for soloing — it builds
# trackslevels from MIXER_TRACKS instead.
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

# mixer.tracks for bryan-adams/18-til-i-die (13 tracks: Click + 12 real).
# mixer.tracks[K].src_id = K+1, so trackslevels id at position K+1 is
# src_id+1 = K+2.
MIXER_TRACKS = [
    MixerTrack(index=0,  src_id=1,  is_click=True,  description="Intro count Click"),
    MixerTrack(index=1,  src_id=2,  is_click=False, description="Drum Kit"),
    MixerTrack(index=2,  src_id=3,  is_click=False, description="Bass"),
    MixerTrack(index=3,  src_id=4,  is_click=False, description="Electric Guitar (left)"),
    MixerTrack(index=4,  src_id=5,  is_click=False, description="Electric Guitar (right)"),
    MixerTrack(index=5,  src_id=6,  is_click=False, description="Electric Guitar (crunch 1)"),
    MixerTrack(index=6,  src_id=7,  is_click=False, description="Electric Guitar (crunch 2)"),
    MixerTrack(index=7,  src_id=8,  is_click=False, description="Electric Guitar (clean)"),
    MixerTrack(index=8,  src_id=9,  is_click=False, description="Distorted Electric Guitar"),
    MixerTrack(index=9,  src_id=10, is_click=False, description="Lead Electric Guitar (left)"),
    MixerTrack(index=10, src_id=11, is_click=False, description="Lead Electric Guitar"),
    MixerTrack(index=11, src_id=12, is_click=False, description="Backing Vocals"),
    MixerTrack(index=12, src_id=13, is_click=False, description="Lead Vocal"),
]
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
    r.iter_content = lambda chunk_size: iter([content])
    r.__enter__ = lambda self: self
    r.__exit__ = lambda self, *a: None
    return r


def _begin_download_html(cdn_url):
    return f'<div class="modal__content"><a href="{cdn_url}">DL</a></div>'


def _make_dl(session):
    return DirectDownloader(session, TEMPLATE_PARAMS, MIXER_TRACKS, SONG_URL)


class TestDirectDownloaderHappyPath:
    def test_download_track_full_flow(self, tmp_path):
        session = MagicMock()
        # The downloader will:
        #   1. snapshot initial hash via begin_download (HASH_OLD)
        #   2. call basket.php → 200
        #   3. poll begin_download until hash flips (HASH_NEW)
        #   4. fetch the MP3 bytes
        mp3_bytes = b"\xff\xfb\x90\x00fake-mp3-data" * 100
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            _mock_response(200, content=mp3_bytes),
        ]

        dl = _make_dl(session)
        dest = tmp_path / "track.mp3"
        # target_index=3 → DOM data-index 3 → mixer.tracks[3] (src_id=4) →
        # trackslevels position 4 with id=5 at level=100
        result = dl.download_track(target_index=3, dest=dest, poll_interval=0.0)

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
        dl = _make_dl(session)
        dl.download_track(target_index=3, dest=tmp_path / "t.mp3", poll_interval=0.0)

        basket_call = session.get.call_args_list[1]
        url = basket_call.args[0] if basket_call.args else basket_call.kwargs.get("url", "")
        assert "basket.php" in url
        assert "trackslevels=" in url
        # target_index=3 → mixer.tracks[3].src_id=4 → trackslevels id=5
        # at position 4, level=100. Segment "100.5" appears in the
        # trackslevels query value.
        assert "100.5" in url
        assert "prodid=21279320" in url

    def test_fetch_uses_referer_header(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            _mock_response(200, content=b"mp3"),
        ]
        dl = _make_dl(session)
        dl.download_track(target_index=3, dest=tmp_path / "t.mp3", poll_interval=0.0)

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
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(500, "Internal Server Error: bad trackslevels"),
        ]
        dl = _make_dl(session)
        with pytest.raises(BasketUpdateError) as exc:
            dl.download_track(
                target_index=3, dest=tmp_path / "t.mp3", poll_interval=0.0
            )
        assert "500" in str(exc.value)
        assert "trackslevels" in str(exc.value).lower()

    def test_basket_non_200_raises(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(403, "Forbidden"),
        ]
        dl = _make_dl(session)
        with pytest.raises(BasketUpdateError):
            dl.download_track(
                target_index=3, dest=tmp_path / "t.mp3", poll_interval=0.0
            )

    def test_polling_never_sees_new_hash_raises_timeout(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
        ]
        dl = _make_dl(session)
        with pytest.raises(MixGenTimeout) as exc:
            dl.download_track(
                target_index=3,
                dest=tmp_path / "t.mp3",
                max_wait=0.0,
                poll_interval=0.0,
            )
        assert "did not return" in str(exc.value) or "timeout" in str(exc.value).lower()

    def test_polling_no_url_in_response_raises_timeout(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, "<html>no mp3 url here</html>"),
        ]
        dl = _make_dl(session)
        with pytest.raises(MixGenTimeout):
            dl.download_track(
                target_index=3,
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
            ConnectionError("connection reset"),
            ConnectionError("connection reset"),
        ]
        dl = _make_dl(session)
        with pytest.raises(MP3FetchError) as exc:
            dl.download_track(
                target_index=3,
                dest=tmp_path / "t.mp3",
                poll_interval=0.0,
                fetch_retry_backoff=0.0,
            )
        msg = str(exc.value).lower()
        assert "connection reset" in msg
        assert "3 attempts" in msg

    def test_fetch_returns_5xx_raises_mp3_fetch_error(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            _mock_response(503, "Service Unavailable"),
            _mock_response(503, "Service Unavailable"),
            _mock_response(503, "Service Unavailable"),
        ]
        dl = _make_dl(session)
        with pytest.raises(MP3FetchError):
            dl.download_track(
                target_index=3, dest=tmp_path / "t.mp3", poll_interval=0.0
            )


class TestRetryBehavior:
    """Phase 4 hardening: transient failures should be retried before
    giving up on a track."""

    def test_mp3_fetch_retries_on_network_error(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            ConnectionError("transient 1"),
            ConnectionError("transient 2"),
            _mock_response(200, content=b"mp3-success"),
        ]
        dl = _make_dl(session)
        result = dl.download_track(
            target_index=3,
            dest=tmp_path / "t.mp3",
            poll_interval=0.0,
            fetch_retry_backoff=0.0,
        )
        assert result.size_bytes == len(b"mp3-success")
        assert (tmp_path / "t.mp3").read_bytes() == b"mp3-success"

    def test_mp3_fetch_gives_up_after_max_retries(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            ConnectionError("attempt 1"),
            ConnectionError("attempt 2"),
            ConnectionError("attempt 3"),
        ]
        dl = _make_dl(session)
        with pytest.raises(MP3FetchError):
            dl.download_track(
                target_index=3,
                dest=tmp_path / "t.mp3",
                poll_interval=0.0,
                fetch_retry_backoff=0.0,
            )

    def test_mp3_fetch_5xx_retries_then_succeeds(self, tmp_path):
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(CDN_URL_OLD)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(CDN_URL_NEW)),
            _mock_response(503, "Service Unavailable"),
            _mock_response(200, content=b"mp3-ok"),
        ]
        dl = _make_dl(session)
        result = dl.download_track(
            target_index=3,
            dest=tmp_path / "t.mp3",
            poll_interval=0.0,
            fetch_retry_backoff=0.0,
        )
        assert (tmp_path / "t.mp3").read_bytes() == b"mp3-ok"


class TestStateAcrossCalls:
    def test_second_track_uses_first_tracks_hash_as_baseline(self, tmp_path):
        session = MagicMock()
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

        dl = _make_dl(session)
        dl.download_track(target_index=3, dest=tmp_path / "t1.mp3", poll_interval=0.0)
        dl.download_track(target_index=4, dest=tmp_path / "t2.mp3", poll_interval=0.0)

        assert (tmp_path / "t1.mp3").read_bytes() == b"mp3-1"
        assert (tmp_path / "t2.mp3").read_bytes() == b"mp3-2"
        assert dl._last_hash == HASH_NEWER


# ----------------------------------------------------------------------
# Track-identity verification (2026-07-30)
#
# The server names the rendered MP3 after the track it soloed, e.g.
# Toto_Hold_the_Line(Lead_Electric_Guitar_Custom_Backing_Track).mp3.
# Accepting a render on "hash changed" alone let a fresh render of the
# WRONG track be saved under the requested track's name (see
# docs/plans/2026-07-30-verify-track-identity.md).
# ----------------------------------------------------------------------


from packages.download_management.direct_api.direct_downloader import (  # noqa: E402
    TrackMismatchError,
    extract_track_label,
    normalize_label,
    identify_track,
)

SONG = "Bryan_Adams_18_til_I_Die"


def _cdn(hash_, label=None, song=SONG):
    """Build a CDN URL, optionally carrying a server track label."""
    name = f"{song}({label}_Custom_Backing_Track).mp3" if label else f"{song}.mp3"
    return f"https://c1.recis.io/sl/k/{hash_}/{name}"


class TestExtractTrackLabel:
    def test_simple_name(self):
        url = _cdn("aaa1", "Lead_Electric_Guitar")
        assert extract_track_label(url) == "Lead Electric Guitar"

    def test_nested_parens_in_track_name(self):
        url = _cdn("aaa1", "Rhythm_Electric_Guitar_(muted_left)")
        assert extract_track_label(url) == "Rhythm Electric Guitar (muted left)"

    def test_parenthesised_song_title_does_not_poison_capture(self):
        # A leftmost-'(' regex captures "Radio_Edit)(Bass" here.
        url = _cdn("aaa1", "Bass", song="Ricky_Livin_la_Vida_Loca_(Radio_Edit)")
        assert extract_track_label(url) == "Bass"

    def test_percent_encoded_filename(self):
        url = ("https://c1.recis.io/sl/k/aaa1/"
               "Toto%28Lead_Electric_Guitar_Custom_Backing_Track%29.mp3")
        assert extract_track_label(url) == "Lead Electric Guitar"

    def test_url_without_label_returns_none(self):
        assert extract_track_label(CDN_URL_OLD) is None

    def test_malformed_returns_none(self):
        assert extract_track_label("https://c1.recis.io/sl/k/aaa1/x.mp3") is None
        assert extract_track_label("") is None
        assert extract_track_label(None) is None


class TestNormalizeLabel:
    def test_punctuation_and_case_are_irrelevant(self):
        assert normalize_label("Rhythm Electric Guitar (muted left)") == \
               normalize_label("rhythm_electric_guitar_(MUTED_LEFT)")

    def test_accents_fold_to_ascii(self):
        assert normalize_label("Ukulélé") == normalize_label("Ukulele")


class TestIdentifyTrack:
    def test_server_click_label_resolves_to_intro_count_click(self):
        # Postmortem records the server saying "Click" while the DOM
        # description is "Intro count Click".
        assert identify_track("Click", MIXER_TRACKS) == 0

    def test_exact_match_wins_over_longer_containing_name(self):
        # "Lead Electric Guitar" must NOT resolve to index 9,
        # "Lead Electric Guitar (left)".
        assert identify_track("Lead Electric Guitar", MIXER_TRACKS) == 10

    def test_longer_name_resolves_to_itself(self):
        assert identify_track("Lead Electric Guitar (left)", MIXER_TRACKS) == 9

    def test_ambiguous_label_returns_none(self):
        assert identify_track("Electric Guitar", MIXER_TRACKS) is None

    def test_unknown_label_returns_none(self):
        assert identify_track("Kazoo", MIXER_TRACKS) is None

    def test_duplicate_descriptions_return_none(self):
        dupes = [
            MixerTrack(index=0, src_id=1, is_click=False, description="Guitar"),
            MixerTrack(index=1, src_id=2, is_click=False, description="Guitar"),
        ]
        assert identify_track("Guitar", dupes) is None


class TestTrackIdentityVerification:
    def test_fresh_render_of_wrong_track_is_rejected(self, tmp_path):
        """THE REGRESSION. Server returns a fresh hash whose label names a
        different track — previously accepted and saved under the wrong
        name."""
        wrong = _cdn(HASH_NEW, "Drum_Kit")
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(_cdn(HASH_OLD, "Bass"))),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(wrong)),
            _mock_response(200, "ok"),          # re-issued basket.php
            _mock_response(200, _begin_download_html(wrong)),
        ]
        dl = _make_dl(session)
        dest = tmp_path / "lead.mp3"

        with pytest.raises(TrackMismatchError) as exc:
            dl.download_track(target_index=10, dest=dest,
                              max_wait=0.0, poll_interval=0.0)

        assert "Drum Kit" in str(exc.value)
        assert not dest.exists(), "wrong-track audio must never reach disk"

    def test_stale_hash_with_matching_label_is_not_accepted(self, tmp_path):
        """Freshness gate must survive: a matching label on a STALE render
        (e.g. a resumed re-run) must not short-circuit the hash check."""
        stale = _cdn(HASH_OLD, "Lead_Electric_Guitar")
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(stale)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(stale)),
        ]
        dl = _make_dl(session)
        dest = tmp_path / "t.mp3"

        with pytest.raises(MixGenTimeout):
            dl.download_track(target_index=10, dest=dest,
                              max_wait=0.0, poll_interval=0.0)
        assert not dest.exists()

    def test_stall_raises_mixgen_timeout_not_mismatch(self, tmp_path):
        """A server that never renders anything fresh is a stall, not a
        wrong-track render — the two must stay distinguishable."""
        stale = _cdn(HASH_OLD, "Drum_Kit")
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(stale)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(stale)),
        ]
        dl = _make_dl(session)

        with pytest.raises(MixGenTimeout):
            dl.download_track(target_index=10, dest=tmp_path / "t.mp3",
                              max_wait=0.0, poll_interval=0.0)

    def test_correct_label_is_accepted(self, tmp_path):
        session = MagicMock()
        good = _cdn(HASH_NEW, "Lead_Electric_Guitar")
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(_cdn(HASH_OLD, "Bass"))),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(good)),
            _mock_response(200, content=b"mp3-bytes"),
        ]
        dl = _make_dl(session)
        dest = tmp_path / "lead.mp3"
        result = dl.download_track(target_index=10, dest=dest, poll_interval=0.0)

        assert result.url == good
        assert dest.read_bytes() == b"mp3-bytes"

    def test_mismatch_reissues_basket_once_then_self_heals(self, tmp_path):
        """On the first fresh mismatch the cart update is re-sent — if it was
        lost, that is the actual repair."""
        wrong = _cdn("ccc111", "Drum_Kit")
        good = _cdn("ddd222", "Lead_Electric_Guitar")
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(_cdn(HASH_OLD, "Bass"))),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(wrong)),
            _mock_response(200, "ok"),          # re-issued basket.php
            _mock_response(200, _begin_download_html(good)),
            _mock_response(200, content=b"mp3"),
        ]
        dl = _make_dl(session)
        dest = tmp_path / "lead.mp3"
        result = dl.download_track(target_index=10, dest=dest,
                                   max_wait=30.0, poll_interval=0.0)

        assert result.url == good
        basket_calls = [
            c for c in session.get.call_args_list
            if "basket.php" in str(c.args[0] if c.args else "")
        ]
        assert len(basket_calls) == 2, "basket.php should be re-issued exactly once"

    def test_last_hash_recorded_after_mismatch_failure(self, tmp_path):
        wrong = _cdn(HASH_NEW, "Drum_Kit")
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(_cdn(HASH_OLD, "Bass"))),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(wrong)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(wrong)),
        ]
        dl = _make_dl(session)
        with pytest.raises(TrackMismatchError):
            dl.download_track(target_index=10, dest=tmp_path / "t.mp3",
                              max_wait=0.0, poll_interval=0.0)
        assert dl._last_hash == HASH_NEW, (
            "the wrong render's hash must be recorded, or the next track "
            "will treat it as fresh under the fallback path"
        )

    def test_unrecognised_label_repeating_filename_is_rejected(self, tmp_path):
        """Label parses but names no known track (format drift): an
        identical filename means identical cart content, so keep waiting."""
        first = _cdn(HASH_OLD, "Zither")
        session = MagicMock()
        session.get.side_effect = [
            _mock_response(200, _begin_download_html(first)),
            _mock_response(200, "ok"),
            _mock_response(200, _begin_download_html(first)),
            _mock_response(200, content=b"mp3"),
        ]
        dl = _make_dl(session)
        dl._last_filename = f"{SONG}(Zither_Custom_Backing_Track).mp3"
        dl._last_hash = "someotherhash"

        with pytest.raises(MixGenTimeout):
            dl.download_track(target_index=10, dest=tmp_path / "t.mp3",
                              max_wait=0.0, poll_interval=0.0)
