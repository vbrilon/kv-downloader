# Direct-API Baseline (2026-05-09)

First post-cutover measurement. Direct-API is now the default download
path; legacy Selenium remains as `--legacy-selenium-download`.

## Headline

| Path | Avg per track | 6-track wall time | Reliability |
|---|---|---|---|
| Direct-API (new default) | **12.1 s** | **1m 19.4 s** | **6/6 (100%)** |
| Legacy Selenium (prior default) | ~24 s | ~78 s for 3 tracks | (not run on this song) |

Per-track speedup: ~2× (49% reduction). Plan estimated 37%; we beat it.

## Per-track timings

Måneskin — *Beggin'* (6 tracks, full song, fresh — never cached):

| Track | Time | Notes |
|---|---|---|
| Intro Count (Click + Key) | 12 s | Click track; renders via all-zero levels + `precount=1` |
| Click | 12 s | |
| Drum Kit | 11 s | |
| Bass | 17 s | Slowest track; still well under 60 s timeout |
| Electric Guitar | 8 s | Fastest; cache warm at this point |
| Lead Vocal | 12 s | |

All 6 files: 8,754,553 bytes (consistent — identical render duration).

## How to reproduce

```bash
# Edit songs.yaml to point at the song
# Clear any existing folder for it (or use --max-tracks N for partial)
bin/python karaoke_automator.py
```

Uses cached Chrome session (`chrome_profile/`); first run after a
session expiry will be ~10 s slower.

## Earlier comparison run (2026-05-08, 18 Til I Die, 3 tracks)

| Run | Path | Result | Avg/track |
|---|---|---|---|
| 1 (baseline gen) | Legacy | 3/3 ✅ | 24.2 s |
| 2 (verification) | Legacy | 3/3 ✅ | ~24.5 s |
| 3 (direct-API smoke) | direct-API | 3/3 ✅ | 12.3 s |
| 4 (default-on smoke) | direct-API → legacy fallback | 2/3 (Bass server-side transient — failed in *all three* paths) | n/a |

Run 4 confirmed the fallback chain works correctly: a clear
`MixGenTimeout` from direct-API automatically routed Bass through the
existing Tier 1 / Tier 2 retry tiers. The same track failed via legacy
too — server-side issue, not a direct-API regression.

## Configuration at time of measurement

- Default path: direct-API
- `DOWNLOAD_MAX_WAIT`: 90 s (legacy path)
- `max_wait` (direct-API mix-gen poll): 60 s
- `poll_interval`: 2 s
- `fetch_max_attempts`: 3 with backoff (1 s, 2 s, 4 s)

## Notes for future comparisons

- **Don't** use SHA-256 equality as a regression check — see
  `docs/site-flow/mp3-encoder-nondeterminism.md`. Use file size
  instead.
- **Do** clear the song folder before measuring, otherwise the
  per-track skip in `_track_file_already_exists` makes runs look
  artificially fast.
- A typical 6-track song clears in ~80 s on direct-API; budget 5 min
  for a 13-track song.
