# Direct-API: Mapping, Precount, and Cascade Failures (2026-05-09)

Investigation + fix postmortem for three bugs found while downloading
`led-zeppelin/good-times-bad-times`. All three predate the report;
all three were silent because they didn't crash, they just produced
wrong output (or wrong wait time).

## What was wrong

| Bug | Symptom | Lived since |
|---|---|---|
| Off-by-one trackslevels mapping | Every direct-API track contained the audio of the *previous* track in DOM order. | direct-API cutover (~commit `c097712`, ~6 months) |
| Precount captured static, not live | Downloaded tracks lacked the intro count-in even when the user enabled the checkbox. | same |
| Cascading failures unbounded | After server stops producing fresh renders, 8-track download hung for 12+ minutes (direct-API timeouts + legacy auto-retry compounding). | same |

Fixes shipped in commits `841b38d` (mapping) and `4ab435b` (precount +
cascade). All three were latent in `main` from the cutover until
2026-05-09.

## Why they were silent

**Mapping bug**: Phase 3 of the direct-API rewrite plan validated
**file size match** vs legacy, not **content match**. For a fixed-
duration song with CBR encoding, every soloed track has the same
byte size regardless of which track is soloed (the per-song baseline
in `tests/fixtures/baseline_sha256.json` confirms this — 3 different
tracks of 18-til-i-die all at exactly 8,654,285 bytes). So a fully
mis-mapped download passed Phase 3 with 100% size-match.

**Precount bug**: nothing crashed. Tracks were fully downloadable, just
without the count-in. For songs whose static `mixer.setPrecount("...")`
was already `"1"` (e.g. `bryan-adams/18-til-i-die`), the bug was
*invisible* — the captured static value happened to match the desired
live value. For songs initialized with `"0"` (Good Times Bad Times),
the captured value was wrong but the user might not notice unless they
were specifically listening for the count-in.

**Cascade bug**: 8/8 success was the common case (server cooperated).
The hang only appeared when the server's session got into a bad state,
which doesn't happen on cold runs.

## Diagnostic methodology that worked

A few techniques here were non-obvious and worth preserving:

### 1. URL filename = server's authoritative track label

`begin_download.html` returns an `<a href="...mp3">` whose filename is
generated server-side from the soloed track's name, e.g.
`Led_Zeppelin_Good_Times_Bad_Times(Drum_Kit_Custom_Backing_Track).mp3`.
That filename tells you, definitively, which track the server
*thought* it was rendering. Compare it against the DOM-derived name we
saved the file under — any mismatch surfaces a mapping bug instantly.

This was the breakthrough. The probe in `tools/probe_track_mapping.py`
calls `basket.php` for each non-edge position in the captured template,
polls `begin_download.html`, and prints `pos N → server says X` rows.
For the bug, every row showed an off-by-one: pos 1 → "Click", pos 2 →
"Drum_Kit", … instead of pos 1 → "Drum_Kit", pos 2 → "Bass", …

### 2. PCM amplitude-envelope cosine similarity for fuzzy audio match

You CAN'T compare two MP3s for content equality via byte/SHA — encoder
nondeterminism produces different bitstreams for the same audio (see
`docs/site-flow/mp3-encoder-nondeterminism.md`). PCM hash is also
unreliable; the encoder's dithering noise produces different decoded
samples too.

Robust fuzzy match: decode both MP3s to mono lo-rate (4 kHz) PCM, slice
into 0.5s windows, take mean abs amplitude per window → vector of
~340 floats per track. Compare two vectors via cosine similarity.
**Same audio content → similarity 1.0000 (bit-perfect).** Different
content → some lower number, often 0.5–0.95 depending on how similar
the dynamics are.

This gave us a definitive content check: for each user-downloaded MP3,
we found the probe-rendered position whose envelope matched at exactly
1.0000. That nailed down the off-by-one without ambiguity.

```python
# Sketch of the comparison (full impl was in tools/compare_audio.py,
# now removed; reconstruct from this if needed):
def envelope(mp3_path, window_s=0.5, sr=4000):
    cmd = ["ffmpeg", "-v", "quiet", "-i", str(mp3_path),
           "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    samples = struct.unpack("...", subprocess.run(cmd, ...).stdout)
    return [mean_abs(samples[i:i+win_n]) for i in range(0, len, win_n)]

def cosine(a, b):
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    return sum(x*y for x,y in zip(a,b)) / (norm(a) * norm(b))
```

### 3. `window.mixer.tracks` is the canonical track manifest

We were building trackslevels from the captured `setLevels` template.
That template is incomplete (omits one slot — Lead Vocal in both probed
songs) and its `id` labels are offset from the source track ids by +1.
Using `window.mixer.tracks` as the source of truth solves both
problems:

```js
// What mixer.tracks gives you (verified against both songs):
mixer.tracks = [
  {index: 0, url: ".../1.mp3", isClick: true,  description: "...Click..."},
  {index: 1, url: ".../2.mp3", isClick: false, description: "Drum Kit"},
  {index: 2, url: ".../3.mp3", isClick: false, description: "Bass"},
  ...
];
```

- `index` = DOM `data-index` (== position in `mixer.tracks`)
- `url` ends in `<src_id>.mp3` — that's the per-track source MP3 id
- `isClick` flags the click/precount row
- `description` is the human caption (HTML; strip tags + collapse whitespace)

The trackslevels position-to-track mapping is **`pos K solos
mixer.tracks[K-1]`** universally. The trackslevels id label is
**`src_id + 1`**. Build trackslevels with one segment per
`mixer.tracks` entry and you get a complete, correct trackslevels for
any song.

### 4. Cross-song verification is non-negotiable

The mapping convention "data-index N → trackslevels position N" was
verified for `bryan-adams/18-til-i-die` and codified in
`docs/site-flow/trackslevels-format.md`. **It was wrong for that song
too** — we just hadn't checked content. Probing
`led-zeppelin/good-times-bad-times` showed the bug; re-probing
18-til-i-die confirmed it was identical.

**Lesson**: any code path whose correctness depends on per-page DOM
structure must be verified against ≥2 songs with materially different
shapes (different track counts, different precount defaults, etc.).
"Verified against song X" doesn't mean "works for all songs"; it means
"works for song X, possibly by coincidence".

## Known gap (not fixed in 2026-05-09 commits)

**Legacy Selenium fallback path is still unbounded.** The cascade fix
in `karaoke_automator.py _download_all_tracks_direct_api` only bounds
the direct-API path. If `capture_session` itself fails for a whole
song (rare — site structure change, session expired, etc.), the
orchestrator falls through to legacy `_download_single_track` for
every track in that song. Legacy uses:

- `DOWNLOAD_MAX_WAIT = 90` (seconds, in `packages/configuration/config.py`)
- `_wait_for_download_readiness(max_wait=60)` (in `download_manager.py`)
- `_monitor_download_completion` polls until `DOWNLOAD_MAX_WAIT` elapses

Worst case: N tracks × ~90s + retry tiers = many minutes per song.
Plus `_retry_song_failures` and `_retry_all_failures` add more rounds.
A capture failure on a multi-song run could still hang for a long time
even with the direct-API path bounded.

**To fix when needed:**
- Bound `DOWNLOAD_MAX_WAIT` and `_wait_for_download_readiness` to ~30s
  (matches user's stated per-track budget).
- Add a cascade-abort to the legacy whole-song fallback, mirroring the
  direct-API logic (`_download_all_tracks_direct_api` lines around the
  `for track in tracks_to_process` loop).
- Or: surface capture failures to the user immediately ("session
  capture failed for this song; skipping") instead of silently falling
  through to a slow path.

This isn't bothering anyone today (capture rarely fails), but it's a
latent worst-case that should be capped before someone hits it.

## What changed in code

### `841b38d` — off-by-one mapping
- `packages/download_management/direct_api/trackslevels.py`: replaced
  template-based `build_trackslevels(template, target_pos)` with
  `build_trackslevels(mixer_tracks, target_index)`. New function
  iterates `mixer.tracks` in DOM order, generates one segment per
  entry with `id = src_id + 1`.
- `packages/download_management/direct_api/session_capture.py`: added
  `_read_mixer_tracks` to capture `window.mixer.tracks` via JS.
- `packages/download_management/direct_api/direct_downloader.py`:
  `download_track(target_index, ...)` takes DOM data-index directly;
  internally builds trackslevels from captured `mixer_tracks`.
- `karaoke_automator.py`: removed click-track special case (Click is
  now just `mixer.tracks[0]`, downloaded via the same path as any
  other track — no `level=0` workaround).

### `4ab435b` — precount + cascade
- `session_capture.py`: added `_read_live_precount` (reads
  `window.mixer.parameters.precount`) and overrides the static value.
- `karaoke_automator.py _download_all_tracks_direct_api`: bounded
  `max_wait` to 25s, cascade-abort after 2 consecutive failures, no
  auto-retry to legacy on direct-API failure.

## Probes worth keeping

- `tools/probe_track_mapping.py` — for any song, prints DOM order,
  `mixer.tracks` info, captured template, and `pos N → server says X`
  rows. **Run this first** if a new song's downloads have wrong
  content.

(Other probes used during this investigation —
`probe_audio_verify.py`, `probe_extended_trackslevels.py`,
`probe_mixer_internals.py`, `compare_audio.py` — were one-off and
removed. Their key techniques are documented above; reconstruct from
this doc if needed.)
