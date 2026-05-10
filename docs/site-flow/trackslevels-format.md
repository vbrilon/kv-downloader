# `trackslevels` Format Reference

The `trackslevels` query-param on `basket.php` tells the server which
tracks to mix at which volumes. Format and per-song mapping verified
empirically 2026-05-09 against `bryan-adams/18-til-i-die` AND
`led-zeppelin/good-times-bad-times`.

Code: `packages/download_management/direct_api/trackslevels.py`,
`packages/download_management/direct_api/session_capture.py`.

## Wire format

Comma-separated segments, one per slot. Two kinds:

| Shape | Meaning |
|---|---|
| `<level>.<id>` | A track slot. `level` ∈ 0..100 (volume %), `id` is the per-song server-side track id. |
| `<bare-number>` | A *flag* slot — leading `1` is the precount-enabled flag, trailing `0` is currently unknown but server-required. |

Example string captured from led-zeppelin/good-times-bad-times's inline
`mixer.setLevels(...)`:

```
1,0.2,0.3,0.4,0.5,0.6,0.7,100.8,0
^   ^                       ^^^^ ^
│   │                       │    │
│   │                       │    └ trailing edge (bare; leave alone)
│   └ pos 1, id=2, level=0
└ pos 0: leading edge (bare; leave alone)
```

9 segments → 7 audible slots (positions 1..7) + 2 bare flag edges.

## ⚠️ Critical: bare-numeric slots

**Do NOT change bare-numeric slots.** `basket.php` runs a server-side
consistency check; modifying position 0 or position N-1 returns HTTP
500. Verified empirically (`tools/probe_direct_api.py`).

## Authoritative mapping: use `mixer.tracks`, NOT the captured template

The runtime build path uses **the page's own `window.mixer.tracks` array**
(read via JS in `session_capture._read_mixer_tracks`) — NOT the captured
`setLevels` template — for two reasons:

1. **The captured template is incomplete.** It omits the slot for the
   LAST DOM track. Both probed songs had this property (`bryan-adams/18-til-i-die`:
   13 DOM tracks, 12 audible slots; `led-zeppelin/good-times-bad-times`:
   8 DOM tracks, 7 audible slots). To solo the last track we must build
   an *extended* trackslevels with one more slot — verified accepted by
   the server in `tools/probe_extended_trackslevels.py`.

2. **The `<id>` labels in trackslevels are offset by +1 from the source
   track id.** `mixer.tracks[K]` has its source URL at `…/<src_id>.mp3`
   (e.g. `/3.mp3` for Bass on Good Times Bad Times). The corresponding
   trackslevels segment has `id = src_id + 1`. So to solo
   `mixer.tracks[K]`, we put the level at the segment whose label is
   `src_id + 1` — which (universally, both songs) is **trackslevels
   position K+1**.

So the universal rule is:

> **trackslevels position K+1 solos `mixer.tracks[K]`** (where K is the
> DOM `data-index`, 0-based)

`build_trackslevels(mixer_tracks, target_index, level)` constructs the
full trackslevels from scratch:

```
1,<level>.<src_id+1>,...,<level>.<src_id+1>,0
  ^^^^^^^^^^^^^^^^^^
  one slot per mixer.tracks entry, in DOM order;
  level = `level` arg at target_index, 0 elsewhere
```

## Soloing the click track

`mixer.tracks[0]` is the Click row (with `isClick=True`). It's a *real*
audible slot in the trackslevels — not a separate flag — so soloing it
is exactly the same operation as any other track:

```python
downloader.download_track(target_index=0, dest=dest, level=100)
# Renders the click track audio (clicks throughout the song).
```

(The previous code had a special case sending `level=0` to produce a
near-silent file, which the bug-report user described as "empty". After
the 2026-05-09 fix, the click track download contains the actual click
audio — useful as a metronome reference.)

The separate `precount=1` flag (set via the `Intro count` checkbox in
the UI) adds a 1-2 click count-in to the START of every soloed render —
orthogonal to which track is soloed.

## What `id` really means in trackslevels

The `<id>` in a `<level>.<id>` segment is `src_id + 1` where `src_id`
is the per-track source-MP3 number (mixer.tracks[K].url ends in
`<src_id>.mp3`). The +1 offset is empirical — likely a server-side
1-based vs 0-based convention. Whatever the reason, our code derives
ids from `mixer.tracks[K].src_id + 1` so it stays correct without
caring about the underlying convention.

## Reference test fixture

`tests/fixtures/mixer_init_script.js` contains the verbatim inline
script from `bryan-adams/18-til-i-die`. Useful for replaying
`session_capture.parse_mixer_script` deterministically in tests.

## Server-side flakiness: cascade timeouts

Empirically (observed 2026-05-09 during heavy reuse of one song page),
the server can stop producing fresh renders after several rapid
basket.php updates in a single session. Symptom: the first failing
track returns `MixGenTimeout` with `last_url=<old hash>` (server
serving the cart's previous render); subsequent tracks return
`last_url=None` (server returns no MP3 URL at all). Looks like
session-level rate-limiting or cart-state breakdown.

Mitigation in code (`karaoke_automator.py
_download_all_tracks_direct_api`):

- `max_wait` per direct-API call is bounded to **25s** (typical
  successful render is 5–10s, so 25s is a generous ceiling).
- After **2 consecutive direct-API failures** in one song, abort the
  remaining tracks for that song and surface a "re-run later" message
  to the user. Keeps worst-case time-to-failure to ~50s instead of
  N × 25s for N remaining tracks.
- Direct-API failures are NOT auto-retried via legacy Selenium —
  the same server-state issue affects both paths, so a retry just
  doubles the wait.

If you see this happen repeatedly for the same song without unusual
recent activity, the server may have changed its rate-limit thresholds;
re-investigate.

## Probing tool

`tools/probe_track_mapping.py` — for a given song, calls `basket.php`
for each non-edge position in the captured template and reports the
URL filename the server returns (= the actually-soloed-track name),
plus the `mixer.tracks` info. Run this if the per-track download
content for a new song looks wrong; it'll surface any
position-to-track misalignment.
