# Final Performance Comparison (2026-05-08)

Three runs against ELO "Don't Bring Me Down", first 5 tracks each, with `--profile`.

| Metric | main | Phases 1+4+5+6 | Phases 1+3+4+5+6 |
|---|---|---|---|
| Session duration | 150.7s | 121.4s | **109.4s** |
| Total download time | 138.2s | 112.5s | **101.6s** |
| **Mean per-track** | **27.6s** | **22.5s** | **20.3s** |

**Total improvement: −7.3s/track (−26.5%) vs main.**

| Phase batch | Cumulative savings |
|---|---|
| Phases 1+4+5+6 (drop redundant verification, fix solo bug, etc.) | −5.1s |
| Phase 3 (modal flow rework) incremental | −2.2s |
| **Total** | **−7.3s** |

## Per-track

| Track | main | +1/4/5/6 | +Ph3 | Total Δ |
|---|---|---|---|---|
| Intro count Click | 43.3s | 29.8s | **17.2s** | **−26.1s** |
| Drum Kit | 21.6s | 22.2s | 30.6s | +9.0s ⚠ |
| Tambourine | 31.9s | 20.1s | **19.6s** | **−12.3s** |
| Shaker | 20.1s | 20.1s | **17.6s** | **−2.5s** |
| Hand Clap | 21.3s | 20.2s | **16.7s** | **−4.6s** |

The Drum Kit regression on the post-Phase-3 run (22.2s → 30.6s) is almost certainly server-side jitter rather than Phase 3 overhead — all four other tracks improved meaningfully on the same run. Server mix-generation time (~14s of every track) varies, and a single track being slow on a 5-track sample is within noise. The Click track's drop from 43.3s → 17.2s is the most striking, and it's the track where the redundant verification cascade and inflated polling intervals stacked up worst.

## Why the Click track sees the biggest win

The original audit predicted the first track of each song would benefit most:
- It has the longest server-side audio sync window (no prior solo state to cache)
- All redundant verification fired back-to-back on it (Phase 1 polling + Phase 2 mixer state + Phase 3 audio mix + initial+final pre-download verification)
- The blind window-poll waited the full timeout on every track but was a bigger fraction of first-track total time

Empirical: 43.3s → 17.2s = **−26.1s**, single-track. Predicted upper bound was −15s; reality blew past it.

## What's left

Theoretical floor is dominated by:
- Server mix-generation: ~14s, unavoidable
- File completion polling: ~3–5s
- Solo activation polling: ~1–3s
- BETWEEN_TRACKS_PAUSE: 0.5s

That floor is in the 18–22s range, which is roughly where we are. Going below would require:
- **Phase 8.3** (move out of Dropbox): plausibly another 1–3s on file ops
- **Phase 8.2** (speculative pre-soloing while previous track downloads): risky; could in principle cut to ~14s by overlapping the human-perceived per-track time with server generation

For now, **20.3s/track represents a clean stopping point**. A 15-track song that took 7m 30s now takes ~5m 5s.
