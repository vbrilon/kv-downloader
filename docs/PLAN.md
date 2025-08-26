# Project Plan: kv-downloader Phased Implementation

Progress Update
- Completed: Centralized download/track/solo selectors in `packages/configuration/selectors.py`.
- Completed: Standardized WebDriverWait presence checks for download button and track/solo elements.
- Completed: `ChromeManagerAdapter.quit_driver` now falls back to `quit()` when appropriate.
- Completed: Aligned `IFileManager` interface with actual usage; updated unit tests.
- Completed: Added basic tooling configs (`pyproject.toml`, `.pre-commit-config.yaml`).
- Merged: Plan doc and Phase 1 quick wins into `main`.
Status
- Phase 1 is in progress; remaining items include optional watchdog integration and migrating any remaining hard-coded selectors/waits.
This plan translates the recommendations in `docs/RECS.md` into a pragmatic, phased roadmap. It prioritizes high-impact wins first, then deepens reliability, architecture, and developer experience. Phases can be delivered as small PRs per bullet for fast review.

## Scope & Goals
- Improve reliability and performance of automated downloads from Karaoke Version.
- Clarify architecture boundaries; enable testability and maintainability.
- Preserve current CLI behavior while adding safer defaults and observability.

## Phase 1: Quick Wins
Status: In progress
- Objectives: Land high-impact, low-risk improvements quickly.
- Key changes:
  - Align `IFileManager`/`IChromeManager` with actual usage (method names and gaps).
  - Add `packages/configuration/selectors.py` and migrate hard-coded selectors (primary + fallbacks).
  - Replace manual polls with `WebDriverWait` and `EC.*` where feasible.
  - Optional `watchdog` path for fast file event detection with automatic fallback to polling.
  - Introduce `ruff` + `mypy` + `pre-commit` configured minimally; annotate public surfaces touched.
- Deliverables: Updated interfaces/adapters, selector registry, lint/type config, watchdog integration path.
  - Delivered so far: selector registry, waits standardization (download + track/solo), interface alignment, adapter update, tooling configs.
- Acceptance: End-to-end flow still works; lint/type checks pass on touched files; reduced log noise.

## Phase 2: Interfaces & Dependency Injection
- Objectives: Improve testability and consistency.
- Key changes:
  - Constructor-inject config, profiler, and collaborators; avoid importing global config inside methods.
  - Define lean interfaces (“ports”) per component; keep adapters small.
  - Standardize `ChromeManager.quit()` naming and single shutdown ownership.
- Deliverables: Updated constructors, DI wiring, interface docs.
- Acceptance: No global config access inside methods; single shutdown path; components accept fakes in tests.

## Phase 3: Selectors & Waits Consolidation
- Objectives: Centralize selectors and standardize Selenium waits.
- Key changes:
  - Move all selectors into `selectors.py` with documented primary/fallbacks.
  - Replace `is_displayed()`/manual loops with `ExpectedConditions` helpers.
  - Tune timeouts/backoffs consistently via config constants.
- Deliverables: Selector registry and EC-based interaction helpers.
- Acceptance: Fewer transient element-not-interactable errors across repeated runs.

## Phase 4: File I/O & Reliability
- Objectives: Faster, safer file detection and naming.
- Key changes:
  - Use `os.scandir` for directory scans in hot paths.
  - Centralize filename normalization (NFKC, apostrophes policy, length caps).
  - Atomic renames and explicit `.crdownload` → final transitions.
  - Centralized retry/backoff policy and narrow exception sets with contextual error messages.
- Deliverables: File utils module, retry utilities, naming policy doc.
- Acceptance: No partial reads; predictable retries; consistent filenames; clearer error context.

## Phase 5: Architecture Refactor
- Objectives: Clarify boundaries and reduce complexity.
- Key changes:
  - Library/CLI split: move orchestration to package modules (e.g., `kv/automator`, `kv/cli`) with a thin CLI.
  - Decompose `TrackManager` and `DownloadManager` into focused modules (discovery, soloing, mixer, readiness, completion).
  - Clear lifecycle ownership in `ChromeManager` (authoritative quit after downloads settled).
- Deliverables: New package structure and thin CLI entry.
- Acceptance: Same observable behavior via CLI; minimal changes for consumers; maintained or improved coverage on moved logic.

## Phase 6: Config & CLI
- Objectives: Safer configuration with clear precedence.
- Key changes:
  - Validate `songs.yaml` using Pydantic or JSON Schema with helpful errors.
  - Typed models: `Song`, `RunOptions`, `Paths`.
  - Precedence: CLI > env > YAML > defaults; log effective config once at INFO.
  - Support `--config` flag and `KV_CONFIG` env var; predictable relative path resolution.
- Deliverables: Config models/validator and CLI enhancements.
- Acceptance: Invalid configs fail fast with crisp errors; effective config shown once.

## Phase 7: Selenium & Browser Robustness
- Objectives: More reliable readiness signals and fewer port conflicts.
- Key changes:
  - Allow ChromeDriver `Service()` to pick a free port (don’t force 9515).
  - Integrate CDP hooks for `Page.downloadWillBegin` and network `Content-Disposition`.
  - Keep DOM-based fallbacks; add tab/window handling where needed.
- Deliverables: CDP-based monitor with fallback strategy.
- Acceptance: Start/finish detection robust even when DOM changes; fewer race conditions.

## Phase 8: Logging & Telemetry
- Objectives: Actionable, structured observability.
- Key changes:
  - Demote harmless warning chatter to DEBUG (e.g., “Could not find target button”).
  - Add run/session IDs and song context via `LoggerAdapter` or `Filter`.
  - Per-run artifact directories: `logs/<YYYYMMDD_HHMMSS>/`.
  - Optional `rich`-based progress UI; keep plain mode for CI.
- Deliverables: Logging config, per-run artifact layout, optional TUI.
- Acceptance: INFO logs succinct and contextual; artifacts do not mix across runs.

## Phase 9: Testing & CI
- Objectives: Confidence and speed in development.
- Key changes:
  - HTML fixture harness to fake Selenium flows (discovery/mixer/popups) without hitting live site.
  - Deterministic tests via injected clocks/profiler; narrow exception testing.
  - GitHub Actions matrix (3.8–3.12), separate unit/integration, cache pip and drivers.
- Deliverables: Test suite structure and CI workflows.
- Acceptance: CI green across matrix; low flake rate; coverage on critical paths.

## Phase 10: Packaging & Ops
- Objectives: Smooth install and diagnostics.
- Key changes:
  - PyProject packaging with `console_scripts` entry: `kv-downloader`.
  - Constraints/pins for transitive deps.
  - `kv doctor` command for Chrome/Driver compatibility, write permissions, env checks.
- Deliverables: Installable package, doctor command, ops docs.
- Acceptance: Fresh install exposes `kv-downloader`; `kv doctor` passes on a healthy machine.

## Milestones & Sequencing
- Milestone 1 (Weeks 1–2): Phases 1–3
- Milestone 2 (Weeks 3–4): Phases 4–6
- Milestone 3 (Weeks 5–6): Phases 7–8
- Milestone 4 (Weeks 7–8): Phases 9–10

Dependencies:
- Phase 2 (DI) eases Phase 5 refactors and Phase 9 tests.
- Phase 3 (selectors/waits) reduces flakes that could mask later regressions.
- Phase 6 (config) supports reliable CLI behavior across environments.

## Risks & Mitigations
- Selector drift: Maintain primary + fallbacks; add lightweight smoke tests.
- Refactor regressions: Move in small steps with adapters; keep behavior-compatible until Phase 5 completes.
- CI flakiness: Use fixtures and injected clocks; quarantine flaky tests early.

## Out of Scope (for now)
- Major feature additions beyond download automation.
- Non-Chrome browsers.

## Working Agreements
- Small PRs (≤300 lines changed), each mapped to a single bullet.
- Definition of Done: code, tests (where applicable), docs updated, `ruff`/`mypy` clean on changed files.
- Observability-first: add contextual logging around new or risky paths.

## Next Steps
- Confirm priority order and any deadlines.
- Begin Phase 1 with separate PRs per bullet (interfaces, selectors, waits, tooling).
