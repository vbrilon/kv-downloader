"""trackslevels query-param builder for basket.php.

The trackslevels string encodes which tracks are soloed (and at what
volume) when the karaoke-version server renders a custom mix.

Format (verified against bryan-adams/18-til-i-die, 2026-05-08):

    "1,0.2,0.3,100.4,...,0.13,0"

  - Comma-separated segments, one per slot.
  - Bare-numeric edge slots (positions 0 and N-1) encode site-level flags
    (e.g. precount). Changing them returns HTTP 500 — preserve verbatim.
  - Middle segments are "<level>.<id>". `level` = 0..100, `id` = the
    server-side track id (NOT the position).

To solo position N: set position N to "<level>.<id>", every other middle
segment to "0.<id>", leave edges alone.
"""

from typing import List, Optional, Tuple


class InvalidTemplateError(ValueError):
    """The trackslevels template is malformed."""


class InvalidPositionError(ValueError):
    """The target position is out of range or refers to a bare-numeric
    edge slot (which is a flag, not a soloable track)."""


# (pos, track_id_or_None, level_str)  — id is None for bare-numeric edges,
# in which case level_str holds the raw numeric value.
Segment = Tuple[int, Optional[str], str]


def parse_segments(template: str) -> List[Segment]:
    """Decompose a trackslevels template into structured segments.

    Returns a list of (position, id_or_None, level_str). Bare-numeric edge
    slots have id=None and level_str=the raw numeric value.
    """
    if not template or not template.strip():
        raise InvalidTemplateError("template is empty")

    out: List[Segment] = []
    for i, seg in enumerate(template.split(",")):
        if "." in seg:
            parts = seg.split(".")
            if len(parts) != 2:
                raise InvalidTemplateError(
                    f"segment {i} has {len(parts) - 1} dots, expected 1: {seg!r}"
                )
            level, sid = parts
            out.append((i, sid, level))
        else:
            out.append((i, None, seg))
    return out


def build_trackslevels(
    template: str,
    target_pos: int,
    level: int = 100,
) -> str:
    """Build a trackslevels string that solos `target_pos` at `level`.

    Every other id-bearing segment is set to "0.<id>". Bare-numeric edge
    slots are preserved verbatim (changing them returns HTTP 500).

    Raises:
        InvalidTemplateError: template is empty or malformed
        InvalidPositionError: target_pos is out of range or points at a
            bare-numeric edge slot
    """
    segments = parse_segments(template)

    if target_pos < 0 or target_pos >= len(segments):
        raise InvalidPositionError(
            f"target_pos {target_pos} out of range [0, {len(segments) - 1}]"
        )

    target_seg = segments[target_pos]
    if target_seg[1] is None:
        raise InvalidPositionError(
            f"target_pos {target_pos} is a bare-numeric edge slot "
            f"(value {target_seg[2]!r}); cannot solo a flag slot"
        )

    out_segments: List[str] = []
    for i, (_pos, sid, raw_level) in enumerate(segments):
        if sid is None:
            out_segments.append(raw_level)
        elif i == target_pos:
            out_segments.append(f"{level}.{sid}")
        else:
            out_segments.append(f"0.{sid}")
    return ",".join(out_segments)
