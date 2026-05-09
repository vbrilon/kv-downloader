# Plan: Direct-API download path

**Goal:** Replace the per-track Selenium-driven download flow (solo button →
click download → modal handling → Chrome download manager) with direct HTTP
calls to `basket.php` + `begin_download.html`. Drops per-track time from
~16-18s to ~10-11s and eliminates a class of Selenium failure modes.

**Status:** Not started. Discovered 2026-05-08 via the Tier 2 investigation
(see `2026-05-08-tier2-parallel-downloads.md` postmortem). All probes that
prove the flow exist in `tools/probe_direct_api.py`.

**Estimated effort:** 2-3 days focused work + iterative validation runs.

---

## Why this is worth doing

| | Existing (Selenium) | Direct API |
|---|---|---|
| Solo via UI + audio_server_sync | ~3s | (skipped) |
| Click download + modal handling | ~1s | (skipped) |
| `basket.php` | (inside the click) | ~0.7s |
| Server mix-gen | ~14s | ~7s (warm caches in probe; budget ~14s) |
| File delivery via Chrome | ~2s | ~2s (`requests`) |
| **Per-track total** | **~16-18s** | **~10-11s** |

15-track song: **~4 min → ~2:30** (~37% reduction). With pipelining
(also in `PLAN.md`) on top, ~50–60%.

The qualitative win is just as important: drops solo-button retry hammer,
modal handling, Chrome download-manager filename collisions, and
crdownload polling. Less surface area for site DOM changes to break us.

---

## Architecture

**Stays as-is:**
- `LoginManager` + `chrome_profile` for session management
- `TrackManager.discover_tracks()` for the per-song track list
- `TrackManager.ensure_intro_count_enabled()` and `adjust_key()` for mixer
  setup before download
- `FileManager` for filename cleanup and validation
- `StatsReporter` and `ProgressTracker` for observability
- `KaraokeVersionAutomator` as orchestrator

**New:**
- `packages/download_management/direct_api/` (new sub-package)
  - `session_capture.py` — captures the basket template via one UI-triggered
    download per song
  - `direct_downloader.py` — sends `basket.php`, polls `begin_download.html`,
    fetches MP3 via `requests`
  - `trackslevels.py` — builds trackslevels strings, preserving the
    bare-numeric edge slots that encode flags

**Replaced:**
- The per-track section of `DownloadManager.download_current_mix()` —
  specifically `_navigate_and_find_download_button`, `_execute_download_click`,
  `_wait_for_download_readiness`, and `_monitor_download_completion`. These
  collapse into one direct-API call.

**Kept around but unused (initially):** the existing Selenium download
methods stay in tree for fallback/comparison until Phase 5. Don't delete
yet — see Phase 5.

---

## Phased plan

### Phase 1: Core direct-API downloader (~1 day)

**Deliverable:** Standalone `DirectDownloader` class that, given a
`requests.Session` (with cookies) and a basket template dict, downloads any
single track to a destination path. No Selenium dependency.

**Files:**
- `packages/download_management/direct_api/__init__.py`
- `packages/download_management/direct_api/trackslevels.py`
  - `build_trackslevels(template: str, target_pos: int, level: int = 100) -> str`
  - Preserves bare-numeric segments verbatim (positions without a `.id`
    suffix encode the precount flag — changing them triggers HTTP 500)
  - `parse_segments(template: str) -> list[(pos, id, level)]` for diagnostics
- `packages/download_management/direct_api/direct_downloader.py`
  - `class DirectDownloader`:
    - `__init__(session, template_params, cookies, ua)`
    - `download_track(target_pos: int, dest: Path, *, max_wait: int = 60) -> DownloadResult`
    - `_call_basket(trackslevels)` — GET, raises on non-200
    - `_poll_until_hash_changes(prev_hash, max_wait, interval)` — returns
      new URL on hash change; raises on timeout
    - `_fetch_mp3(url, dest)` — streamed write via `requests`
    - `_url_hash(url)` — `re.search(r"/sl/[^/]+/([a-f0-9]+)/", url)`

**Tests** (`tests/unit/test_direct_downloader.py`):
- `build_trackslevels`:
  - preserves bare-numeric edges (positions 0 and N-1)
  - sets one `.id` segment to the requested level, others to 0
  - round-trip: parse_segments(build_trackslevels(t, k)) shows exactly one
    segment with `level=k`
- `_url_hash`:
  - extracts `aca6624e80…` from a real CDN URL
  - returns None for malformed URLs
- `download_track` happy path with mocked `requests.Session`:
  - basket call fires with the right URL
  - polling returns when mock advances the hash
  - fetch writes the body to `dest`
- Error paths:
  - basket returns 500 → raises `BasketUpdateError` with URL + body excerpt
  - polling never sees a hash change → raises `MixGenTimeout`
  - fetch network error → raises `MP3FetchError`

### Phase 2: Session capture helper (~0.5 day)

**Deliverable:** `capture_session(driver, song_url) -> SessionContext` that
returns everything `DirectDownloader` needs (cookies, basket template, UA).

**Files:**
- `packages/download_management/direct_api/session_capture.py`
  - `@dataclass class SessionContext: cookies: dict; template_params: dict; ua: str`
  - `capture_session(driver, song_url, log) -> SessionContext`
    - Trigger one UI download via existing `DownloadManager` click logic
    - Watch the perf log for the `basket.php` URL
    - Parse query params → `template_params`
    - Snapshot `driver.get_cookies()` → `cookies`
    - Read `navigator.userAgent` → `ua`
- ChromeManager: add an `enable_perf_logging: bool = False` constructor
  param. When True, sets the `goog:loggingPrefs` capability before driver
  init. (The probes use a monkeypatch — replace that with the real param.)

**Tests:**
- Unit-test the URL parser with sample URLs
- Smoke test (manual): run against the configured song, assert
  `template_params` has the expected keys (`prodid`, `s`, `pannings`,
  `pitch`, `precount`, `bkac`, `famid`, `method`, `trackslevels`)

**Open questions to investigate during this phase:**
- **Q1.** Can we read `prodid` + `pannings` directly from the page DOM
  (hidden form fields, JS variables) and skip the UI download click? Would
  drop the per-song setup time from ~16s to ~2s. Worth ~14s/song.
  Investigate by `view-source:` on the song page and grepping for `prodid`.
- **Q2.** Does the basket template change between sessions for the same
  song+account? If stable, we can cache it on disk and skip capture
  entirely on repeat runs.

### Phase 3: Wire as feature-flagged path (~0.5 day)

**Deliverable:** A `--direct-api` CLI flag that routes per-track downloads
through the new path while leaving Selenium as the default.

**Files:**
- `karaoke_automator.py`:
  - Add `--direct-api` to argparse
  - In `KaraokeVersionAutomator.__init__`, store the flag
  - New method `_download_all_tracks_direct_api(song, tracks, song_key)`
    that mirrors `_download_all_tracks` but uses `DirectDownloader`
- `_download_all_tracks` dispatches to direct-API or legacy based on flag
- The direct-API path:
  1. (Already done by existing flow) ensure intro count + key adjustment
  2. Call `capture_session(driver, song_url)` once
  3. For each track:
     - Determine `target_pos` for this track's data-index (need a mapping;
       see below)
     - `DirectDownloader.download_track(target_pos, temp_path)`
     - Apply existing `FileManager` cleanup + validation
     - Update progress + stats via existing callbacks
- Track-index → trackslevels-position mapping. From observation: position 0
  is the precount flag; positions 1..N correspond to data-index 1..N (with
  trackslevels id N+1). Verify this against multiple songs before relying.

**Validation:**
- Run with and without `--direct-api` against the same song
- Compare wall times
- Compare downloaded file SHA-256s — they should be byte-identical (or
  acceptably similar accounting for any mp3-encoder nondeterminism)
- Run with `--max-tracks 3` first, then full song

### Phase 4: Hardening (~0.5 day)

**Errors and recovery:**

| Failure | Detection | Recovery |
|---|---|---|
| Cookie expired mid-song | `basket.php` returns 401/302 to login | Spin Selenium back up, re-auth via `LoginManager`, refresh `SessionContext.cookies`, retry once |
| `basket.php` 500 | non-200 status | Log full URL + response body excerpt; fail this track; continue |
| `begin_download.html` never returns new hash | timeout | Retry once with `max_wait * 2`; then fail this track |
| MP3 GET fails (5xx, network) | exception in `_fetch_mp3` | Retry up to 3x with exponential backoff (1s, 2s, 4s) |
| URL hash flipped but content matches a previous track | post-fetch SHA check | Likely server returned stale; re-issue basket and poll again |
| Site adds CSRF token | 403 on basket.php | Log clearly; fall back to legacy Selenium path for the rest of the song |

**Logging:**
- Per-track: `basket_call_ms`, `mix_gen_wait_s`, `fetch_s`, `total_s`
- Per-song: `setup_s` (capture_session cost), per-track summary, total
- Use existing `performance_profiler` decorators for consistency

**Adaptive polling:**
- Initial poll interval: 2s
- After 10s without hash change: back off to 4s
- Hard cap: 60s (configurable via `--mix-gen-timeout`)

### Phase 5: Cutover (~0.25 day)

**Switch the default. Keep an opt-out.**

- Default: direct-API on
- Add `--legacy-selenium-download` for opt-out (debug/comparison)
- Update `CLAUDE.md` Architecture section
- Update `README.md` with the new flag
- After 2 weeks of clean runs, *delete* the legacy per-track download code
  paths (the methods replaced in Phase 1 architecture). Don't delete
  earlier — keep the safety net.

### Phase 6 (separate plan): Pipelining

Once direct-API is the default, layering pipelining on top is much easier:
fire `basket.php(N+1)` immediately when track N's MP3 fetch starts. Owned
by the pipelining entry in `PLAN.md`.

---

## Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Site adds CSRF token to `basket.php` | Medium | High | Detect via 403; fall back to legacy Selenium path; alert |
| Cookie expiry during long-running session | Low | Medium | Re-auth via `LoginManager`; refresh `SessionContext` |
| Basket template format changes (new param, renamed key) | Low | High | Re-capture per song from a fresh UI click; legacy fallback |
| Per-account rate limit on `basket.php` | Low | Medium | Keep cadence ≤ existing flow's natural rate (one per ~10s) |
| Pannings need to differ per track in some unknown way | Low | Medium | Investigate: does the UI flow ever vary pannings between tracks? Probe before relying on a constant per song |
| Server CDN hash collision across runs (cached prior mix) | Low | Low | We already handle: poll until hash changes from `prev_hash` |

---

## Open questions

1. **Q1 (Phase 2)** — Can `prodid` + `pannings` be scraped from page DOM
   without a UI download click? Would save ~14s/song setup cost.
2. **Q2 (Phase 2)** — Is the basket template stable across sessions for the
   same song+account? If yes, cache on disk → skip capture on repeat runs.
3. **Q3 (Phase 3)** — Verify the trackslevels-position → data-index mapping
   on a 2nd and 3rd song (different track counts) before relying on it.
4. **Q4 (Phase 4)** — Does the server enforce a minimum interval between
   consecutive `basket.php` calls? Probe by firing 5 in 2s and watching for
   429/throttle.

---

## Non-goals

- **Parallelism.** The Tier 2 postmortem confirmed it's structurally
  infeasible on a single account (per-prodid basket cancellation). Don't
  re-attempt under the guise of "direct API enables it" — it doesn't.
- **Multi-account.** Out of scope.
- **Removing Selenium entirely.** Still needed for login (chrome_profile),
  intro count + key adjustment, and the basket template capture.
- **Pipelining.** Separate plan; can layer on after direct-API ships.

---

## Validation gates

Before declaring each phase done:

- **Phase 1:** all unit tests pass; integration test downloads one track
  from a real session and the bytes match a known-good baseline
- **Phase 2:** `capture_session` returns a `template_params` dict with all
  expected keys against three different songs (track counts varying)
- **Phase 3:** `--direct-api` produces SHA-256-identical files vs legacy
  for at least 5 tracks across 2 songs; per-track wall time at least 30%
  faster on average
- **Phase 4:** all five failure modes in the recovery table verified by
  fault injection (mock or real); no regressions vs Phase 3 timing
- **Phase 5:** 5 consecutive full-song runs with default-on, no warnings,
  no fallbacks triggered

---

## Files touched, summary

```
packages/download_management/direct_api/__init__.py            (new)
packages/download_management/direct_api/trackslevels.py        (new)
packages/download_management/direct_api/direct_downloader.py   (new)
packages/download_management/direct_api/session_capture.py     (new)
packages/browser/chrome_manager.py                              (small: enable_perf_logging param)
karaoke_automator.py                                            (--direct-api flag + dispatch)
tests/unit/test_direct_downloader.py                            (new)
tests/unit/test_trackslevels.py                                 (new)
CLAUDE.md                                                       (architecture update)
README.md                                                       (flag doc)
docs/plans/2026-05-08-direct-api-rewrite.md                     (this plan)
```

After Phase 5 cutover, also remove (separate commit):
```
packages/download_management/download_manager.py — _navigate_and_find_download_button,
  _execute_download_click, _wait_for_download_readiness, _monitor_download_completion,
  _wait_for_download_readiness, _monitor_download_progress, _check_for_in_progress_downloads,
  related helpers if unused
```
