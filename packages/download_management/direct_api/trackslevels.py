"""trackslevels query-param builder for basket.php.

The trackslevels string encodes which tracks are soloed (and at what
volume) when the karaoke-version server renders a custom mix.

Format (verified empirically 2026-05-09 against bryan-adams/18-til-i-die
AND led-zeppelin/good-times-bad-times):

    "1,<level>.<id>,<level>.<id>,...,<level>.<id>,0"

  - Comma-separated segments
  - Leading bare "1" and trailing bare "0" are flag slots; touching them
    returns HTTP 500
  - Middle segments are "<level>.<id>" with level ∈ 0..100 and
    id = mixer.tracks[K].src_id + 1 (where src_id comes from the K-th
    track's source URL, e.g. ".../2.mp3" → src_id=2)

Position-to-track mapping (verified empirically against both songs):

    trackslevels position N solos mixer.tracks[N-1]

The captured trackslevels template from the page is INCOMPLETE — it
omits the slot for the LAST DOM track. So we build trackslevels from
scratch using `mixer.tracks` (the page's own canonical track list,
read via JS) instead of the captured template.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


class InvalidTemplateError(ValueError):
    """mixer_tracks list is empty/malformed, or a captured template
    cannot be parsed."""


class InvalidPositionError(ValueError):
    """The target index is out of range."""


@dataclass
class MixerTrack:
    """One entry from the page's window.mixer.tracks array."""
    index: int        # DOM data-index (== position in mixer.tracks)
    src_id: int       # extracted from mixer.tracks[K].url like ".../2.mp3"
    is_click: bool    # mixer.tracks[K].isClick
    description: str  # human-readable track caption (HTML stripped)


# (pos, track_id_or_None, level_str). id is None for bare-numeric edges;
# in that case level_str holds the raw numeric value.
Segment = Tuple[int, Optional[str], str]


def parse_segments(template: str) -> List[Segment]:
    """Decompose a trackslevels string into structured segments.

    Useful for inspecting a captured template (the static page-source
    setLevels value) for debugging or test fixtures. Not used by the
    runtime build path — that builds from mixer.tracks instead.
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


# Empirically (both probed songs), the leading flag is always "1" and
# the trailing flag is "0". Override only if a future probe finds otherwise.
LEADING_FLAG = "1"
TRAILING_FLAG = "0"


def build_trackslevels(
    mixer_tracks: List[MixerTrack],
    target_index: int,
    level: int = 100,
    leading_flag: str = LEADING_FLAG,
    trailing_flag: str = TRAILING_FLAG,
) -> str:
    """Build a trackslevels value that solos `mixer_tracks[target_index]`
    at `level`, with every other track at level=0.

    Args:
        mixer_tracks: window.mixer.tracks in DOM order, captured by
            session_capture
        target_index: DOM data-index of the track to solo
        level: volume 0..100 for the target slot
        leading_flag: bare slot at position 0 (default "1")
        trailing_flag: bare slot at the last position (default "0")

    Returns:
        e.g. "1,0.2,100.3,0.4,0.5,0" for a 4-track song soloing index 1

    Raises:
        InvalidTemplateError: mixer_tracks is empty
        InvalidPositionError: target_index out of range
    """
    if not mixer_tracks:
        raise InvalidTemplateError("mixer_tracks is empty")
    if target_index < 0 or target_index >= len(mixer_tracks):
        raise InvalidPositionError(
            f"target_index {target_index} out of range "
            f"[0, {len(mixer_tracks) - 1}]"
        )

    parts = [leading_flag]
    for i, track in enumerate(mixer_tracks):
        track_id = track.src_id + 1
        slot_level = level if i == target_index else 0
        parts.append(f"{slot_level}.{track_id}")
    parts.append(trailing_flag)
    return ",".join(parts)
