# Phase 8 Research Spikes (2026-05-08)

## 8.1 — Direct API call to `mixer.getMix()` instead of clicking the button

**Question:** Can we bypass the Selenium download-button click + popup flow by calling `mixer.getMix()` directly?

**Evidence (from Phase 2 live inspection):**
- `mixer.getMix` body:
  ```js
  this.parameters.trackslevels = this.getLevels();
  this.parameters.pannings = this.getPannings();
  if (typeof this.getMixCallback === "function") this.getMixCallback();
  this.editMix();
  ```
- The function returns `void`. The download URL appears asynchronously inside the modal DOM after `editMix()` completes its backend request (~14s of server time).

**Conclusion: SKIP.** There is no faster path. The existing JS click `arguments[0].click()` already fires the same `onclick="mixer.getMix();return false;"` handler — which IS the API call. Spending engineering effort on calling `getMix()` directly via `execute_script` would yield zero perceptible improvement, and we'd still need to wait for the modal to populate to extract the download URL.

## 8.3 — Move downloads out of Dropbox-synced folder — **TESTED, RULED OUT**

**Original hypothesis:** Dropbox-synced folders add measurable filesystem overhead (sync events, CloudStorage extension serialization) to the hot path.

**Tests run (2026-05-08):**

1. **End-to-end profiler comparison** (`bin/python karaoke_automator.py --profile --max-tracks 5` on each path). Result was noisy: local came out *slower* (31.0s vs 20.3s/track) but driven by a single Shaker-track outlier (17.6s → 46.4s on identical config). Server-side mix-generation jitter dominated the signal — single-run comparison is unreliable for this question.

2. **Targeted filesystem micro-benchmark** (`/tmp/fs_bench.py`, 10 iterations each, all the file ops kv-downloader does in the hot path: mkdir, 6MB write, two renames, 12 stat-polls, rmtree). This isolates filesystem from server interaction.

   | Phase | Local median | Dropbox median | Delta |
   |---|---|---|---|
   | mkdir | 0.03ms | 0.03ms | ~0 |
   | write 6MB | 2.21ms | 2.34ms | +0.14ms |
   | rename .crdownload | 0.06ms | 0.08ms | +0.02ms |
   | 12× stat polls | 0.28ms | 0.29ms | +0.01ms |
   | rename cleanup | 0.04ms | 0.04ms | ~0 |
   | rmtree | 0.11ms | 0.11ms | ~0 |
   | **TOTAL per song** | **2.72ms** | **2.90ms** | **+0.18ms** |

**Conclusion:** Dropbox adds ~0.18ms per song to filesystem operations. **Negligible.** The 14s of server-side mix-generation per track dwarfs every filesystem cost we touch.

**Verdict: do not pursue.** Hypothesis disproven empirically. The macOS File Provider extension is fast enough that local-vs-Dropbox is invisible at the granularity our hot path operates at.

## Other spikes from PLAN.md (not pursued)

- **8.2 Speculative pre-soloing** of next track during current download: deferred. Solo state is shared on the page; concurrent state mutation while a download is in flight risks corrupting the in-flight mix. The 22.5s/track post-Phase-1-through-6 number is good enough that this risky change is hard to justify. Skip unless we hit hard requirements for further speedup.
- **8.4 Wire `--profile` into CI**: deferred. The user runs this tool manually; CI is overkill. The existing `PerformanceBaselineTester` already supports A/B comparisons for ad-hoc regression checks.
