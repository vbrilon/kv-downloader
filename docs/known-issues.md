# Known Issues

Open, deferred, or "WONTFIX-for-now" issues. Each entry has:

- **Severity** — how much it actually hurts.
- **Source** — where the issue was first written down (postmortem,
  user report, etc.).
- **Fix sketch** — enough detail that a future session can pick it
  up without re-doing the analysis.

Resolved entries should be **deleted**, not marked done — git history
is the audit trail. (Add a final summary to the relevant postmortem
or commit message before deleting.)

---

## Legacy Selenium fallback timeouts unbounded

**Severity:** Low (rare path; only triggers on `capture_session`
failure, which is itself rare). High blast-radius **when** it
triggers — can hang for many minutes per song.

**Source:** `docs/investigations/2026-05-09-direct-api-mapping-precount-cascade.md`
§ "Known gap (not fixed in 2026-05-09 commits)".

**The gap:** When `capture_session` fails for a whole song, the
orchestrator (`karaoke_automator.py _download_all_tracks_direct_api`)
falls through to legacy `_download_single_track` for every track in
that song. The bounded-timeout fix from commit `4ab435b` covered
ONLY the direct-API path. Legacy uses:

- `DOWNLOAD_MAX_WAIT = 90` (seconds, in `packages/configuration/config.py`)
- `_wait_for_download_readiness(max_wait=60)` in `download_manager.py`
- `_monitor_download_completion` polls until `DOWNLOAD_MAX_WAIT` elapses
- `_retry_song_failures` and `_retry_all_failures` add another two
  rounds on top

Worst case: N tracks × ~90s × 3 retry tiers = many minutes per song.

**Fix sketch:**

1. Drop `DOWNLOAD_MAX_WAIT` from 90 → 30 in
   `packages/configuration/config.py` (matches stated user budget of
   ~30s per track).
2. Drop `_wait_for_download_readiness` default from 60 → 25 in
   `download_manager.py`.
3. Add cascade-abort to legacy whole-song fallback in
   `_download_all_tracks_direct_api` (the `except CaptureError:`
   branch) — mirror the direct-API logic: track consecutive failures,
   abort the song after 2.
4. Consider removing `_retry_all_failures` (Tier 2 retry) entirely
   for direct-API failures, since the same server-state issue affects
   both paths.

**Why deferred:** capture rarely fails in practice. Documented because
when it DOES fail, the user experience is bad (silent multi-minute
hang). Pick this up the next time someone hits a slow run.
