# Performance & Cleanup Implementation Plan

> **STATUS (2026-05-08): IMPLEMENTED & MERGED.** See "Implementation Status" section below for what shipped and what's still outstanding. The task-by-task content below is preserved as historical record but should not be re-executed.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut per-track wall-clock time from ~22–25s to ~12–15s by removing redundant verification, replacing blind waits with positive DOM-based waits, and fixing one silent bug — without weakening the validated solo→audio-server-sync mechanism that prior incidents have hardened.

---

## Implementation Status (2026-05-08)

### Final result

| Metric | Pre-implementation (`main`) | After Phase 1–6 merge | After post-merge fixes | Delta vs main |
|---|---|---|---|---|
| Mean per-track | 27.6s | 20.3s | **19.5s** | **−8.1s, −29.3%** |
| 15-track song duration | ~7m 30s | ~5m 5s | **5m 6s** | −2m 24s |
| Click track | 43.3s | 17.2s | 29.7s* | −13.6s |
| Slowest non-Click | 31.9s | 30.6s | 29.2s | −2.7s |
| Success rate (full 15-track run) | — | — | **15/15 (100%)** | — |

\* Click track went up post-merge because the off-screen click bug (introduced by Phase 5's fix) was triggering on the Click→Drum Kit transition; later fixed via `ebefab8`. The 29.7s here is the new floor — 12s of mandatory click-track solo polling + ~18s server mix generation.

Validated end-to-end against ELO "Don't Bring Me Down" with full 15-track runs. Stats archived in `docs/baselines/`.

### Phases shipped (all merged to `main` via `feature/perf-optimization`)

| Phase | Outcome |
|---|---|
| 0 — Baselines | ✅ Captured pre/post stats |
| 1 — Quick wins (5 tasks: js click, drop dup verify, scan-then-sleep, dead method/import) | ✅ |
| 2 — Live modal flow inspection | ✅ Confirmed `.modal__overlay.is-open` is the activation signal |
| 3 — Modal flow rework (positive modal wait, eliminate page_source polling, reorder modal close) | ✅ |
| 4 — Verification collapse (Phase 3 audio mix, mixer state, page_source debug) | ✅ |
| 5 — `ensure_only_track_active` type-comparison fix + drop redundant solo click | ✅ |
| 6.1 — Consolidate `_is_solo_button_active*` into `packages/utils/solo_state` | ✅ |
| 6.2 — Replace misleading `WebDriverWait(...).until(lambda d: True)` no-ops | ✅ |
| 6.3 — Audit `tools/inspection/` and `archive/` | ✅ Audit done; stale scripts + `archive/` deleted |

### Post-merge fixes (2026-05-08, after Phase 1–6 merge)

Discovered during validation runs and shipped directly to `main` with user approval:

| Commit | Change | Why |
|---|---|---|
| `b8bc1e3` | Rule out Dropbox folder swap (docs only) | Micro-benchmark showed 0.18ms/song overhead — negligible |
| `ebefab8` | Off-screen solo button clicks → `js_click_with_scroll` | Three bare `button.click()` calls in `track_manager` were failing on off-screen targets after Phase 5's fix. Cost ~23s on Click + Drum Kit per song before fix. |
| `958f84d` | Pin `watchdog==6.0.0` in `requirements.txt` | The watchdog fast-path in `wait_for_download_to_start` was silently disabled (import failed); production was using polling fallback (~500ms avg detection delay). Saves ~7s per 15-track song. |
| `40399c7` | Use `string.capwords` instead of `str.title()` for URL-derived names | `str.title()` capitalized letters after apostrophes (`"Don't"` → `"Don'T"`). Folders now render correctly. |
| `0fdaac7` | Collapse embedded whitespace in track names from DOM | The "Intro count Click" caption is two siblings with `\n      ` between them; broke progress-display column alignment. |
| `4f4a178` | Propagate download-completion outcome via `result` dict | A timed-out download (e.g. CDN connection died, `.crdownload` stuck at 32KB) was returning `True` from `_monitor_download_completion`, bypassing the retry tier. Now correctly routes through retry. |
| `044d4d9` | Normalize whitespace in track-name verification | Regression from `0fdaac7`: `_verify_track_selection_state` re-read the DOM caption fresh and didn't apply the same whitespace normalization, causing every Click track download to fail verification 3× in retry. |
| `f57d1bf` | Skip already-downloaded tracks (idempotent re-runs) | Re-running on a partially-completed song was wiping the folder and re-downloading everything. Now skips tracks whose final `.mp3` is on disk; sweeps only stale `.crdownload` files. |

### Phases skipped or closed without action

| Phase | Reason |
|---|---|
| 7.1 — Per-track folder clearing investigation | Hypothesized bug **does not exist** — `cleanup_existing=False` propagates correctly. Closed. |
| 7.2 — Mystery 2s solo→download gap | Hypothesized gap **does not exist** — measured at 0ms. Closed. |
| 8.1 — Direct `mixer.getMix()` API call | Impossible: function returns void; download URL only delivered via modal DOM. Closed. |
| 8.2 — Speculative pre-soloing of next track | Deferred — risky (shared solo state, could corrupt in-flight download). Not worth it given current 19.5s/track. |
| 8.4 — Wire `--profile` into CI | Deferred — the tool runs manually; CI would be overkill. |

### Outstanding (NOT implemented; worth your consideration later)

1. **Site-selectors drift refresh.** Phase 2 live inspection (2026-05-08) found the karaoke-version.com mixer DOM has shifted: the live site uses `.custom__mixer-track-line` (with `data-index`) for tracks and `a.custom__song-download` for the download link. The codebase's primary selectors (`.track`, `a.download`) no longer match; production succeeds because of fallback selectors (`a[class*='download']` matches; `.track[data-index]` is searched but production-side Selenium queries through some other path that still works). Worth a future selectors refresh in `packages/configuration/selectors.py` to make the primary selectors accurate again. **Effort: ~30min, low risk** — replace primaries, keep fallbacks for safety. Also: `/login` returns 404; the actual form is at `/my/login.html`. The `LOGIN_URL` env default in `packages/configuration/config.py` should probably be updated. See `docs/site-flow/2026-05-08-download-modal-flow.md`.

2. **`tools/inspection/` partial-cleanup follow-up.** The 2026-05-08 audit deleted 7 broken/stale scripts and the `archive/` directory. Four scripts remain (`debug_track_discovery.py`, `inspect_key_controls.py`, `simple_page_test.py`, `verify_solo_button_detection.py`). They compile but haven't been used recently. If you don't reach for them in the next month, consider deleting too. See `docs/audits/2026-05-08-tools-inspection-audit.md`.

3. **Optional: `--force` CLI flag for clean re-runs.** Today's skip-existing change makes the default behavior idempotent. If you ever want to force re-download a song without manually deleting the folder, a `--force` flag that re-enables the old `clear_song_folder` call would take ~10 lines. Not strictly needed (manual delete works fine), but worth knowing about.

### Investigated and ruled out

- **Phase 8.3 — Moving `DOWNLOAD_FOLDER` out of Dropbox.** Tested 2026-05-08 with both an end-to-end profiler comparison (noisy, server jitter dominated) and a targeted filesystem micro-benchmark (`/tmp/fs_bench.py`) plus a watchdog event-latency benchmark (`/tmp/watchdog_bench.py`). Results: Dropbox adds 0.18ms per song to FS operations and ~1.4ms to watchdog event delivery — both within noise, completely negligible. The 14s/track of server-side mix-generation dwarfs everything else. Don't bother changing. See `docs/spikes/2026-05-08-phase-8-research.md`.

---

**Architecture:** Each phase is an independent, shippable change. Capture before/after numbers via the existing `--profile` infrastructure on every task; refuse to merge a task whose profiler delta doesn't match the prediction. Phases are ordered by risk (lowest first) so we accumulate confidence as we go.

**Tech Stack:** Python 3.13, Selenium WebDriver (Chrome), pytest, `watchdog` (filesystem events), existing `PerformanceBaselineTester` (A/B harness).

---

## Pre-Plan: Read these once before starting any task

| File | Why |
|---|---|
| `CLAUDE.md` | Architecture overview and current performance numbers |
| `packages/configuration/config.py` | All timing constants in one place |
| `packages/track_management/track_manager.py:30-37` | The `ACTIVE_SOLO_CLASS_TOKENS` invariant — DO NOT widen without evidence |
| `packages/utils/baseline_tester.py` | A/B harness; use this for all before/after measurements |

**Branching convention (from user CLAUDE.md):** Each phase ships from its own `feature/<phase-name>` branch. Never edit on `main`. Merge to `main` only after user approval.

**Measurement protocol for every task that touches hot-path code:**

```bash
# Before:
python karaoke_automator.py --profile --max-tracks 5
cp logs/automation_stats.json /tmp/before-task-N.json

# Apply change, then:
python karaoke_automator.py --profile --max-tracks 5
cp logs/automation_stats.json /tmp/after-task-N.json

# Compare:
python -c "
import json
b = json.load(open('/tmp/before-task-N.json'))
a = json.load(open('/tmp/after-task-N.json'))
print(f'Before: {b[\"session_metadata\"][\"total_download_time\"]:.1f}s')
print(f'After:  {a[\"session_metadata\"][\"total_download_time\"]:.1f}s')
"
```

If the after is not better, **stop and investigate before committing.** Performance tasks must show their work.

---

## Phase 0: Capture baseline & set up branch

### Task 0.1: Establish performance baseline

**Files:**
- Read: `packages/utils/baseline_tester.py`
- Create: `docs/baselines/2026-05-07-pre-optimization.md` (results doc only)

- [ ] **Step 1: Create feature branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/perf-optimization-phase-0
```

- [ ] **Step 2: Run baseline with profiler enabled**

```bash
python karaoke_automator.py --profile --max-tracks 5 2>&1 | tee /tmp/baseline.log
cp logs/automation_stats.json docs/baselines/2026-05-07-pre-optimization-stats.json
cp logs/performance/*.log docs/baselines/2026-05-07-pre-optimization-perf.log
```

- [ ] **Step 3: Document the numbers**

Write `docs/baselines/2026-05-07-pre-optimization.md` with these fields filled in from the JSON / perf log:

```markdown
# Pre-Optimization Baseline (2026-05-07)

- Song tested: <name>
- Tracks: <count>
- Total session duration: <seconds>
- Mean per-track download_time: <seconds>
- Slowest track: <name> @ <seconds>
- Fastest track: <name> @ <seconds>
- Per-phase breakdown (from profiler):
  - solo activation: <ms mean>
  - audio_server_sync: <ms mean>
  - validate_pre_download: <ms mean>
  - download click → modal: <ms mean>
  - download readiness wait: <ms mean>
  - file completion: <ms mean>
```

- [ ] **Step 4: Commit baseline artifacts**

```bash
git add docs/baselines/
git commit -m "docs: capture pre-optimization performance baseline"
```

---

## Phase 1: Quick wins (low risk, deterministic gains)

These four tasks touch self-contained code paths and individually save 3–5s per track. Each one ships independently.

### Task 1.1: Skip the always-intercepted regular click on the download button

**Why:** Empirical: every observed run logs `Click intercepted on download button, using JavaScript click`. The `safe_click` flow tries `element.click()`, the site intercepts it, an exception fires, then we fall back to JS click — costing ~1s per track in exception round-trip.

**Files:**
- Modify: `packages/utils/click_handlers.py` — add a JS-only variant
- Modify: `packages/download_management/download_manager.py:181` — call the new variant
- Test: `tests/unit/test_click_handlers.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_click_handlers.py`:

```python
def test_js_click_with_scroll_skips_native_click(mocker):
    """js_click_with_scroll must not call element.click(), only execute_script."""
    from packages.utils.click_handlers import js_click_with_scroll
    driver = mocker.Mock()
    element = mocker.Mock()

    js_click_with_scroll(driver, element, "download button")

    element.click.assert_not_called()
    # First execute_script call is scrollIntoView, second is the click
    assert driver.execute_script.call_count == 2
    click_call = driver.execute_script.call_args_list[1]
    assert "arguments[0].click()" in click_call[0][0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_click_handlers.py::test_js_click_with_scroll_skips_native_click -v
```

Expected: FAIL with `ImportError: cannot import name 'js_click_with_scroll'`.

- [ ] **Step 3: Add the JS-only click variant**

Append to `packages/utils/click_handlers.py`:

```python
def js_click_with_scroll(driver: WebDriver, element: WebElement, element_description: str = "element") -> bool:
    """Scroll into view then click via JavaScript, skipping the native click attempt.

    Use this when empirical evidence shows the native click is always intercepted
    (e.g. the karaoke-version download button), so the exception round-trip from
    safe_click is pure overhead.
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        driver.execute_script("arguments[0].click();", element)
        logging.debug(f"✅ {element_description} clicked via JavaScript (direct)")
        return True
    except Exception as e:
        logging.error(f"JS click failed on {element_description}: {e}")
        return False
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_click_handlers.py::test_js_click_with_scroll_skips_native_click -v
```

Expected: PASS.

- [ ] **Step 5: Wire the new function into the download click**

In `packages/download_management/download_manager.py`, change the import on line 16:

```python
from ..utils import safe_click_with_scroll, js_click_with_scroll, profile_timing, profile_selenium
```

And change line 181 from:

```python
safe_click_with_scroll(self.driver, download_button, "download button")
```

to:

```python
js_click_with_scroll(self.driver, download_button, "download button")
```

Also add `js_click_with_scroll` to `packages/utils/__init__.py` exports (find the existing `safe_click_with_scroll` line and add the new one beside it).

- [ ] **Step 6: Run full test suite**

```bash
python tests/run_tests.py
```

Expected: all green.

- [ ] **Step 7: Measure with `--profile`**

```bash
python karaoke_automator.py --profile --max-tracks 3
```

Look at `_execute_download_click` timing in the perf log — should drop by ~1s/track.

- [ ] **Step 8: Commit**

```bash
git add packages/utils/click_handlers.py packages/utils/__init__.py packages/download_management/download_manager.py tests/unit/test_click_handlers.py
git commit -m "perf: skip always-intercepted native click on download button (saves ~1s/track)"
```

### Task 1.2: Remove the duplicate "final verification before download"

**Why:** `_validate_pre_download_requirements` calls `_verify_track_selection_with_retry` twice in succession with no DOM mutation between calls. Each verification scans every solo button, costs ~100–300ms, and adds 2s of `RETRY_VERIFICATION_DELAY` per failure. The second call is pure duplication.

**Files:**
- Modify: `packages/download_management/download_manager.py:321-358`
- Test: `tests/unit/test_download_detection_regression.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_download_detection_regression.py`:

```python
def test_validate_pre_download_calls_verify_only_once(mocker):
    """The duplicate 'final verification' call must be removed."""
    from packages.download_management.download_manager import DownloadManager

    dm = mocker.Mock(spec=DownloadManager)
    dm._verify_track_selection_with_retry = mocker.Mock(return_value=True)
    dm.progress_tracker = mocker.Mock()
    dm.stats_reporter = mocker.Mock()

    # Call the real method on the mock instance
    DownloadManager._validate_pre_download_requirements(dm, "Bass", 3, "Test Song")

    assert dm._verify_track_selection_with_retry.call_count == 1, \
        f"Expected 1 verification call, got {dm._verify_track_selection_with_retry.call_count}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_download_detection_regression.py::test_validate_pre_download_calls_verify_only_once -v
```

Expected: FAIL with `Expected 1 verification call, got 2`.

- [ ] **Step 3: Remove the duplicate call**

In `packages/download_management/download_manager.py`, replace lines 321–358 with:

```python
    @profile_timing("_validate_pre_download_requirements", "download_management", "method")
    def _validate_pre_download_requirements(self, track_name, track_index, song_name):
        """Verify the solo state once before clicking download.

        We used to call this twice ("initial" and "final") with nothing in between,
        which doubled cost and hid no real bug. The single call is sufficient: the
        solo button cannot change state between two adjacent Python statements with
        no DOM interaction.
        """
        if self._verify_track_selection_with_retry(track_name, track_index):
            return True

        logging.error(f"❌ Track selection verification failed for {track_name} - BLOCKING DOWNLOAD")
        if self.progress_tracker and track_index:
            self.progress_tracker.update_track_status(track_index, 'failed')
        self.stats_reporter.record_track_completion(
            song_name, track_name, success=False,
            error_message="Solo verification failed"
        )
        return False
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_download_detection_regression.py::test_validate_pre_download_calls_verify_only_once -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

```bash
python tests/run_tests.py
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add packages/download_management/download_manager.py tests/unit/test_download_detection_regression.py
git commit -m "perf: drop duplicate pre-download verification (saves 100-300ms/track, more on retries)"
```

### Task 1.3: First-iteration fast scan in download monitoring loop

**Why:** `_monitor_download_progress` enters its loop with `adaptive_interval = 3` and sleeps 3s before the first scan — but Chrome often has the file on disk by the time `_wait_for_download_readiness` returns True. The first 3 seconds are waste.

**Files:**
- Modify: `packages/download_management/download_manager.py:651-703`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_completion_debug.py`:

```python
def test_monitor_progress_scans_before_first_sleep(mocker):
    """When the file is already present, completion must be detected immediately
    without burning the full check_interval."""
    import time
    from packages.download_management.download_manager import DownloadManager

    dm = mocker.Mock(spec=DownloadManager)
    dm._wait_for_download_readiness = mocker.Mock(return_value=True)
    dm._wait_for_check_interval = mocker.Mock(side_effect=lambda i: time.sleep(0.01))
    dm._check_for_in_progress_downloads = mocker.Mock(return_value=[])
    dm._check_for_new_downloads = mocker.Mock(return_value=["fake_completed_file"])
    dm._handle_completed_download = mocker.Mock()
    dm._update_progress_if_needed = mocker.Mock()

    context = {
        'track_name': 'Bass', 'song_name': 'Test', 'song_path': mocker.Mock(),
        'max_wait': 90, 'check_interval': 3, 'waited': 0, 'initial_files': set()
    }

    start = time.time()
    DownloadManager._monitor_download_progress(dm, context, track_index=3)
    elapsed = time.time() - start

    assert elapsed < 1.0, f"Expected fast detection, took {elapsed:.2f}s"
    dm._handle_completed_download.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_completion_debug.py::test_monitor_progress_scans_before_first_sleep -v
```

Expected: FAIL — current code waits ~3s before first scan.

- [ ] **Step 3: Reorder the loop to scan before sleeping**

In `packages/download_management/download_manager.py`, replace lines 651–703 (`_monitor_download_progress`) with:

```python
    def _monitor_download_progress(self, context, track_index):
        """Main monitoring loop. Scan-then-sleep so an already-present file is
        detected on iteration 0 instead of after one full check_interval."""
        download_ready = self._wait_for_download_readiness(context['track_name'])
        if download_ready:
            logging.info(f"✅ Download ready signal detected for {context['track_name']}")
        else:
            logging.warning(f"⚠️ Download readiness not detected for {context['track_name']}, falling back")
            self._wait_for_check_interval(3)
            context['waited'] += 3

        download_detected = False
        in_progress_detected = False
        adaptive_interval = context['check_interval']

        while context['waited'] < context['max_wait']:
            in_progress_files = self._check_for_in_progress_downloads(context['song_path'])
            new_completed_files = self._check_for_new_downloads(context)

            if in_progress_files and not in_progress_detected:
                in_progress_detected = True
                download_detected = True
                adaptive_interval = 2
                logging.info(f"🚀 Download in progress for {context['track_name']}, polling at 2s")
            elif in_progress_detected and not in_progress_files:
                adaptive_interval = 1
                logging.info(f"⚡ Download completion imminent for {context['track_name']}, polling at 1s")

            if new_completed_files:
                self._handle_completed_download(new_completed_files, context, track_index)
                return

            if download_detected and context['waited'] % 5 == 0:
                progress_status = "in progress" if in_progress_files else "completing"
                logging.info(f"   📊 Download {progress_status} for {context['track_name']} (waited {context['waited']}s)")
            else:
                self._update_progress_if_needed(context, track_index)

            self._wait_for_check_interval(adaptive_interval)
            context['waited'] += adaptive_interval

        self._handle_timeout(context['track_name'], track_index, context['song_name'])
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_completion_debug.py::test_monitor_progress_scans_before_first_sleep -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

```bash
python tests/run_tests.py
```

- [ ] **Step 6: Commit**

```bash
git add packages/download_management/download_manager.py tests/unit/test_completion_debug.py
git commit -m "perf: scan for completed file before first sleep (saves ~3s/track)"
```

### Task 1.4: Delete dead `_check_solo_activation_status` method

**Why:** Defined at `track_manager.py:388-401`, never called anywhere.

**Files:**
- Modify: `packages/track_management/track_manager.py`

- [ ] **Step 1: Confirm it is unused**

```bash
grep -rn "_check_solo_activation_status" --include="*.py" packages/ tests/ karaoke_automator.py
```

Expected output: only the definition line. No other matches.

- [ ] **Step 2: Delete the method**

In `packages/track_management/track_manager.py`, delete lines 388–401 (the entire `def _check_solo_activation_status(...)` method).

- [ ] **Step 3: Run full test suite**

```bash
python tests/run_tests.py
```

- [ ] **Step 4: Commit**

```bash
git add packages/track_management/track_manager.py
git commit -m "chore: remove dead _check_solo_activation_status method"
```

### Task 1.5: Remove dead `DOWNLOAD_MONITORING_INITIAL_WAIT` import

**Why:** Imported at `download_manager.py:25` but unused. The 30s blind wait it controlled was replaced by DOM-based readiness detection. Constant itself stays in `config.py` (still used by `baseline_tester.py`).

**Files:**
- Modify: `packages/download_management/download_manager.py:20-25`

- [ ] **Step 1: Confirm the import is unused**

```bash
grep -n "DOWNLOAD_MONITORING_INITIAL_WAIT" packages/download_management/download_manager.py
```

Expected: only the import line.

- [ ] **Step 2: Remove from the import block**

Change the multi-line import (lines 20–25) to drop `DOWNLOAD_MONITORING_INITIAL_WAIT`:

```python
from ..configuration.config import (WEBDRIVER_DEFAULT_TIMEOUT, WEBDRIVER_SHORT_TIMEOUT,
                                    WEBDRIVER_BRIEF_TIMEOUT, DOWNLOAD_MAX_WAIT,
                                    DOWNLOAD_CHECK_INTERVAL, TRACK_SELECTION_MAX_RETRIES,
                                    RETRY_VERIFICATION_DELAY, LOG_INTERVAL_SECONDS,
                                    PROGRESS_UPDATE_LOG_INTERVAL, TRACK_MATCH_MIN_RATIO)
```

- [ ] **Step 3: Run tests**

```bash
python tests/run_tests.py
```

- [ ] **Step 4: Commit**

```bash
git add packages/download_management/download_manager.py
git commit -m "chore: remove unused DOWNLOAD_MONITORING_INITIAL_WAIT import"
```

---

## Phase 2: Validate the live download flow before changing the modal handling

Phase 3 changes how we wait for the download modal. Before making those changes, we need empirical evidence about what the site actually does. The user has Chrome DevTools MCP available — use it.

### Task 2.1: Document the live download flow

**Files:**
- Create: `docs/site-flow/2026-05-07-download-modal-flow.md` (research notes only)

- [ ] **Step 1: Use Chrome DevTools MCP to log into karaoke-version.com manually**

Open the site, log in, navigate to a purchased song page.

- [ ] **Step 2: Set up DOM observation before clicking download**

In Chrome DevTools console, run:

```js
window.__events = [];
const obs = new MutationObserver(muts => {
    muts.forEach(m => {
        m.addedNodes.forEach(n => {
            if (n.nodeType === 1 && (n.matches?.('.modal,[role=dialog],.popup,.dialog,.overlay'))) {
                window.__events.push({t: performance.now(), kind: 'modal-added', cls: n.className, html: n.outerHTML.slice(0, 200)});
            }
        });
    });
});
obs.observe(document.body, {childList: true, subtree: true, attributes: true});
window.__startTime = performance.now();
```

- [ ] **Step 3: Click the download button and capture events**

Click `a.download` manually, wait 10 seconds, then run:

```js
JSON.stringify(window.__events, null, 2);
```

- [ ] **Step 4: Document findings**

Write `docs/site-flow/2026-05-07-download-modal-flow.md` answering these questions explicitly:

```markdown
# karaoke-version.com Download Modal Flow (verified 2026-05-07)

1. Does clicking download open a NEW WINDOW? (yes/no — if no, document the inline flow)
2. CSS selector that matches the modal that appears: <selector>
3. Time from click to modal visible: <ms>
4. Where does the readiness text "you can also click on the link below..." appear?
   - In the modal's `.text` content (yes/no)
   - As a child element with selector: <selector>
5. After auto-download fires, does the modal stay in the DOM (display:none) or get removed?
6. Does the readiness text remain readable in the page after the modal closes?
7. Network: does mixer.getMix() fire an XHR? URL: <url> Method: <GET/POST> Auth: <how>
```

- [ ] **Step 5: Commit findings**

```bash
git add docs/site-flow/
git commit -m "docs: document live download modal flow (basis for Phase 3)"
```

**STOP. Read the doc you just wrote before starting Phase 3.** If your assumptions about the modal are wrong, the Phase 3 implementation will silently break downloads.

---

## Phase 3: Replace blind window/page_source polling with positive modal waits

These tasks depend on Phase 2's findings. The selectors below are the current best guess — **if Phase 2 found different ones, substitute those throughout.**

### Task 3.1: Replace window-handle polling with modal-element wait

**Why:** `_execute_download_click` polls `len(driver.window_handles) > 1` and `driver.page_source.lower()` for "generating"/"preparing" — both with full timeouts that always expire because (a) no new window opens on this site, (b) page_source is huge and slow to read. Net cost: ~5s per track of mostly idle waiting.

**Files:**
- Modify: `packages/download_management/download_manager.py:162-221` (`_execute_download_click`)
- Modify: `packages/configuration/selectors.py` (add `DOWNLOAD_MODAL_SELECTORS`)

- [ ] **Step 1: Add modal selectors to centralized config**

In `packages/configuration/selectors.py`, append:

```python
# Download readiness modal — appears after clicking a.download.
# Verified 2026-05-07: the karaoke-version.com download flow opens an inline
# modal (not a new window). Match any of these so we're robust to class drift.
DOWNLOAD_MODAL_SELECTORS = [
    ".modal",
    "[role='dialog']",
    ".popup",
    ".dialog",
]
DOWNLOAD_MODAL_COMBINED_SELECTOR = ", ".join(DOWNLOAD_MODAL_SELECTORS)
```

- [ ] **Step 2: Write the test**

Add to `tests/unit/test_download_cleanup.py`:

```python
def test_execute_download_click_waits_for_modal_not_window(mocker):
    """The post-click wait must look for the modal element, not for a new window
    or page_source text. Looking for new windows wastes 5s every track on this site."""
    from packages.download_management.download_manager import DownloadManager
    from selenium.common.exceptions import TimeoutException

    dm = mocker.Mock(spec=DownloadManager)
    dm.driver = mocker.Mock()
    dm.driver.window_handles = ['main']
    dm.driver.current_url = 'https://example.com'
    dm._handle_download_popup = mocker.Mock()
    dm._check_and_handle_inline_popups = mocker.Mock()

    download_button = mocker.Mock()
    download_button.text = 'Download MP3'
    download_button.get_attribute = mocker.Mock(return_value='mixer.getMix();')

    # Patch WebDriverWait to record what was waited for
    waited_for = []
    def fake_wait(driver, timeout):
        wait = mocker.Mock()
        def until(condition):
            waited_for.append(condition)
            raise TimeoutException()
        wait.until = until
        return wait

    mocker.patch('packages.download_management.download_manager.WebDriverWait', side_effect=fake_wait)
    mocker.patch('packages.download_management.download_manager.js_click_with_scroll')

    DownloadManager._execute_download_click(dm, download_button)

    # No condition we waited on should call .page_source or .window_handles
    # (we can't introspect lambda bodies easily — assert on call counts to driver instead)
    assert dm.driver.page_source.lower.call_count == 0
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/unit/test_download_cleanup.py::test_execute_download_click_waits_for_modal_not_window -v
```

Expected: FAIL — current code calls `page_source.lower()` twice.

- [ ] **Step 4: Replace the wait logic**

In `packages/download_management/download_manager.py`, change the import on line 17:

```python
from ..configuration.selectors import DOWNLOAD_BUTTON_SELECTORS, DOWNLOAD_MODAL_COMBINED_SELECTOR
```

Replace lines 162–221 (`_execute_download_click`) with:

```python
    def _execute_download_click(self, download_button):
        """Click the download button, then wait for the readiness modal to appear.

        Verified 2026-05-07: the site opens an inline modal (no new window). We
        wait specifically for that modal — replacing the previous logic that
        polled window_handles and page_source.lower() through full timeouts.
        """
        button_text = download_button.text.strip()
        button_onclick = download_button.get_attribute('onclick') or ''
        logging.info(f"Download button text: '{button_text}'")
        if button_onclick:
            logging.info(f"Download onclick: {button_onclick[:50]}...")

        logging.info("Clicking download button...")
        js_click_with_scroll(self.driver, download_button, "download button")

        # Wait specifically for the readiness modal. 8s is generous; current
        # observed time is ~1-2s. If we time out, fall through to the file-system
        # detection path which has its own retry logic.
        try:
            WebDriverWait(self.driver, 8).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, DOWNLOAD_MODAL_COMBINED_SELECTOR))
            )
            logging.debug("✅ Download modal detected")
        except TimeoutException:
            logging.warning("⚠️ Download modal did not appear within 8s — proceeding anyway")

        return True
```

NOTE: We are deliberately NOT calling `_handle_download_popup` or `_check_and_handle_inline_popups` here anymore. Modal closure is now Task 3.2's responsibility (after we read the readiness text). Make sure tests do not rely on those being called from `_execute_download_click`.

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_download_cleanup.py::test_execute_download_click_waits_for_modal_not_window -v
```

- [ ] **Step 6: Run full suite**

```bash
python tests/run_tests.py
```

- [ ] **Step 7: Manually validate end-to-end**

Run the full automation against one song with `--debug`, watch a track download succeed:

```bash
python karaoke_automator.py --debug --max-tracks 1
```

- [ ] **Step 8: Commit**

```bash
git add packages/download_management/download_manager.py packages/configuration/selectors.py tests/unit/test_download_cleanup.py
git commit -m "perf: wait for modal element instead of window/page_source polling (saves ~5s/track)"
```

### Task 3.2: Reorder modal close vs readiness detection (read first, close after)

**Why:** Currently `_execute_download_click` calls `_check_and_handle_inline_popups` (which tries to close any visible modal) before `_wait_for_download_readiness` runs (which needs to read text *from inside* the modal). It works only because the readiness text leaks into `page_source` — a lucky accident.

**Files:**
- Modify: `packages/download_management/download_manager.py:516-649` (`_wait_for_download_readiness`) and `:1019-1077` (`_check_and_handle_inline_popups`)

- [ ] **Step 1: Write the test**

Add to `tests/unit/test_download_cleanup.py`:

```python
def test_readiness_check_uses_modal_text_not_page_source(mocker):
    """_wait_for_download_readiness must read modal text directly, not page_source."""
    from packages.download_management.download_manager import DownloadManager
    from selenium.webdriver.common.by import By

    dm = mocker.Mock(spec=DownloadManager)
    dm.driver = mocker.Mock()
    dm.driver.window_handles = ['main']

    fake_modal = mocker.Mock()
    fake_modal.is_displayed.return_value = True
    fake_modal.text = "Your download will begin in a moment. You can also click on the link below to manually begin your download:"

    dm.driver.find_elements = mocker.Mock(return_value=[fake_modal])
    dm._wait_for_check_interval = mocker.Mock()

    result = DownloadManager._wait_for_download_readiness(dm, "Bass", max_wait=10)

    assert result is True
    assert dm.driver.page_source.lower.call_count == 0, "page_source must not be read"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_download_cleanup.py::test_readiness_check_uses_modal_text_not_page_source -v
```

Expected: FAIL.

- [ ] **Step 3: Rewrite `_wait_for_download_readiness` to use modal element text only**

In `packages/download_management/download_manager.py`, replace `_wait_for_download_readiness` (lines 516–649) with:

```python
    @profile_timing("_wait_for_download_readiness", "download_management", "method")
    def _wait_for_download_readiness(self, track_name, max_wait=60):
        """Wait for the readiness text to appear inside the download modal.

        Reads modal element text only — does NOT read page_source. The earlier
        version polled the entire DOM serialization on every tick across all
        windows; this version queries the modal directly via centralized selectors.
        """
        from ..configuration.selectors import DOWNLOAD_MODAL_COMBINED_SELECTOR

        primary_pattern = "you can also click on the link below to manually begin your download:"
        fallback_patterns = (
            "your download will begin in a moment",
            "download will begin",
            "download is ready",
            "click here to download",
            "download starting",
        )

        def readiness_visible(_driver):
            try:
                modals = _driver.find_elements(By.CSS_SELECTOR, DOWNLOAD_MODAL_COMBINED_SELECTOR)
                for modal in modals:
                    if not modal.is_displayed():
                        continue
                    text = (modal.text or "").lower()
                    if primary_pattern in text:
                        return "primary"
                    for pat in fallback_patterns:
                        if pat in text:
                            return pat
            except Exception:
                pass
            return False

        try:
            matched = WebDriverWait(self.driver, max_wait, poll_frequency=0.5).until(readiness_visible)
            logging.info(f"🎉 Download readiness ({matched}) detected for {track_name}")
            return True
        except TimeoutException:
            logging.warning(f"⚠️ Download readiness not detected within {max_wait}s for {track_name}")
            return False
```

- [ ] **Step 4: Move modal close to AFTER readiness detection**

In `_monitor_download_progress`, after `download_ready = self._wait_for_download_readiness(...)`, add a modal-close step:

```python
        download_ready = self._wait_for_download_readiness(context['track_name'])
        if download_ready:
            logging.info(f"✅ Download ready signal detected for {context['track_name']}")
            # Now (and only now) close the modal — we already read what we needed.
            self._check_and_handle_inline_popups()
        else:
            ...
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_download_cleanup.py::test_readiness_check_uses_modal_text_not_page_source -v
python tests/run_tests.py
```

- [ ] **Step 6: Manual end-to-end validation**

```bash
python karaoke_automator.py --debug --max-tracks 2
```

Watch the log: confirm "Download readiness (primary) detected" appears before any modal-close log lines.

- [ ] **Step 7: Commit**

```bash
git add packages/download_management/download_manager.py tests/unit/test_download_cleanup.py
git commit -m "perf: read modal text before closing modal; drop page_source polling (saves ~2s/track)"
```

---

## Phase 4: Collapse the redundant solo-state verification into one source of truth

`solo_track` already polls until the button is active. Everything that runs after is a re-check of the same DOM state, looking for an event that cannot have happened (the button silently un-activating). This phase collapses 6+ redundant checks down to 1.

### Task 4.1: Delete `_validate_audio_mix_state` (Phase 3 validation)

**Why:** It calls `_is_expected_solo_active`, which checks the same `class_tokens & ACTIVE_SOLO_CLASS_TOKENS` predicate that `_wait_for_solo_activation` already polled to True.

**Files:**
- Modify: `packages/track_management/track_manager.py:447-497` (`_finalize_solo_activation`) and `:627-675`

- [ ] **Step 1: Write the test**

Add to `tests/unit/test_solo_button_detection.py`:

```python
def test_finalize_solo_activation_does_not_call_phase3_validation(mocker):
    """_finalize_solo_activation should not call _validate_audio_mix_state anymore."""
    from packages.track_management.track_manager import TrackManager

    tm = mocker.Mock(spec=TrackManager)
    tm._wait_for_audio_server_sync = mocker.Mock(return_value=True)
    tm._verify_mixer_state_configuration = mocker.Mock(return_value=True)
    tm._validate_audio_mix_state = mocker.Mock(return_value={'audio_mix_validated': True})

    TrackManager._finalize_solo_activation(tm, "Bass", 3)

    tm._validate_audio_mix_state.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_solo_button_detection.py::test_finalize_solo_activation_does_not_call_phase3_validation -v
```

Expected: FAIL.

- [ ] **Step 3: Delete `_validate_audio_mix_state` and `_is_expected_solo_active`**

In `packages/track_management/track_manager.py`, delete the entire method bodies for `_validate_audio_mix_state` (lines 627–648) and `_is_expected_solo_active` (lines 650–675).

Then in `_finalize_solo_activation` (lines 447–497), remove the Phase 3 block (lines 458–474) — everything from `# Phase 3: Enhanced audio mix validation (optional)` down to `# Don't fail the entire process if Phase 3 has issues`. Also remove the `phase3_validation_passed` variable from the final assessment block; the final log becomes simply:

```python
        if overall_success:
            logging.info(f"✅ Audio server sync verification successful for {track_name}")
        else:
            logging.warning(f"⚠️ Audio server sync verification had issues for {track_name} - using fallback timing")

        return True
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_solo_button_detection.py -v
python tests/run_tests.py
```

- [ ] **Step 5: Commit**

```bash
git add packages/track_management/track_manager.py tests/unit/test_solo_button_detection.py
git commit -m "perf: drop redundant Phase 3 audio mix validation (already verified by polling)"
```

### Task 4.2: Delete `_verify_mixer_state_configuration`

**Why:** Method 1 (looking for `mixer.getState()`) is fictional — the global `mixer` object exposes `mixer.getMix()`, not `mixer.getState()`. Method 2 (`.mixer, .audio-mixer` selectors) doesn't match anything on this site. Method 3 uses hardcoded class names that *miss* `track__solo--active` from the canonical `ACTIVE_SOLO_CLASS_TOKENS` and is fully redundant with `_wait_for_audio_server_sync`.

**Files:**
- Modify: `packages/track_management/track_manager.py:447-497` and `:555-625`

- [ ] **Step 1: Write the test**

Add to `tests/unit/test_solo_button_detection.py`:

```python
def test_finalize_solo_activation_does_not_call_mixer_state_check(mocker):
    from packages.track_management.track_manager import TrackManager

    tm = mocker.Mock(spec=TrackManager)
    tm._wait_for_audio_server_sync = mocker.Mock(return_value=True)
    tm._verify_mixer_state_configuration = mocker.Mock(return_value=True)

    TrackManager._finalize_solo_activation(tm, "Bass", 3)

    tm._verify_mixer_state_configuration.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_solo_button_detection.py::test_finalize_solo_activation_does_not_call_mixer_state_check -v
```

Expected: FAIL.

- [ ] **Step 3: Delete `_verify_mixer_state_configuration` (lines 555–625) and remove its call site in `_finalize_solo_activation`**

After this task `_finalize_solo_activation` simplifies to:

```python
    @profile_timing("_finalize_solo_activation", "track_management", "method")
    def _finalize_solo_activation(self, track_name, track_index=None):
        """Wait for audio server sync via DOM polling; brief safety buffer if needed."""
        logging.info(f"⏳ Waiting for audio server to process solo state for {track_name}...")

        audio_server_ready = (
            self._wait_for_audio_server_sync(track_index)
            if track_index is not None
            else False
        )

        if audio_server_ready:
            time.sleep(0.2)  # Tiny safety buffer after deterministic detection
            logging.info(f"✅ Audio server sync verified for {track_name}")
        else:
            time.sleep(1.0)  # Fallback safety buffer when DOM detection didn't conclude
            logging.warning(f"⚠️ Audio server sync inconclusive for {track_name} — using fallback")

        return True
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_solo_button_detection.py -v
python tests/run_tests.py
```

- [ ] **Step 5: Commit**

```bash
git add packages/track_management/track_manager.py tests/unit/test_solo_button_detection.py
git commit -m "perf: drop _verify_mixer_state_configuration (broken on this site, redundant)"
```

### Task 4.3: Drop `page_source` debug read in `_verify_track_selection_state`

**Why:** Lines 1248–1263 of `download_manager.py` serialize the entire DOM via `page_source.lower()` purely to log a debug line that nothing branches on. Pure waste.

**Files:**
- Modify: `packages/download_management/download_manager.py:1248-1263`

- [ ] **Step 1: Delete the dead debug block**

In `_verify_track_selection_state`, delete the entire `try`/`except` block that contains `page_text = self.driver.page_source.lower()` and the `isolation_indicators` check (lines 1248–1263).

- [ ] **Step 2: Run tests**

```bash
python tests/run_tests.py
```

- [ ] **Step 3: Commit**

```bash
git add packages/download_management/download_manager.py
git commit -m "chore: remove dead page_source debug read in track verification"
```

---

## Phase 5: Fix the silently-broken `ensure_only_track_active`

### Task 5.1: Fix the type-comparison bug — or delete the function

**Decision required:** This function is currently broken (the `i == target_index` comparison is `int == str` and never matches, so the target-button activation path is dead code; the function returns `False` after logging a warning every track). The system happens to work because `solo_track` does the activation right after.

Two viable paths:

**A. Fix it and remove the redundant click in `solo_track`** (more invasive, bigger payoff)

**B. Delete `ensure_only_track_active` entirely; let `clear_all_solos` (or selective deactivation) handle the "clear conflicting solos" part separately** (simpler, smaller payoff)

This plan picks **A** because it removes a duplicate click+poll cycle that costs the most on the first track of every song (~5s on the first track in the observed log).

**Files:**
- Modify: `packages/track_management/track_manager.py:726-825` (`ensure_only_track_active`)
- Modify: `packages/track_management/track_manager.py:197-227` (`solo_track`)
- Modify: `karaoke_automator.py:288-292` (call sequence)
- Test: `tests/unit/test_solo_button_detection.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_solo_button_detection.py`:

```python
def test_ensure_only_track_active_finds_target_with_string_index(mocker):
    """data-index comes from the DOM as a string. ensure_only_track_active must
    handle string indices correctly (the prior int == str comparison silently failed)."""
    from packages.track_management.track_manager import TrackManager

    tm = mocker.Mock(spec=TrackManager)
    tm.driver = mocker.Mock()
    tm.driver.current_url = 'https://song-url'

    btn0 = mocker.Mock()
    btn3 = mocker.Mock()
    btn3.click = mocker.Mock()
    tm.driver.find_elements = mocker.Mock(return_value=[btn0, mocker.Mock(), mocker.Mock(), btn3])
    tm._is_solo_button_active = mocker.Mock(return_value=False)

    # WebDriverWait stub
    mocker.patch('packages.track_management.track_manager.WebDriverWait')

    result = TrackManager.ensure_only_track_active(tm, "3", "https://song-url")

    assert result is True
    btn3.click.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_solo_button_detection.py::test_ensure_only_track_active_finds_target_with_string_index -v
```

Expected: FAIL — current code never matches the target button.

- [ ] **Step 3: Fix the type comparison**

In `packages/track_management/track_manager.py:756-768`, change:

```python
            for i, button in enumerate(solo_buttons):
                try:
                    if self._is_solo_button_active(button):
                        active_tracks.append(i)
                        logging.debug(f"Found active track: {i}")

                    # Remember target button for later activation
                    if i == target_index:
                        target_button = button
```

to:

```python
            target_index_int = int(target_index) if isinstance(target_index, str) else target_index
            for i, button in enumerate(solo_buttons):
                try:
                    if self._is_solo_button_active(button):
                        active_tracks.append(i)
                        logging.debug(f"Found active track: {i}")

                    if i == target_index_int:
                        target_button = button
```

And in line 802 change:

```python
            if target_index not in active_tracks:
```

to:

```python
            if target_index_int not in active_tracks:
```

- [ ] **Step 4: Remove the redundant activation in `solo_track`**

`solo_track`'s job becomes "verify the target solo is active; if not, click it." It no longer assumes it has to click unconditionally.

In `packages/track_management/track_manager.py:198-227`, replace `solo_track` with:

```python
    @profile_timing("solo_track", "track_management", "method")
    def solo_track(self, track_info, song_url):
        """Ensure the target track is solo'd. Assumes ensure_only_track_active was just called."""
        track_name = track_info['name']
        track_index = track_info['index']

        logging.info(f"Soloing track {track_index}: {track_name}")

        if self.progress_tracker:
            self.progress_tracker.update_track_status(track_index, 'isolating')

        try:
            self._navigate_to_song_if_needed(song_url)
            track_element = self._find_track_element(track_index)
            if not track_element:
                return False

            solo_button = self._find_solo_button(track_element, track_index)
            if not solo_button:
                return False

            # Fast path: ensure_only_track_active should have already activated.
            # Only click if the button isn't active.
            if not self._is_solo_button_active(solo_button):
                safe_click(self.driver, solo_button, f"solo button for {track_name}")

            return self._activate_solo_button_verify_only(solo_button, track_name, track_index)

        except (InvalidSessionIdException, NoSuchWindowException):
            raise
        except Exception as e:
            logging.error(f"Error soloing track {track_name}: {e}")
            return False
```

And rename `_activate_solo_button` (line 287) to `_activate_solo_button_verify_only` and drop the up-front click — keep only the polling and finalization:

```python
    @profile_timing("_activate_solo_button_verify_only", "track_management", "method")
    def _activate_solo_button_verify_only(self, solo_button, track_name, track_index):
        """Wait for solo activation (button has either been clicked by us or by ensure_only_track_active)."""
        if self._wait_for_solo_activation(solo_button, track_name):
            return self._finalize_solo_activation(track_name, track_index)
        return self._retry_solo_activation(solo_button, track_name, track_index)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_solo_button_detection.py -v
python tests/run_tests.py
```

- [ ] **Step 6: End-to-end smoke test**

```bash
python karaoke_automator.py --profile --max-tracks 3
```

Verify in the log: no more "Could not find target button" warnings. Verify per-track timing is faster (especially the *first* track of the song).

- [ ] **Step 7: Commit**

```bash
git add packages/track_management/track_manager.py tests/unit/test_solo_button_detection.py
git commit -m "fix: ensure_only_track_active type-comparison bug; drop redundant solo click"
```

---

## Phase 6: Housekeeping (no perf impact, but reduces drift risk)

### Task 6.1: Consolidate the three copies of `_is_solo_button_active*`

**Why:** Three near-identical implementations: `track_manager._is_solo_button_active` (line 343), `track_manager._is_solo_button_active_for_index` (line 537), and `download_manager._is_solo_button_active_enhanced` (line 1293). All three share `ACTIVE_SOLO_CLASS_TOKENS` but otherwise duplicate ~30 lines apiece. If we widen the active-class set in one place, the others silently drift.

**Files:**
- Create: `packages/utils/solo_state.py` (new module, focused responsibility)
- Modify: `packages/track_management/track_manager.py`
- Modify: `packages/download_management/download_manager.py`
- Modify: `packages/utils/__init__.py`
- Test: `tests/unit/test_solo_button_detection.py`

- [ ] **Step 1: Write the test for the consolidated module**

Create `tests/unit/test_solo_state.py`:

```python
"""Tests for the consolidated solo-button state detector."""
import pytest


def test_is_active_with_canonical_class():
    from packages.utils.solo_state import is_solo_button_active

    class FakeButton:
        def get_attribute(self, name):
            return {'class': 'track__solo track__solo--active', 'aria-pressed': None, 'data-state': None}.get(name)
    assert is_solo_button_active(FakeButton()) is True


def test_inactive_does_not_match_via_substring():
    """The word 'active' inside 'inactive' must not match. This is the primary
    bug the token-based comparison was introduced to prevent."""
    from packages.utils.solo_state import is_solo_button_active

    class FakeButton:
        def get_attribute(self, name):
            return {'class': 'track__solo track__solo--inactive', 'aria-pressed': None, 'data-state': None}.get(name)
    assert is_solo_button_active(FakeButton()) is False


def test_aria_pressed_true_means_active():
    from packages.utils.solo_state import is_solo_button_active

    class FakeButton:
        def get_attribute(self, name):
            return {'class': 'track__solo', 'aria-pressed': 'true', 'data-state': None}.get(name)
    assert is_solo_button_active(FakeButton()) is True


def test_data_state_active_means_active():
    from packages.utils.solo_state import is_solo_button_active

    class FakeButton:
        def get_attribute(self, name):
            return {'class': 'track__solo', 'aria-pressed': None, 'data-state': 'active'}.get(name)
    assert is_solo_button_active(FakeButton()) is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_solo_state.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Create the consolidated module**

Create `packages/utils/solo_state.py`:

```python
"""Single source of truth for solo-button active-state detection.

Use this from both track_management (during activation) and download_management
(during pre-download verification). If the active class set ever changes, update
ACTIVE_SOLO_CLASS_TOKENS here — exactly once.

Class matching is by exact token (not substring): "active" appears inside
"inactive", and "on" appears inside "button"/"icon", so substring matching
produces false positives on every inactive solo button.
"""
import logging

# Exact CSS class tokens that signal an active solo button.
ACTIVE_SOLO_CLASS_TOKENS = frozenset({
    "is-active",
    "active",
    "selected",
    "track__solo--active",
})


def is_solo_button_active(solo_button) -> bool:
    """Detect active state via class tokens, ARIA, or data-state.

    Returns False on any error (caller handles retries)."""
    try:
        class_tokens = set((solo_button.get_attribute('class') or '').lower().split())
        if class_tokens & ACTIVE_SOLO_CLASS_TOKENS:
            return True

        aria_pressed = solo_button.get_attribute('aria-pressed')
        if aria_pressed == 'true':
            return True

        data_state = (solo_button.get_attribute('data-state') or '').lower()
        if data_state in ('active', 'on', 'selected'):
            return True

        return False
    except Exception as e:
        logging.debug(f"Error in solo button active detection: {e}")
        return False
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_solo_state.py -v
```

Expected: PASS.

- [ ] **Step 5: Add the export**

In `packages/utils/__init__.py`, add:

```python
from .solo_state import ACTIVE_SOLO_CLASS_TOKENS, is_solo_button_active
```

- [ ] **Step 6: Replace `track_manager._is_solo_button_active` with the shared function**

In `packages/track_management/track_manager.py`:

1. Remove the local `ACTIVE_SOLO_CLASS_TOKENS` constant (lines 30–37).
2. Replace the imports near the top to import from utils instead:
   ```python
   from ..utils import safe_click, validation_safe, profile_timing, profile_selenium, is_solo_button_active, ACTIVE_SOLO_CLASS_TOKENS
   ```
3. Delete the entire `_is_solo_button_active` method (lines 343–386).
4. Replace every `self._is_solo_button_active(...)` call with `is_solo_button_active(...)` (single-arg function now).
5. In `_is_solo_button_active_for_index`, simplify to:
   ```python
   def _is_solo_button_active_for_index(self, expected_solo_index):
       try:
           track_selector = f".track[data-index='{expected_solo_index}']"
           track_elements = self.driver.find_elements(By.CSS_SELECTOR, track_selector)
           if not track_elements:
               return False
           solo_button = track_elements[0].find_element(By.CSS_SELECTOR, "button.track__solo")
           return is_solo_button_active(solo_button)
       except Exception:
           return False
   ```

- [ ] **Step 7: Replace `download_manager._is_solo_button_active_enhanced`**

In `packages/download_management/download_manager.py`:

1. Replace the import on line 18 (`from ..track_management.track_manager import ACTIVE_SOLO_CLASS_TOKENS`) with:
   ```python
   from ..utils import is_solo_button_active, ACTIVE_SOLO_CLASS_TOKENS
   ```
2. Delete `_is_solo_button_active_enhanced` (lines 1293–1337).
3. Replace every call to `self._is_solo_button_active_enhanced(button)` with `is_solo_button_active(button)`.

- [ ] **Step 8: Run all tests**

```bash
python tests/run_tests.py
```

- [ ] **Step 9: Commit**

```bash
git add packages/utils/solo_state.py packages/utils/__init__.py packages/track_management/track_manager.py packages/download_management/download_manager.py tests/unit/test_solo_state.py
git commit -m "refactor: consolidate _is_solo_button_active* into packages/utils/solo_state"
```

### Task 6.2: Replace `WebDriverWait(...).until(lambda d: True)` no-ops with explicit comments or removal

**Why:** Three places (`track_manager.py:425`, `:984-997`, `:994-996`) use `WebDriverWait(driver, N).until(lambda d: True)` to "create a delay" — but the lambda returns truthy on first call, so it's actually a no-op (returns immediately, not after N seconds). The comments imply a delay; the code does not produce one. Misleading.

**Files:**
- Modify: `packages/track_management/track_manager.py`

- [ ] **Step 1: Read each occurrence and decide intent**

For each `WebDriverWait(...).until(lambda d: True)` call, determine:
- Is a delay actually needed there? (look at the surrounding context)
- If yes: replace with explicit `time.sleep(N)`.
- If no: delete the line entirely.

Specifically:
- Line 425 (`_perform_aggressive_clicks`): the JS click is fire-and-forget; no delay needed. Delete the try/except.
- Lines 984–989 (between pitch button clicks): a brief pause helps the UI register. Replace with `time.sleep(0.1)`.
- Lines 994–998 (after final pitch click, before reading the value): a longer pause. Replace with `time.sleep(0.5)`.

- [ ] **Step 2: Make the changes per above**

- [ ] **Step 3: Run tests**

```bash
python tests/run_tests.py
```

- [ ] **Step 4: Commit**

```bash
git add packages/track_management/track_manager.py
git commit -m "chore: remove misleading WebDriverWait(...).until(lambda d: True) no-ops"
```

### Task 6.3: Audit `tools/inspection/` directory and `archive/`

**Why:** `tools/inspection/` has 11 ad-hoc scripts (some named `test_*.py` but not in the test suite) that may reference selectors or APIs that no longer exist. `archive/` is described in CLAUDE.md only by absence — it's likely stale code we can remove.

**Files:**
- Inspect: `tools/inspection/` directory
- Inspect: `archive/` directory
- Create: `tools/inspection/README.md` (status doc)

- [ ] **Step 1: Audit each inspection script**

For each `.py` file under `tools/inspection/`, run:

```bash
python <script>.py 2>&1 | tail -20
```

Record in a table: file, last-modified date, runs cleanly (yes/no), still useful (yes/no/unsure).

- [ ] **Step 2: Audit `archive/`**

```bash
ls -la archive/
git log --diff-filter=D -- archive/ | head -20
```

Determine: is anything in `archive/` referenced from current code? If not, this is dead code.

- [ ] **Step 3: Decision time** (ASK USER before deleting)

Before deleting anything, post the audit table to the user and get explicit approval. CLAUDE.md says "Delete old code completely — no deprecation, versioned names, or 'removed code' comments" — but only if we're certain it's dead.

- [ ] **Step 4: After approval — delete or move stale files**

Either delete dead scripts/dirs, or move clearly-useful inspection scripts into a documented `tools/diagnostics/` with a README explaining what each one does.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove stale inspection scripts and archive/ directory"
```

---

## Phase 7: Investigations (write up findings; do not fix yet)

### Task 7.1: INVESTIGATE — why is the song folder being cleared on every track?

**Why this matters:** Empirical evidence from `logs/automation.log` shows the folder being cleared per-track:

```
23:00:19.616 🗑️ Clearing existing song folder (before Bass)
23:00:36.696 🗑️ Clearing existing song folder (before Acoustic Guitar)
23:01:05.515 🗑️ Clearing existing song folder (before Backing Vocals)
```

But the call chain shows `cleanup_existing=False` is passed from `_download_single_track:297` → `download_current_mix(cleanup_existing=False)` → `_setup_file_management(cleanup_existing=False)` → `setup_song_folder(clear_existing=False)` → `if clear_existing:` should be False.

If the folder really is being cleared every track, the previous track's file is being **deleted** before the next track's download. The fact that final files survive suggests either (a) the file is preserved elsewhere (maybe Chrome moves it before our delete?), or (b) my call-chain analysis is missing something. Either way: **investigate before changing.**

- [ ] **Step 1: Add explicit logging to confirm the call path**

Temporarily, in `packages/file_operations/file_manager.py:setup_song_folder`, change:

```python
if clear_existing:
    self.clear_song_folder(song_folder_name)
```

to:

```python
import traceback
logging.warning(f"setup_song_folder(clear_existing={clear_existing}) called. Stack:\n{''.join(traceback.format_stack()[-5:])}")
if clear_existing:
    self.clear_song_folder(song_folder_name)
```

- [ ] **Step 2: Run a 2-track test**

```bash
python karaoke_automator.py --debug --max-tracks 2 2>&1 | grep -A 6 "setup_song_folder"
```

- [ ] **Step 3: Read the stack traces and answer**

Document in `docs/investigations/2026-05-07-song-folder-clearing.md`:

```markdown
# Why is the song folder cleared per track?

## Observed
<paste log lines>

## Stack traces
<paste stacks>

## Conclusion
- [ ] cleanup_existing IS False as expected; clearing comes from a different code path I missed (which one? line: ___)
- [ ] cleanup_existing is somehow True when it reaches setup_song_folder (where does it get re-defaulted? line: ___)
- [ ] A different mechanism is clearing the folder (e.g., Chrome's download path manager). What/where: ___

## Impact
- Files visible after a successful 15-track run: how many?
- Files visible mid-run after track N completes and track N+1 starts: how many?
```

- [ ] **Step 4: Revert the diagnostic logging**

`git checkout packages/file_operations/file_manager.py`

- [ ] **Step 5: Based on findings, file a follow-up plan**

If clearing IS happening unintentionally: write a new plan task to fix it. Saving the per-track `shutil.rmtree` would save another ~50–500ms/track depending on file count and Dropbox sync latency.

If clearing is NOT actually happening (log misread): document the explanation and close.

- [ ] **Step 6: Commit the investigation**

```bash
git add docs/investigations/
git commit -m "docs: investigate per-track song folder clearing"
```

### Task 7.2: INVESTIGATE — the unexplained 2s gap between solo finalize and download_current_mix start

**Why:** The log shows a consistent ~2s gap between `✅ Complete audio server sync verification successful` and `Downloading current mix:` with no log lines in between. None of the `time.sleep(...)` calls in the code account for it.

- [ ] **Step 1: Add timing instrumentation around the gap**

Temporarily, in `karaoke_automator.py:_download_single_track`, wrap the call:

```python
import time as _t
_gap_t0 = _t.perf_counter()
if self.solo_track(track, song['url']):
    _gap_t1 = _t.perf_counter()
    logging.warning(f"GAP: solo_track→download_current_mix call site: {(_gap_t1-_gap_t0)*1000:.0f}ms")
    try:
        success = self.download_manager.download_current_mix(...)
```

And in `solo_track`'s last line before return, log `_t.perf_counter()` as the "solo_track exit time."

And in `download_current_mix`'s first line, log `_t.perf_counter()` as the "download_current_mix entry time."

- [ ] **Step 2: Run and inspect**

```bash
python karaoke_automator.py --debug --max-tracks 3 2>&1 | grep -E "GAP|solo_track exit|download_current_mix entry"
```

- [ ] **Step 3: Likely culprits to check**

The gap is probably one of:
- `ProgressTracker.update_track_status('isolating')` blocking on a screen redraw
- Logging buffer flush (large debug payload causing I/O wait)
- A `time.sleep` I missed
- Selenium implicit wait somewhere

Document findings in `docs/investigations/2026-05-07-mystery-2s-gap.md`.

- [ ] **Step 4: Revert instrumentation, commit findings**

```bash
git checkout karaoke_automator.py
git add docs/investigations/
git commit -m "docs: investigate 2s gap between solo finalize and download start"
```

---

## Phase 8: Optional / advanced (only after Phase 1–7 complete and validated)

These are higher-risk, higher-reward changes. Only attempt after all the safe wins are landed and benchmarked. Each should be its own brainstorm + plan, not crammed into this document.

### Task 8.1: Spike — direct API call to `mixer.getMix()` instead of clicking the button

The download button's onclick is `mixer.getMix();return false;`. If we can call `mixer.getMix()` directly via `driver.execute_script("return mixer.getMix();")` we may skip the modal entirely. Worth a research spike (timeboxed, 1–2 hours):

- What does `mixer.getMix()` return? (Promise? URL?)
- Does it block or return immediately while server work continues?
- Does the auto-download still fire if we suppress the button click?

If yes to all three: this could shave another 5–10s per track. But it's site-specific reverse engineering, and any site change breaks it. **Only attempt after all the safe wins are stable.**

### Task 8.2: Spike — speculative pre-soloing while the previous track downloads

Currently: track N download finishes → ensure_only_track_active(N+1) → solo_track(N+1) → download(N+1). The audio-server-sync wait runs serially.

Spike: while track N is in `wait_for_download_to_start` / `_monitor_download_progress` (idle Selenium time), kick off ensure_only_track_active(N+1) on a worker thread.

Hard parts:
- Selenium drivers are not thread-safe.
- The site may rate-limit concurrent mix-generation requests.
- Race conditions around solo state could corrupt the in-flight download.

**This is risky. Only worth it if Phase 1–7 didn't get us to the target.**

### Task 8.3: Move downloads out of Dropbox-synced folder

The `.env` `DOWNLOAD_FOLDER` currently points into `~/Library/CloudStorage/Dropbox/...`. Each `shutil.rmtree`, file create, and rename triggers Dropbox sync events that may slow filesystem operations and contend with Chrome's download. Spike: download to a local scratch folder (`/tmp/kv-downloads/<song>`), then `rsync` or move to Dropbox at the end of the run.

### Task 8.4: Wire `--profile` into a CI smoke test

Once the optimizations land, prevent regression by running `python karaoke_automator.py --profile --max-tracks 3` against a known-good test song in CI (or as a pre-merge check), parsing the resulting JSON, and failing the build if `mean per-track download_time` regresses by >20% from a stored baseline. This is the same A/B framework that `PerformanceBaselineTester` already implements — surface it.

---

## Other suggestions you may have missed

In addition to the audit findings + housekeeping I called out above, here are four items I noticed while writing this plan that we didn't explicitly cover — flagging them so you can decide whether they're worth a task:

1. **`BETWEEN_TRACKS_PAUSE = 0.5s` may be removable.** The download monitoring already calls `monitor_thread.join()` which blocks until the file is on disk. The 0.5s `time.sleep` after that is belt-and-suspenders. Likely safe to drop but verify no regression — it's a 0.5s/track win × N tracks if it works.

2. **`requirements.txt` doesn't pin `watchdog`.** The fast download-start detection path depends on `watchdog`; if it's not installed, the code silently falls back to 1s polling. Pin it explicitly so the optimized path is the default.

3. **`_does_file_match_track` runs full-string regex/word-set comparison on every poll** during completion monitoring. With 1-2 files in flight, fine. But the function also runs in `validate_audio_content` on every downloaded file. Worth a future review if folder sizes grow.

4. **The `archive/` directory is 8KB+ of code that nothing imports.** Already covered in Task 6.3 but flagging because it may be larger than I estimated — Phase 6's audit will tell.

---

## Self-Review Checklist

Run this before considering the plan ready to execute:

- [ ] Every task has explicit file paths (no "the file" references)
- [ ] Every code change has actual code shown (no "implement X")
- [ ] Every test has a runnable `pytest` command with expected pass/fail
- [ ] Phase ordering: low risk → high risk (yes — Phase 1 is independent quick wins, Phase 8 is research spikes)
- [ ] Each phase ships independently (no Phase 2 task depends on a Phase 4 task)
- [ ] No "TBD", "fix later", "etc." placeholders
- [ ] Each commit message explains the *why*, not the *what*
- [ ] Performance claims have a measurement protocol attached
- [ ] Race-condition territory (`_wait_for_solo_activation`, the polling tokens, track-type timeouts) is preserved verbatim — none of the tasks touch it

---

## Expected outcomes

| Phase | Expected savings per track | Risk |
|---|---|---|
| 1 (Quick wins) | 4–5s | Low |
| 3 (Modal flow) | 5–7s | Medium — needs Phase 2 verification first |
| 4 (Verification collapse) | 0.5–1.5s happy path; 4s+ on retries | Low |
| 5 (`ensure_only_track_active` fix) | 1–5s (more on first track of song) | Medium — touches behavior the system relies on |
| 6 (Housekeeping) | 0s (cleanup) | Very low |
| 7 (Investigations) | unknown until findings | Zero — no code change |
| 8 (Spikes) | potentially 5–15s | High — site-specific reverse-engineering |

If Phases 1, 3, 4, 5 all land cleanly, expect **per-track time to drop from ~22–25s to ~12–15s** (40–50% improvement). A 15-track song that took ~10 minutes should take ~5–6 minutes.
