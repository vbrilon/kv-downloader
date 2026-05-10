# CLAUDE.md — Project Index

Project: automated downloader for individual instrument tracks from
purchased songs on karaoke-version.com. Selenium-driven login + mixer
setup, direct-HTTP per-track downloads.

## Core facts

- **Default download path**: direct-HTTP API (`packages/download_management/direct_api/`).
  ~12 s/track. Fallback: legacy Selenium flow when capture fails or a
  track times out.
- **Entry point**: `karaoke_automator.py` (CLI). Songs configured in
  `songs.yaml`.
- **Python venv**: project root contains `pyvenv.cfg`; use `bin/python`
  (Python 3.13).
- **Tests**: `bin/python -m pytest tests/unit/` — 416 tests as of
  2026-05-09.
- **Auth**: Chrome profile in `chrome_profile/` + session cache in
  `.cache/session_data.pkl`.
- **Downloads land in**: `~/Dropbox/New_Song_Tracks/<song folder>/`
  (resolved by `packages/file_operations/file_manager._download_folder`).

## Doc index — read these when…

| When you're doing… | Read… |
|---|---|
| User-facing setup (install, songs.yaml format, CLI flags) | `README.md` |
| Anything structural — new package, refactor, DI rewiring, error-handling change | [`docs/architecture.md`](docs/architecture.md) |
| Current per-track perf budget + reliability data | [`docs/baselines/`](docs/baselines/) — newest file wins |
| Working on a specific in-flight feature | [`docs/plans/`](docs/plans/) — newest plan wins |
| Site DOM behavior, modal open/close, hidden inputs, mixer init script | [`docs/site-flow/`](docs/site-flow/) |
| Updating a CSS/XPath selector | [`docs/site-flow/selectors.md`](docs/site-flow/selectors.md) **and** `packages/configuration/selectors.py` |
| How basket.php params are captured from the page (direct-API foundation) | [`docs/site-flow/2026-05-09-mixer-state-capture.md`](docs/site-flow/2026-05-09-mixer-state-capture.md) |
| Building or parsing a `trackslevels` query value | [`docs/site-flow/trackslevels-format.md`](docs/site-flow/trackslevels-format.md) |
| Why same-input MP3 renders produce different SHA-256s (don't write equality tests) | [`docs/site-flow/mp3-encoder-nondeterminism.md`](docs/site-flow/mp3-encoder-nondeterminism.md) |
| Investigating a past bug — has someone already chased this? | [`docs/investigations/`](docs/investigations/) |
| Research spike before designing a feature | [`docs/spikes/`](docs/spikes/) |
| Validating a fix end-to-end against the live site | [`docs/validation/`](docs/validation/) |

## Working agreements (project-specific)

- **Branching**: feature work on `feature/<descriptive-name>`. Merge to
  `main` only after the user approves. No worktrees.
- **TDD** for direct-API and trackslevels code (pure functions / HTTP
  with mocked `requests.Session`). Smoke against the live site after
  any change touching `direct_api/` or Selenium glue.
- **Stale info**: when refactoring, update the relevant doc in `docs/`
  AND this index if a new doc topic appears.
- **No backwards-compat shims**: delete old code outright; don't leave
  `// removed` markers or rename-only aliases.
