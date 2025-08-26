# Recommendations: Structure, Modularity, and Performance

## Architecture

- Library/CLI split: Move orchestration logic out of `karaoke_automator.py` into a library package (`kv/automator`, `kv/cli`). Keep a thin CLI that parses flags and composes services.
- Centralize selectors: Create `packages/configuration/selectors.py` to hold all CSS/XPath selectors (login, tracks, mixer, download). Import from there to avoid drift and ease maintenance.
- Profiler injection: Replace the global profiler singleton with constructor injection of a `Profiler` interface (no‑op default). Removes the “initialize before import” constraint and simplifies tests.
- Decompose large classes: Split `TrackManager` (discovery, soloing, mixer controls, validation) and `DownloadManager` (navigation, popups, readiness detection, completion monitoring) into smaller modules for clarity and testability.
- Clear lifecycle ownership: Give `ChromeManager` a single authoritative shutdown method that performs “wait for downloads → quit”, and call it from one place only.

## Dependency Injection & Interfaces

- Align interfaces with usage:
  - `IFileManager` lacks methods used by `DownloadManager` (`wait_for_download_to_start`, `check_for_completed_downloads`, `clean_downloaded_filename`, `validate_audio_content`). Add them to the interface or stop using non‑interface methods.
  - `IChromeManager` declares `quit_driver()` but the concrete exposes `quit()`. Standardize the name and update the adapter.
- Constructor injection everywhere: Inject config, profiler, and collaborators via constructors; avoid importing `packages.configuration.config` inside methods. Improves testability and supports dynamic baselines.
- Typed ports: Define minimal “ports” (interfaces) per component; keep adapters small and focused. Avoid leaking concrete types across boundaries.

## Configuration & CLI

- Schema validation: Validate `songs.yaml` with `pydantic` or `jsonschema` to provide crisp errors (types, bounds, required fields). Emit a helpful summary on startup.
- Config layering: Establish precedence CLI > env > YAML > defaults. Expose the effective config in logs for reproducibility.
- Typed models: Introduce `@dataclass` (or Pydantic) for `Song`, `RunOptions`, and `Paths`. Pass these instead of ad‑hoc dicts.
- Secrets: Optional `keyring` support for credentials (fallback to `.env`).

## Performance

- File system monitoring: Add optional `watchdog` (FSEvents/inotify/ReadDirectoryChangesW) to detect `.crdownload`/audio file events immediately. Fallback to current polling when unavailable.
- Refine waits: Prefer `WebDriverWait(..., EC.*)` over manual loops and `page_source` scans. When polling is necessary, use capped backoff and clear totals.
- Cache scope: Keep the 2s file metadata cache for relatively static scans; bypass or shorten TTL during the hot download window to avoid stale reads.
- Overlap work (opt‑in): After a download starts, pre‑navigate and set up mixer/key for the next track (same song) while a background monitor thread waits for completion. Guard with a `--concurrency` or `--overlap` flag and ensure isolation (separate windows/tabs or careful sequencing).

## Selenium & Browser

- ChromeDriver service port: Don’t force port `9515`; allow `Service()` to pick a free port to avoid occasional bind failures.
- DevTools hooks: Use Chrome DevTools Protocol (CDP) to watch `Page.downloadWillBegin` and network `Content‑Disposition` for robust readiness signals; keep DOM fallbacks.
- ExpectedConditions first: Use `element_to_be_clickable`, `visibility_of_element_located`, `presence_of_element_located` consistently instead of manual `is_displayed()` checks.
- Robust selector strategies: In the selectors module, keep primary and fallbacks per element; document known working ones (already in CLAUDE.md) and test periodically.

## File I/O & Naming

- Faster scans: Use `os.scandir` under the hood for directory walks (lower overhead than `Path.iterdir`) in hot paths.
- Normalization: Centralize sanitize/normalize (NFKC) for folder and file names, ensure apostrophes policy is consistent, and cap lengths safely.
- Atomic operations: Use atomic renames and temporary names during cleanup to avoid partial reads; handle `.crdownload` transitions explicitly.

## Reliability & Errors

- Narrow exceptions: Replace many `except Exception` with specific exception sets; always add context (song/url/track index/selector) to error messages.
- Centralized retry policy: Keep retry budgets/backoffs in one place; log attempt counts and outcomes through the profiler to surface flakiness.
- Single shutdown path: Remove duplicate signal/finally cleanup. Route all shutdown through `ChromeManager.quit()` which itself waits for active downloads (already partly implemented).

## Logging & Telemetry

- Levels hygiene: Demote noisy “Could not find target button” style logs to DEBUG (as noted in CLAUDE.md). Keep INFO actionable.
- Structured context: Add session/run IDs, song names, and indices to log records (via a logging `Filter` or `LoggerAdapter`).
- Progress UI: Consider `rich` progress tables/bars for flicker‑free TUI (opt‑in). Keep plain mode for CI.
- Per‑run artifact dirs: Store logs and reports under `logs/<YYYYMMDD_HHMMSS>/` to avoid mixing runs.

## Testing & Tooling

- Types and lint: Add `mypy` (strict optional) and `ruff` + `black` with a `pre-commit` hook. Annotate public APIs, interfaces, and dataclasses.
- CI pipeline: GitHub Actions matrix (3.8–3.12). Separate unit/integration/regression jobs. Cache pip and (optionally) webdriver binaries.
- Selenium fakes: Create a small HTML fixture harness to simulate mixer/solo state and popups for deterministic unit/integration tests without hitting the live site.
- Deterministic tests: Favor constructor‑injected clocks and profilers to avoid time flakiness.

## Packaging & Ops

- PyProject packaging: Ship as a package with `console_scripts` entry point `kv-downloader`. Keep a constraints file to pin transitive deps.
- Configuration discovery: Support `KV_CONFIG` env var and `--config` flag; resolve relative paths predictably.
- Health checks: Add a `kv doctor` command to verify Chrome/ChromeDriver compatibility, write permissions, and environment configuration.

## Quick Wins (High Impact, Low Risk)

- Update `IFileManager`/`IChromeManager` to match actual usage and fix adapter gaps.
- Introduce `selectors.py` and migrate hard‑coded selectors.
- Replace remaining manual loops with `WebDriverWait` where feasible; standardize ExpectedConditions.
- Add `watchdog` (optional) for faster completion detection with automatic fallback.
- Add `mypy` + `ruff` + `pre-commit`; fix obvious type/interface issues early.

## Suggested Refactors (Example Shapes)

```text
packages/
  configuration/
    config.py
    selectors.py
    config_manager.py
  track_management/
    discovery.py
    soloing.py
    mixer.py
    validation.py
  download_management/
    navigation.py
    readiness.py
    popups.py
    completion.py
```

## Optional Enhancements

- Keychain storage: Use `keyring` for credentials on macOS/Windows/Linux secret stores.
- Metrics: Emit minimal metrics (counts/timings) to a local JSONL for historical trend analysis.
- Telemetry sampling: Sample debug‑level logs when `--debug` isn’t set to reduce noise while still keeping breadcrumbs.

## Notes on Backwards Compatibility

- Keep current CLI flags stable; introduce new behavior behind explicit flags (`--overlap`, `--watchdog`, `--rich-ui`).
- Maintain existing defaults; only change when data shows clear reliability/performance gains and tests cover the new path.
- Provide migration notes if interface names/methods change (e.g., `ChromeManager.quit_driver` → `quit`).

