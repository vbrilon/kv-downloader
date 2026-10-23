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

## Legacy flow: pipeline track N's file delivery with track N+1's solo

**Severity:** Low. An optimization for the **legacy Selenium flow only**,
which is now the fallback (direct-API is the default path), so it may no
longer be worth doing. Estimated ~2 s/track, ~30 s on a 15-track song.

**Source:** moved from root `PLAN.md` (2026-05-08) on 2026-10-23; full
write-up in git history (`git show 5d9a537:PLAN.md`).

**Idea:** once the download modal opens, mix N is already a static file on
the CDN, so `solo(N+1)` can start while file N is still arriving.

**Fix sketch:** in `download_manager._wait_for_download_readiness()`, emit a
"ready" signal when the readiness text appears; the orchestrator monitors
file delivery on a background thread and starts `solo(N+1)` in the
foreground. If download N fails after modal-open, retry the captured URL's
GET directly rather than redoing the UI flow (the mixer has moved on).

---

## Slow direct-API MP3 transfers (5–8 min)

**Severity:** Low–Medium. Costs time, not data: on 2026-10-13 three of
~65 tracks took 317 s, 481 s and 353 s, with no retries and complete,
label-verified files.

**Source:** `docs/investigations/2026-10-13-legacy-download-external-volume.md`
§ "Also found".

**What we know:** the render wait is capped at 25 s and no retries or 503s
were logged, so the time was most likely the CDN transfer — `_fetch_mp3`'s
`timeout=180` is per-read, so a slow trickle never trips it. Not proven:
step timing (`basket/render/transfer` on each `✅ direct-API` line) was only
added afterwards (PR #5).

**Fix sketch:** once a slow line confirms `transfer` dominates, add a total
deadline (e.g. 60 s) to the streaming loop in `_fetch_mp3` that raises
`MP3FetchError` so `_fetch_mp3_with_retry` reconnects. While there, compare
the bytes written to the response's `Content-Length` — nothing checks for a
short read today.

---

## Legacy Selenium fallback timeouts unbounded

**Severity:** Medium (raised 2026-10-13). The legacy path used to be
rare (only on `capture_session` failure), but the automator now
switches the **rest of a run** to it whenever Fastly blocks the
direct-API path (see `docs/site-flow/2026-10-13-fastly-bot-challenge.md`),
which happens once the ~1 h clearance expires. High blast-radius when
it triggers — can hang for many minutes per song.

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
