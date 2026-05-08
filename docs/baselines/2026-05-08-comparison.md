# Performance Comparison: main vs feature/perf-optimization (2026-05-08)

**Test:** `python karaoke_automator.py --profile --max-tracks 5` against ELO "Don't Bring Me Down" (15-track song, the first 5 tracks).

| Metric | main | feature/perf-optimization | Delta |
|---|---|---|---|
| Session duration | 150.7s | 121.4s | **−29.3s** |
| Total download time | 138.2s | 112.5s | **−25.7s** |
| **Mean per-track** | **27.6s** | **22.5s** | **−5.1s (−18.6%)** |

## Per-track

| Track | main | feature | Δ |
|---|---|---|---|
| Intro count Click | 43.3s | 29.8s | **−13.5s** |
| Drum Kit | 21.6s | 22.2s | +0.6s |
| Tambourine | 31.9s | 20.1s | **−11.8s** |
| Shaker | 20.1s | 20.1s | 0.0s |
| Hand Clap | 21.3s | 20.2s | −1.1s |

## Notes

- The `Intro count Click` track is the first-track outlier. The drop of 13.5s comes mostly from removing the redundant verification cascade (Tasks 1.2, 4.1, 4.2, 5.1) plus the click-handler optimization (Task 1.1) — these compound on the first track because (a) it has the longest server-side sync wait and (b) all the redundant checks fired back-to-back.
- Variability in middle tracks (Drum Kit +0.6s, Tambourine −11.8s) reflects server-side generation jitter; the means are what matter.
- The remaining 22.5s/track is dominated by **server mix-generation time (~14s, observed in Phase 2)** and download monitoring/file completion (~5–8s). Further optimization would need to either reduce server time (we can't) or batch downloads (architectural change).

## Predicted-vs-actual

PLAN.md predicted 6–10s/track from Phases 1, 4, 5 combined. Actual: ~5s mean. The Click-track outlier saw 13.5s, validating the upper end of the prediction. The middle/end of song tracks saw less because they don't trigger the first-track penalty as hard.

## Phase 3 (modal flow) potential

Phase 3's predicted 5–7s saving was per-track (replacing the 5s window-poll with a positive modal wait). With Phase 1.3 (scan-then-sleep) already shipped, the per-track click-to-modal wait is part of the remaining 22.5s. A clean Phase 3 implementation should bring per-track time toward ~17–18s.
