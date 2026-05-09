# Architecture

A code-structure reference for the karaoke-version.com automation. Read
this before making structural changes (new modules, cross-cutting
refactors, dependency-injection rewiring, error-handling overhauls).

For user-facing setup (install, songs.yaml format, CLI flags), see the
top-level `README.md`. For perf-tuning history and the current
performance budget, see `docs/PERF.md`. For verified DOM selectors and
download-modal behavior, see `docs/site-flow/`.

---

## Package layout

```
packages/
├── authentication/        # Login, session persistence, chrome_profile reuse
├── browser/               # Chrome setup, download-path management
├── configuration/         # YAML parsing, validation, constants, site selectors
├── di/                    # Dependency-injection container + interfaces
├── download_management/
│   ├── download_manager.py   # Legacy Selenium per-track flow (fallback)
│   └── direct_api/           # Default direct-HTTP flow (post 2026-05-08)
├── file_operations/       # File cleanup, path rewriting, audio validation
├── progress/              # Live progress bar + stats reporter
├── track_management/      # Track discovery, solo isolation, mixer controls
└── utils/                 # Logging, error handling, performance profiling
```

---

## Configuration (`packages/configuration/`)

- **`config.py`**: centralized constants — WebDriver timeouts
  (`WEBDRIVER_DEFAULT_TIMEOUT`, …), sleep intervals
  (`PROGRESS_UPDATE_INTERVAL`, `CLICK_HANDLER_DELAY`, …), retry limits
  and polling intervals (`TRACK_SELECTION_MAX_RETRIES`,
  `DOWNLOAD_MAX_WAIT`, …), file-match ratios, UI constants.
- **`config_manager.py`**: `songs.yaml` parsing + validation.
- **`selectors.py`**: site CSS/XPath selectors (single source of truth;
  see `docs/site-flow/selectors.md`).

---

## Dependency injection (`packages/di/`)

- **`DIContainer`** — lightweight service container.
- **Interfaces** (`interfaces.py`): contracts for cross-component
  communication — `IProgressTracker`, `IFileManager`, `IChromeManager`,
  `IStatsReporter`, `IConfig`.
- **Adapters**: bridge concrete classes to those interfaces.
- **Factory** (`factory.py`): wires up the container and produces the
  `DownloadManager` for the orchestrator.

---

## Error handling (`packages/utils/error_handling.py`)

Decorators for consistent failure modes:
- **`@selenium_safe`** — Selenium operations
- **`@validation_safe`** — bool-returning validation methods
- **`@file_operation_safe`** — file-system operations
- **`@retry_on_failure`** — exponential-backoff retry
- **`ErrorContext`** — context manager for compound operations

---

## Performance profiling (`packages/utils/performance_profiler.py`)

Multi-tier (System → Component → Method → Operation) timing collection.

- **`@profile_timing(name, component, tier)`** — generic method timing.
- **`@profile_selenium`** — adds timeout/retry tracking to Selenium ops.
- **`PerformanceProfiler`** — thread-safe collector with optional
  `psutil` memory tracking; produces hierarchical reports.
- **A/B testing** (`baseline_tester.py`): `PerformanceBaselineTester`
  switches between named configurations (`current`, `pre_optimization`,
  `solo_only`, `download_only`) for regression analysis. Results land
  in `logs/performance/baselines/`. CLI: `--baseline-test`,
  `--ab-test`, `--list-baselines`.

For the current perf budget and per-track timing, see `docs/PERF.md`.

---

## Track management (`packages/track_management/`)

Up to 15 tracks per song (data-index 0..14). Track types are detected
automatically (`click`, `bass`, `drums`, `vocal`, `standard`) and feed
adaptive timeouts:

| Track type | Solo activation timeout |
|------------|-------------------------|
| Standard, ≤8-track song | 7s |
| Standard, 9+-track song | 10s |
| Bass / drums | 10s |
| Click | 12s |

**Solo isolation** (`solo_track`) is two-phase:
1. **Phase 1**: poll button class/ARIA/data-state at 200 ms; 8 s cap.
2. **Phase 2**: deterministic DOM signal that the audio server has
   synced (typically 0.3-2 s).

`ensure_only_track_active()` clears just the conflicting solos
(selective) instead of all solos (full clear) to avoid race conditions
in headless mode.

---

## Download management (`packages/download_management/`)

### Default: direct-API (`direct_api/`)

Per-track downloads are three HTTP calls — no UI click, no Chrome
download manager. ~2× faster per track than the legacy path.

| Module | Role |
|---|---|
| `trackslevels.py` | Pure functions for the `trackslevels` query param. Bare-numeric edges (precount flag) preserved verbatim — changing them returns HTTP 500. |
| `direct_downloader.py` | `DirectDownloader.download_track()`. Calls `basket.php` with new trackslevels, polls `begin_download.html` until the CDN URL hash flips, fetches MP3. Maintains `_last_hash` so subsequent calls skip the re-snapshot. 3× retry with exponential backoff on transient CDN failures. |
| `session_capture.py` | `capture_session(driver, song_url)` reads cookies, UA, and the basket template from the page's inline `mixer.setLevels` script. Pure parser is unit-tested; Selenium glue is verified by smoke runs. |

### Reliability: the fallback chain

A direct-API failure on one track does not abort the song — it routes
through the existing retry tiers in `karaoke_automator`:

```
direct-API attempt
   │ MixGenTimeout / BasketUpdateError / MP3FetchError
   ▼
record failure → Tier 1 retry (legacy Selenium, same song)
   │ still failing
   ▼
Tier 2 retry (legacy Selenium, end of run)
   │ still failing
   ▼
recorded as a permanent failure in stats; other tracks unaffected
```

Verified 2026-05-08: when the server itself couldn't render a Bass
mix (transient, also reproduced on a fresh legacy run), direct-API
failed clearly with `MixGenTimeout`, Tier 1 picked it up via legacy,
Tier 1 *also* failed, Tier 2 *also* failed. The error path is correct;
the underlying issue was server-side and not a direct-API regression.
See `docs/baselines/2026-05-09-direct-api-baseline.md` for the run
record.

`capture_session` failures (script structure changed, marker missing)
short-circuit the entire song to legacy on the first track, since
without `template_params` direct-API can't run at all.

### Fallback: legacy Selenium (`download_manager.py`)

Active when `--legacy-selenium-download` is passed, when
`capture_session` raises, or when a per-track direct-API call fails
(routed via the existing Tier 1 / Tier 2 retry tiers in
`karaoke_automator`).

`download_current_mix()` orchestrates four focused methods:
- `_navigate_and_find_download_button()` — page navigation + button location
- `_validate_pre_download_requirements()` — pre-click validation with retry
- `_execute_download_action()` — click + progress update
- `_monitor_download_completion()` — Chrome download manager monitoring

Cross-mode (headless vs visible) timing differences are accommodated by
a 30 s server-generation buffer before active monitoring kicks in.

---

## File operations (`packages/file_operations/`)

- **Caching**: 2-second TTL on file-info reads; pre-compiled
  audio/karaoke-suffix matchers. ~60-80% fewer file-system calls.
- **Cross-mode detection**: handles both new files (visible mode) and
  pre-existing-but-unprocessed files (headless mode).
- **Cleanup**: removes `_Custom_Backing_Track` suffixes that the legacy
  path produces; direct-API writes already-clean filenames.
- **Audio validation**: confirms MP3s are valid post-rename.

---

## Authentication & session (`packages/authentication/`)

- **Chrome profile reuse** via `chrome_profile/` — persistent login.
- **Session cache**: `.cache/session_data.pkl` with 24-hour expiry.
- Subsequent runs skip the full login path and resume in 2-3 s
  (vs 4-14 s cold).

---

## Logging (`packages/utils/`)

| Sink | Purpose |
|---|---|
| `logs/automation.log` | Operational tracking (production); emoji-prefixed for fast visual scan. |
| `logs/debug.log` | Verbose debug — only when `--debug` is passed. |
| `logs/performance/*.log` | Method-level timing dumps from `@profile_timing`. |
| `logs/automation_stats.json` | Structured per-track outcomes + success rates. |

Known noise: `Could not find target button` warnings during multi-step
selector trials are harmless; they're DEBUG-worthy but emitted at WARN.
Filtering them out in tooling is fine.

---

## Testing & regressions

- **117+ unit tests** (`tests/unit/`) — see `tests/run_tests.py` for the
  organized runner.
- **Regression suite**: `python tests/run_tests.py --regression-only` —
  guards against the 2× regression that prompted the perf overhaul.
- **A/B baseline tests** (`--baseline-test`, `--ab-test`) — verify
  optimization claims with deterministic comparison.
- **Smoke tests**: real-site runs are the only way to verify capture +
  full-flow behavior; do them after touching `direct_api/` or any
  Selenium glue.

Critical-path tests to keep green: download detection (visible +
headless), completion monitoring, dependency injection wiring,
trackslevels parser, direct downloader retry behavior, session capture
script-parser.
