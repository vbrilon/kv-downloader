"""Unit tests for direct_api.trackslevels.

The trackslevels string is the basket.php query param that tells the
karaoke-version server which track to render at which volume. Verified
format from probe_direct_api.py and probe_script_source.py:

  Real template (13-track song, captured 2026-05-08):
    "1,0.2,0.3,100.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,0.12,0.13,0"

  Segments:
    pos 0:  "1"      <- bare-numeric edge (precount/flag)
    pos 1:  "0.2"    <- level=0,    id=2
    pos 2:  "0.3"    <- level=0,    id=3
    pos 3:  "100.4"  <- level=100,  id=4   (the seeded track)
    ...
    pos 13: "0"      <- bare-numeric edge

To solo track at position N we set pos N to "100.<id>" and every other
.id segment to "0.<id>", leaving bare-numeric edges untouched (changing
them returns HTTP 500 from basket.php — verified via probe).
"""

import pytest

# This import will fail at first — that's the RED.
from packages.download_management.direct_api.trackslevels import (
    build_trackslevels,
    parse_segments,
    InvalidTemplateError,
    InvalidPositionError,
)


# Real template captured from bryan-adams/18-til-i-die.
REAL_TEMPLATE = "1,0.2,0.3,100.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,0.12,0.13,0"


class TestParseSegments:
    def test_parses_real_template(self):
        segs = parse_segments(REAL_TEMPLATE)
        # 14 segments = 1 leading edge + 12 .id middle segments + 1
        # trailing edge. The 12 middle segments map to data-indices 1..12
        # (data-index 0 is the click/precount, controlled separately).
        assert len(segs) == 14

        # Edges are bare-numeric.
        assert segs[0] == (0, None, "1")
        assert segs[13] == (13, None, "0")

        # Middle entries have id and level. Captured 2026-05-08 with
        # data-index 1 (Drum Kit) seeded → "100.4" at pos 3.
        assert segs[1] == (1, "2", "0")
        assert segs[3] == (3, "4", "100")
        assert segs[12] == (12, "13", "0")

    def test_empty_template_raises(self):
        with pytest.raises(InvalidTemplateError):
            parse_segments("")

    def test_whitespace_only_raises(self):
        with pytest.raises(InvalidTemplateError):
            parse_segments("   ")

    def test_segment_with_multiple_dots_raises(self):
        # "0.0.5" is malformed — could indicate a parse bug we want to
        # surface, not silently accept.
        with pytest.raises(InvalidTemplateError):
            parse_segments("1,0.2,0.0.5,0.4,0")


class TestBuildTrackslevels:
    def test_preserves_bare_numeric_edges(self):
        # No matter which position we solo, the bare edges (pos 0 and pos
        # N-1) must be byte-identical to the template.
        out = build_trackslevels(REAL_TEMPLATE, target_pos=3, level=100)
        segments = out.split(",")
        assert segments[0] == "1"
        assert segments[13] == "0"

    def test_sets_target_to_requested_level(self):
        out = build_trackslevels(REAL_TEMPLATE, target_pos=5, level=100)
        segments = out.split(",")
        assert segments[5] == "100.6"  # id at pos 5 is "6"

    def test_zeros_other_id_segments(self):
        out = build_trackslevels(REAL_TEMPLATE, target_pos=3, level=100)
        segments = out.split(",")
        # Every .id segment except the target is "0.<id>".
        for i, seg in enumerate(segments):
            if i in (0, 13):  # bare edges
                continue
            if i == 3:
                assert seg == "100.4"
            else:
                assert seg.startswith("0."), (
                    f"segment {i} should be 0.<id>, got {seg!r}"
                )

    def test_default_level_is_100(self):
        out_default = build_trackslevels(REAL_TEMPLATE, target_pos=2)
        out_explicit = build_trackslevels(REAL_TEMPLATE, target_pos=2, level=100)
        assert out_default == out_explicit

    def test_custom_level(self):
        out = build_trackslevels(REAL_TEMPLATE, target_pos=2, level=42)
        segments = out.split(",")
        assert segments[2] == "42.3"  # id at pos 2 is "3"

    def test_zero_level(self):
        out = build_trackslevels(REAL_TEMPLATE, target_pos=2, level=0)
        segments = out.split(",")
        # All .id segments are "0.<id>" — equivalent to "no track soloed"
        assert segments[2] == "0.3"

    def test_target_pos_zero_raises(self):
        # pos 0 is a bare-numeric edge, NOT a soloable track. Touching it
        # returns HTTP 500 from basket.php. Refuse the request explicitly.
        with pytest.raises(InvalidPositionError):
            build_trackslevels(REAL_TEMPLATE, target_pos=0)

    def test_target_pos_last_edge_raises(self):
        with pytest.raises(InvalidPositionError):
            build_trackslevels(REAL_TEMPLATE, target_pos=13)

    def test_target_pos_out_of_range_raises(self):
        with pytest.raises(InvalidPositionError):
            build_trackslevels(REAL_TEMPLATE, target_pos=99)

    def test_negative_target_pos_raises(self):
        with pytest.raises(InvalidPositionError):
            build_trackslevels(REAL_TEMPLATE, target_pos=-1)

    def test_round_trip(self):
        # parse(build(template, k)) shows exactly one segment with level=k,
        # at position k.
        out = build_trackslevels(REAL_TEMPLATE, target_pos=7, level=50)
        segs = parse_segments(out)
        non_zero = [s for s in segs if s[1] is not None and s[2] != "0"]
        assert len(non_zero) == 1
        assert non_zero[0] == (7, "8", "50")  # pos 7 has id "8"


class TestRealisticUsage:
    """Spot-check a realistic flow: build trackslevels for every soloable
    track in the real template and confirm each one looks right."""

    def test_every_position_solo_works(self):
        # Skip edges 0 and 13; soloable middle positions are 1..12.
        for pos in range(1, 13):
            out = build_trackslevels(REAL_TEMPLATE, target_pos=pos)
            segs = parse_segments(out)
            soloed = [(p, sid, lvl) for p, sid, lvl in segs if lvl == "100"]
            assert len(soloed) == 1, f"pos {pos} produced {soloed}"
            assert soloed[0][0] == pos
