# Plan: Tier 2 — Parallel Downloads via Multi-Tab Pipelining

> **STATUS (2026-05-08): CANCELLED — server architecture makes single-account parallelism infeasible.**
> See [Postmortem](#postmortem-2026-05-08) below before re-attempting.

## Postmortem (2026-05-08)

Phase 0 was executed using probe scripts in `tools/`:

- `probe_concurrent_tabs.py` — multi-tab in a single Chrome (Approach A)
- `probe_concurrent_processes.py` — multiple Chrome processes (Approach B)
- `probe_direct_fetch.py` — multi-tab + direct URL fetch via `requests`
- `probe_network_capture.py` — full HTTP/CDP capture during one download
- `probe_direct_api.py` — direct API calls to `basket.php`/`begin_download.html`
- `diag_solo_only.py` — production-path solo verifier
- `diag_basket_http.py` — header/cookie diagnostic for basket.php replay

### Bottom line

Single-account parallel downloads are structurally infeasible — but the
investigation surfaced a **direct-API workflow that's ~37% faster sequentially
than the current Selenium flow**. See `PLAN.md` ("Direct-API rewrite") for the
follow-up.

### Mechanism (precise)

The download flow is two HTTP calls:

1. `GET /basket.php?…&trackslevels=…&pannings=…&prodid=PRODID` — updates the
   server-side basket for `PRODID` (account+song) AND triggers async mix-gen.
   Returns 200 + empty body in <1s.
2. `GET /my/begin_download.html?id=PRODID` — returns the modal HTML containing
   the `c*.recis.io` MP3 URL. Polled in a loop; the URL hash changes once the
   new mix is ready (~7–14s after basket.php).

`prodid` is constant per account+song — it's the user's "product" entry baked
into the page template, not regenerated per request. The site's mixer JS
(`f988d05cfcaaccd3056572849b57d779.js`) only ever calls `/basket.php`; there's
no alternate `bkac` value, no separate `createf` endpoint, no way to spawn
parallel mixer slots from the same account.

### Why parallelism fails (verified via `probe_direct_api.py` race test)

When `basket.php(B)` arrives during an in-flight mix-gen for `basket.php(A)`,
the server **cancels A and runs only B**. Race test fired both baskets
within 0.3s, then polled `begin_download.html` for 60s. Only ONE new hash
appeared, and its filename encoded basket B's solo selection (`(Bass_…)`).
A's mix never appeared — it was cancelled.

### Why both Approach A (multi-tab) and Approach B (multi-process) fail

Both approaches authenticate as the same account → same `prodid` →
basket-cancel semantics apply equally. A second Chrome instance does not
give us a second mixer slot.

### What the original investigation got partially wrong

The earlier multi-tab probe blamed "server tracks mixer state per-account,
last-write-wins" — close, but imprecise. The actual mechanism is per-prodid
basket cancellation triggered by basket.php overwrites. Same end result.

### Workarounds considered, not pursued

1. **Multiple Karaoke-Version accounts** — one parallel lane per account.
   Likely violates ToS, multiplies licensing cost, adds operational
   complexity. Not recommended.
2. **Direct-API rewrite (sequential, no parallelism)** — promoted to PLAN.md
   as the highest-value remaining optimization. ~37% faster per track even
   without parallelism, by eliminating Selenium's solo-click + audio-sync +
   modal-handling + Chrome-download-manager overhead.
3. **Pipelining next-track basket with current-track file fetch** — also
   in PLAN.md. Stacks with direct-API for ~50–60% combined reduction.

### Recommendation

Single-account parallelism is dead. Pursue the direct-API rewrite (PLAN.md)
plus pipelining for ~50–60% reduction on a 15-track song without any
multi-account complexity. Re-run the probes only if the site changes its API
shape.

---

## Original plan (preserved for context)

**Goal:** Cut total session time for a 15-track song from ~5 minutes to ~2 minutes (50–60% reduction) by running multiple track downloads concurrently instead of strictly sequentially.

**Why now:** Tier 1 hit the per-track wall-time floor — 14s of every track is server-side audio mix generation that we cannot speed up. The only remaining win is to **overlap that server compute** by running N tracks at once.

---

## The opportunity

Today, per-track timing decomposes (post-Tier-1) as:

```
solo + click + monitor   ~3s   client-side, blockable
server mix generation   ~11s   server compute, NOT blockable on client
file delivery + write    ~2s   network + disk
                       ─────
                       ~16s
```

Sequential 15 tracks → 15 × 16s ≈ 4 minutes wall-time. The server compute is **15 × 11s = 2 min 45s** of pure waiting.

If we could keep N=4 server-compute requests in flight concurrently, the 2:45 server-bound block compresses to ~45s, dropping the total to ~1:30 + setup overhead ≈ **2 min wall-time**.

**Catch:** Karaoke-Version.com is a multi-tenant site. We don't know the per-account concurrency limit. Pushing too hard risks rate-limiting or, worse, account flagging. Conservative N (3–4) with monitoring is the right starting point.

---

## High-level architecture

Two viable approaches; recommend **Approach B**.

### Approach A: Multi-tab single Chrome instance

Open N tabs in the same Chrome process; each tab independently solo-and-downloads a track. One `KaraokeVersionAutomator` orchestrates a queue.

- ✅ Single login, single Chrome
- ✅ All cookies/session shared
- ❌ Each tab needs an isolated download path (Chrome's download directory is per-process, not per-tab — would need DevTools `Page.setDownloadBehavior` per-tab, hairy)
- ❌ Modal interactions: each track's "ready to download" modal pops up in a different tab. Selenium `switch_to.window` is finicky under load.
- ❌ Workers can race on shared mixer state if the site uses any global JS singleton

### Approach B: Multiple Chrome processes, coordinated download paths *(recommended)*

Spin up N Chrome instances (`headless=True` each), each with its own profile + download path + own `KaraokeVersionAutomator`. A coordinator script feeds tracks from a shared queue into worker processes.

- ✅ Full isolation per worker — no shared-state races
- ✅ Each worker downloads to its own subfolder; coordinator merges into the song folder at the end (or per-track as files appear)
- ✅ Each worker is just our existing per-track logic, unchanged
- ✅ Clean retry semantics — if worker N hangs, kill its Chrome and reassign track
- ❌ N× memory overhead (~250MB per Chrome × 4 = 1GB)
- ❌ N× login cost on first run (one-time, ~1s per worker)
- ❌ Requires careful coordination (queue, file move, dedup)

The cost is real but the architecture is clean. **Recommend B.**

---

## Phasing

### Phase 0: Probe the concurrency limit (~1 hour, no code change)

Before architecting anything, confirm the site allows concurrent downloads on one account. Open 2 Chrome windows manually, log in, both go to the same song page. Solo Track 0 in one window, Track 1 in the other. Click download in both within ~1 second. Watch:

- Do BOTH downloads start, or does one fail?
- Is there a "previous download still processing" lockout?
- Does the modal in window 1 get hijacked by window 2's click?
- Does the account get a captcha challenge?

**Pass criterion:** both downloads complete. Iterate up to N=4. If concurrency fails at any N, that becomes the system limit.

If concurrency is hard-blocked at N=1 (single download per account), Tier 2 is infeasible and we stop here.

### Phase 1: Coordinator scaffold (~3 hours)

New module: `packages/coordinator/parallel_downloader.py`. Responsibilities:

- Owns the "track queue" (list of `{song_url, track_index, track_name, song_folder, key_adjustment}`)
- Spawns N worker processes. Each worker runs an existing `KaraokeVersionAutomator` instance configured with:
  - Its own `chrome_profile/` subdirectory (e.g. `chrome_profile/worker-1/`)
  - Its own download path (e.g. `{song_folder}/.workers/worker-1/`)
- Workers pull from queue (multiprocessing.Queue or simple file lock); when a worker finishes a track, it grabs the next one
- Coordinator is responsible for **moving** completed files from `worker-N/` to the song folder root and resolving naming conflicts (shouldn't happen since track names are unique)

Start with N=2. Don't ramp up until N=2 is rock-solid for 5 consecutive runs.

**Test plan for Phase 1:**

- Unit: queue distribution logic, file-merge logic, worker-PID cleanup on shutdown
- Integration: N=1 (degenerate case — should match current sequential behavior)
- Live: N=2 against a 4-track song, then 15-track. Must match all current acceptance criteria (no warnings, no retries, all tracks complete, files in correct folder).

### Phase 2: Failure modes and back-pressure (~2 hours)

The hard part is what happens when things go wrong:

- **Worker hangs on solo activation** (>30s) → coordinator kills that Chrome process, returns the track to the queue, marks worker dead. Spawn replacement.
- **Worker hits a captcha** (account flagged) → ALL workers should pause, surface a one-time prompt, and reduce N to 1 for the rest of the session.
- **Site returns "previous download still processing"** → back off; reduce N by 1 until errors stop.
- **Disk full / Dropbox sync slow** → coordinator should serialize file moves (not parallel) so we don't fight the file system.
- **Coordinator crash mid-song** → workers are children, should exit cleanly. Their downloaded files are valid (already in `worker-N/`), can be merged on the next run.

Each of these needs a test. The captcha case is the scariest and probably requires a manual test against a flagged-but-not-locked test account.

### Phase 3: Tuning + observability (~2 hours)

- Add per-worker telemetry to the perf log: `worker_id` field on each timing event, so we can see which worker is slowest
- Adaptive N: start at N=4, drop to N=3 if one worker shows latency >2× the others (server load-balancing pushing some workers into a slow pool), drop to N=2 on any retry, drop to N=1 on any captcha
- Honor an `--workers` CLI flag (default 4, max 6, min 1)
- On error: log the full state (which worker, which track, which error) and continue with one less worker

### Phase 4: Documentation + ship (~1 hour)

- Update `CLAUDE.md` with the new architecture
- Update `README.md` with the `--workers N` flag
- Capture validation results: full 15-track run timings at N=1, 2, 3, 4 in `docs/baselines/`

**Total estimated effort: ~9 hours focused work + iterative validation runs.**

---

## Specific risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Site detects concurrent downloads as abuse, flags account | Medium | High (user account temporarily limited or banned) | Phase 0 probe + N≤4 hard cap + back-off-on-error |
| Per-account download rate limit silently throttles | Medium | Medium (slower than sequential, defeats purpose) | Phase 0 measurement; if observed, reduce N |
| Worker Chrome processes leak on coordinator crash | Low | Low (memory only; kill -9 cleans up) | psutil-based child-process cleanup on coordinator shutdown |
| Two workers solo conflicting tracks on same page | N/A | N/A | Approach B isolates each worker — non-issue |
| Modal close events from worker A affect worker B | N/A | N/A | Approach B isolates each Chrome — non-issue |
| Race on file-move from `worker-N/` to song folder | Medium | Medium (file collision or partial move) | Single-coordinator file-move queue, atomic rename |
| Dropbox sync fights N× concurrent file writes | Medium | Low–medium (slow file ops) | Workers write to LOCAL temp dir, coordinator atomic-moves into Dropbox song folder |
| Dropbox `New_Song_Tracks/Don't Bring Me Down/.workers/` creates indexable garbage | Low | Low | Use `~/.kv-downloader-workers/` outside Dropbox, then atomic-rename into song folder |

---

## What NOT to do

- **Don't go above N=4 without strong evidence.** Tempting to crank to N=10; almost certainly trips abuse heuristics.
- **Don't share Chrome profiles between workers.** Cookie races and login state corruption guaranteed.
- **Don't build a custom queue.** `multiprocessing.Queue` or even a `threading.Lock` + `list` is enough.
- **Don't merge into Dropbox per-track during the run.** Dropbox sync queue + concurrent writes is a footgun. Stage in `~/.kv-downloader-workers/`, atomic-move at the end of each successful track or song.
- **Don't reuse the same chromedriver binary across workers without a per-worker `--user-data-dir`.** Two Chromes pointing at the same profile = data corruption.

---

## Decision points needing the user's input

1. **Worker count default**: 4? 3? Configurable?
2. **Workers location**: `~/.kv-downloader-workers/` or somewhere else? (Must be outside Dropbox.)
3. **What to do on captcha**: pause-and-prompt, or abort the song and surface to the user?
4. **Phase 0 — manual two-window test**: would you do this yourself, or want a Selenium harness for it?

---

## Realistic outcome

If Phase 0 confirms concurrency works at N=4, expected wall-time for a 15-track song:

- Today (post-Tier 1): ~4:30
- N=2:                  ~3:00 (50% headroom for ramp-up)
- N=3:                  ~2:15
- N=4:                  ~1:45

If Phase 0 confirms concurrency works at N=2 only:

- Best case ~3:00 — still a 33% improvement, worth the effort.

If Phase 0 fails outright:

- We document the constraint and stop. Tier 1 + the click-track fix is the floor.

---

## Why this is the right project, even if it's the last optimization

After Tier 2, the only remaining optimization paths are:
- Move the song folder out of Dropbox (1–3s per song; tiny)
- Optimize Selenium/chromedriver overhead (negligible — we're already at sub-second client-side per track)
- Convince Karaoke-Version to pre-generate mixes (out of our control)

So Tier 2 is the meaningful endpoint. After this, the system is bound by the slowest single track's server-compute time, not by sequential overhead.
