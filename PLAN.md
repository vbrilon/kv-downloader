# Investigation Plan: Click Track Solo Activation Timeout

**Goal:** Determine whether `SOLO_ACTIVATION_DELAY_CLICK = 12.0s` is still needed on the redesigned karaoke-version.com mixer, or whether it's now over-conservative and can be lowered safely.

**Why now:** The Click track is consistently the slowest in every run (~29–30s vs ~16–18s for non-Click tracks). The 12s click-specific solo activation timeout is responsible for ~10s of that delta. The site has been redesigned since this constant was set (mixer DOM moved from `.track` to `.custom__mixer-track-line`, download button from `a.download` to `a.custom__song-download`), so the original assumption that click tracks need extra time may no longer hold.

---

## Background — what we know about the current 12s constant

- Defined in `packages/configuration/config.py`:
  ```python
  SOLO_ACTIVATION_DELAY_CLICK = 12.0   # extended timeout due to server processing differences
  SOLO_ACTIVATION_DELAY_SPECIAL = 10.0  # bass/drums tracks
  SOLO_ACTIVATION_DELAY_SIMPLE = 7.0   # ≤8 tracks
  SOLO_ACTIVATION_DELAY_COMPLEX = 10.0  # 9+ tracks
  ```
- Track-type classification lives in `packages/track_management/track_manager.py:_detect_track_type` — keys `click`, `metronome`, `count` route to the click bucket.
- Used in `_wait_for_solo_activation` and `_get_track_type_timeout`.
- Per CLAUDE.md, the 12s value was set in response to "click track isolation failures" — there's a real prior incident behind it. **Don't lower without empirical evidence on the current site.**

## Empirical observation (from the 2026-05-08 final run)

Looking at `logs/automation.log` for the most recent successful 15-track run:

```
02:23:30  Soloing track 0: Intro count Click
02:23:30  Polling for solo activation for Intro count Click (type: click, timeout: 12.0s)
02:23:42  ⚠️ Solo button not active after 12.0s for Intro count Click (type: click)
02:23:42  🔄 Final retry attempt for Intro count Click
02:23:42  ✅ Solo button active after aggressive retry for Intro count Click  (33ms after retry kicked in)
```

The Click track timed out the full 12s on the *initial* polling, then succeeded almost instantly via the retry path's JS-click hammer. **This is the smoking gun:** the initial click via Selenium isn't registering on the page, but a JS-click does. The 12s is being burned waiting for an event that wasn't going to happen — not for genuine server processing time.

## Hypothesis

The 12s constant was set to mask a **click-event-not-firing problem**, not a server-side timing problem. On the redesigned site, the `.track__solo` button for the Click track may have an overlay, modified event handler, or different click target that prevents the standard Selenium click from registering — so we wait the full 12s, then `_perform_aggressive_clicks` (JS click) succeeds in <100ms.

If this is true, fixing the click — not the timeout — is the right answer. The expected outcome: drop the 12s timeout entirely (or align it with `SOLO_ACTIVATION_DELAY_SPECIAL = 10.0`), and the Click track lands at ~17–20s like every other track.

---

## Investigation steps

### 1. Confirm the smoking gun on a fresh run

Add a single-line warning to `_perform_aggressive_clicks` so we can see whether the JS-click *always* succeeds on the Click track (proving the native click was the only problem) or only sometimes (which would mean there's also a real server-side delay).

```python
# packages/track_management/track_manager.py — temporary instrumentation
def _perform_aggressive_clicks(self, solo_button):
    for i in range(SOLO_BUTTON_MAX_RETRIES):
        self.driver.execute_script("arguments[0].click();", solo_button)
        ...
        # ADD THIS:
        time.sleep(0.05)  # let DOM settle
        if is_solo_button_active(solo_button):
            logging.info(f"DIAG_CLICK: aggressive JS click succeeded after attempt {i+1} (~50ms)")
            return
```

Then run `python karaoke_automator.py --debug` against a song with a Click track. Read `logs/debug.log` for the timing of the JS click vs. the native click.

**Pass criterion to proceed:** JS click succeeds within ~100ms of being fired in 3 consecutive runs.

### 2. Inspect the Click track's solo button on the live site

Use Chrome DevTools MCP (or the user's regular browser) to:

a. Load the song page logged in.
b. Inspect the Click track's `.track__solo` (or `.custom__mixer-track-...` equivalent) button:
   - Is there an overlay on top of it? (e.g., a tooltip, a label, or another sibling `<a>` that captures the click)
   - Is the click handler attached to a different element than what `button.track__solo` matches?
   - Is the button outside the viewport when the page first loads? (We saw off-screen issues earlier.)

c. Try clicking it manually and confirm the solo activates within ~1s.

d. Try `document.querySelector('.track[data-index="0"] button.track__solo').click()` from the console. Confirm it activates.

This tells us *why* the native Selenium click is failing on the Click row specifically when it works fine on other rows.

### 3. Decide on the fix based on findings

**If JS click always succeeds + native click is being intercepted by something on the Click row:**
- The fix is to use `js_click_with_scroll` for the *initial* solo click (not just the retry). Same pattern we used for the download button (Phase 1.1) and for `ensure_only_track_active` (post-merge fix `ebefab8`).
- Drop `SOLO_ACTIVATION_DELAY_CLICK` entirely; let the click track use the standard `_get_adaptive_timeout` like other tracks.
- Expected savings: ~10s on the Click track per song.

**If JS click is also slow sometimes (i.e. the server actually does take longer for click tracks):**
- Keep the 12s timeout but document *which* failure mode it's protecting against.
- Consider tightening to 8s if the worst observed case is well under 12s.

**If the click button is genuinely off-screen or covered by an overlay on initial page load:**
- Fix the underlying scroll/visibility issue.
- Same `js_click_with_scroll` change probably resolves it (it scrolls into view first).

### 4. Validate

Run `python karaoke_automator.py --profile` over a clean 15-track song. The Click track should land in the same 16–20s band as other tracks. Compare to the 29.7s baseline from `docs/baselines/2026-05-08-after-phase3-stats.json` (or wherever the latest after-fixes stats live).

If it drops by >5s without any new "Solo button not active after Xs" warnings across 3 consecutive runs, ship.

---

## Risk / what NOT to do

- **Don't lower `SOLO_ACTIVATION_DELAY_CLICK` without instrumentation evidence.** The 12s was set in response to a real incident. Empirical proof first.
- **Don't widen `ACTIVE_SOLO_CLASS_TOKENS`** to "fix" a timeout — those tokens were locked down for substring-bug reasons (see `packages/utils/solo_state.py`).
- **Don't remove the retry path** in `_retry_solo_activation` even if you find the root cause. Keep it as a safety net for genuine click-failure cases on other tracks.

---

## Estimated effort

- Instrumentation + first run: 30 min
- Live-site inspection: 30 min
- Implementation (if `js_click_with_scroll` fix applies): 30 min + tests
- Validation runs: ~1 hour wall-time but mostly idle

Total: ~2 hours focused work, mostly waiting on Selenium runs.
