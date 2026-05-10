"""Unit tests for direct_api.trackslevels.

The trackslevels string is the basket.php query param that tells the
karaoke-version server which track to render at which volume.

Format (verified empirically 2026-05-09 against bryan-adams/18-til-i-die
AND led-zeppelin/good-times-bad-times):

  "1,<level>.<id>,<level>.<id>,...,<level>.<id>,0"

  - Leading bare "1" and trailing bare "0" are flag slots; touching them
    returns HTTP 500.
  - Middle "<level>.<id>" segments encode each track. id = src_id+1
    where src_id comes from mixer.tracks[K].url like ".../2.mp3" → 2.
  - Position N solos mixer.tracks[N-1] (off-by-one between DOM index
    and trackslevels position).
"""

import pytest

from packages.download_management.direct_api.trackslevels import (
    MixerTrack,
    build_trackslevels,
    parse_segments,
    InvalidTemplateError,
    InvalidPositionError,
)


# Real captured trackslevels from led-zeppelin/good-times-bad-times.
# Used here to test parse_segments against a real-world string.
GTBT_TEMPLATE = "1,0.2,0.3,0.4,0.5,0.6,0.7,100.8,0"


# Real mixer.tracks for led-zeppelin/good-times-bad-times (8 tracks).
# Captured via probe_mixer_internals.py 2026-05-09.
GTBT_TRACKS = [
    MixerTrack(index=0, src_id=1, is_click=True,  description="Intro count Click"),
    MixerTrack(index=1, src_id=2, is_click=False, description="Drum Kit"),
    MixerTrack(index=2, src_id=3, is_click=False, description="Bass"),
    MixerTrack(index=3, src_id=4, is_click=False, description="Rhythm Electric Guitar (left)"),
    MixerTrack(index=4, src_id=5, is_click=False, description="Rhythm Electric Guitar (right)"),
    MixerTrack(index=5, src_id=6, is_click=False, description="Lead Electric Guitar"),
    MixerTrack(index=6, src_id=7, is_click=False, description="Backing Vocals"),
    MixerTrack(index=7, src_id=8, is_click=False, description="Lead Vocal"),
]


class TestParseSegments:
    def test_parses_real_template(self):
        segs = parse_segments(GTBT_TEMPLATE)
        # 9 segments = 1 leading + 7 .id middle + 1 trailing.
        assert len(segs) == 9
        assert segs[0] == (0, None, "1")
        assert segs[8] == (8, None, "0")
        assert segs[1] == (1, "2", "0")
        assert segs[7] == (7, "8", "100")  # the seeded position

    def test_empty_template_raises(self):
        with pytest.raises(InvalidTemplateError):
            parse_segments("")

    def test_whitespace_only_raises(self):
        with pytest.raises(InvalidTemplateError):
            parse_segments("   ")

    def test_segment_with_multiple_dots_raises(self):
        with pytest.raises(InvalidTemplateError):
            parse_segments("1,0.2,0.0.5,0.4,0")


class TestBuildTrackslevels:
    def test_solo_first_track_click(self):
        # mixer.tracks[0] is the click track. Soloing it produces a
        # trackslevels with all slots at 0 except position 1 (= src_id+1 = 2)
        # at level=100.
        out = build_trackslevels(GTBT_TRACKS, target_index=0, level=100)
        assert out == "1,100.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0"

    def test_solo_real_track_drum_kit(self):
        # mixer.tracks[1] is Drum Kit (src_id=2). Soloing produces
        # position 2 (= src_id+1 = 3) at level=100.
        out = build_trackslevels(GTBT_TRACKS, target_index=1, level=100)
        assert out == "1,0.2,100.3,0.4,0.5,0.6,0.7,0.8,0.9,0"

    def test_solo_last_track_lead_vocal(self):
        # mixer.tracks[7] is Lead Vocal (src_id=8). The captured
        # trackslevels template OMITS this slot — but building from
        # mixer.tracks creates it at position 8 (= src_id+1 = 9). The
        # server accepts the extended trackslevels (verified 2026-05-09
        # via probe_extended_trackslevels.py).
        out = build_trackslevels(GTBT_TRACKS, target_index=7, level=100)
        assert out == "1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,100.9,0"

    def test_default_level_is_100(self):
        a = build_trackslevels(GTBT_TRACKS, target_index=2)
        b = build_trackslevels(GTBT_TRACKS, target_index=2, level=100)
        assert a == b

    def test_custom_level(self):
        out = build_trackslevels(GTBT_TRACKS, target_index=2, level=42)
        # mixer.tracks[2] is Bass with src_id=3 → trackslevels id=4 at pos 3.
        segs = parse_segments(out)
        soloed = [s for s in segs if s[1] is not None and s[2] != "0"]
        assert len(soloed) == 1
        assert soloed[0] == (3, "4", "42")

    def test_zero_level(self):
        # level=0 is equivalent to "no track soloed" — same as if every
        # slot were at 0. Useful for click-only renders.
        out = build_trackslevels(GTBT_TRACKS, target_index=2, level=0)
        segs = parse_segments(out)
        non_zero = [s for s in segs if s[1] is not None and s[2] != "0"]
        assert non_zero == []

    def test_target_index_negative_raises(self):
        with pytest.raises(InvalidPositionError):
            build_trackslevels(GTBT_TRACKS, target_index=-1)

    def test_target_index_out_of_range_raises(self):
        with pytest.raises(InvalidPositionError):
            build_trackslevels(GTBT_TRACKS, target_index=99)

    def test_target_index_one_past_last_raises(self):
        # 8 tracks → max valid index 7.
        with pytest.raises(InvalidPositionError):
            build_trackslevels(GTBT_TRACKS, target_index=8)

    def test_empty_mixer_tracks_raises(self):
        with pytest.raises(InvalidTemplateError):
            build_trackslevels([], target_index=0)

    def test_leading_and_trailing_flags_default(self):
        out = build_trackslevels(GTBT_TRACKS, target_index=1)
        segs = out.split(",")
        assert segs[0] == "1"
        assert segs[-1] == "0"

    def test_custom_leading_trailing_flags(self):
        out = build_trackslevels(
            GTBT_TRACKS, target_index=1,
            leading_flag="X", trailing_flag="Y",
        )
        segs = out.split(",")
        assert segs[0] == "X"
        assert segs[-1] == "Y"


class TestRealisticUsage:
    """Spot-check soloing every track produces exactly one non-zero slot
    at the expected position with the expected id."""

    def test_every_track_soloable(self):
        for i, track in enumerate(GTBT_TRACKS):
            out = build_trackslevels(GTBT_TRACKS, target_index=i)
            segs = parse_segments(out)
            soloed = [(p, sid, lvl) for p, sid, lvl in segs if lvl == "100"]
            assert len(soloed) == 1, f"index {i} produced {soloed}"
            # Position is index+1 (skipping the leading bare flag).
            # Id is src_id+1.
            assert soloed[0] == (i + 1, str(track.src_id + 1), "100")

    def test_total_segment_count_matches_track_count_plus_two(self):
        # N tracks → N+2 segments (1 leading flag + N audible + 1 trailing).
        out = build_trackslevels(GTBT_TRACKS, target_index=0)
        assert len(out.split(",")) == len(GTBT_TRACKS) + 2
