# PLAN.md

Active follow-ups for kv-downloader.

## Direct-API rewrite: skip Selenium for the download path (~37% faster)

**Status:** Not started. Highest-value remaining optimization.

**Background:** While probing whether single-account parallelism was
possible (it isn't — see
`docs/plans/2026-05-08-tier2-parallel-downloads.md`), we discovered that
the entire mixer-state→download flow is two HTTP endpoints:

```
GET /basket.php?method=ajax&famid=5&precount=1&trackslevels=...
   &pannings=...&bkac=editf&s={song_id}&prodid={prodid}&pitch=...
GET /my/begin_download.html?id={prodid}&famid=5&produced=1&method=ajax
```

`basket.php` updates the basket AND triggers server-side mix-gen
(asynchronously). `begin_download.html` returns the modal HTML
containing the c*.recis.io MP3 URL — when polled, the URL hash changes
once the new mix is ready (~7-14s after basket.php). The MP3 is then a
plain CDN GET. Validated end-to-end by `tools/probe_direct_api.py`
producing distinct mixes per track via direct API calls.

**Speedup.** Existing Selenium flow is ~16-18s per track. Direct-API is
~10-11s per track — solo button click (~3s), audio-server-sync wait
(~1s), modal handling (~1s), and Chrome download-manager round-trip
(~2s) all disappear; only basket.php (~0.7s) + ~7s mix-gen wait + ~2s
fetch remain. **~6s/track × 15 tracks ≈ 90s/song (~37%).** And it drops
a large class of Selenium failure modes: solo button not latching,
modal handling, file-collision detection, etc.

**Implementation sketch.**
1. Use Selenium ONCE per session for: login (chrome_profile cookie reuse
   already works) and capturing the basket.php template URL for each
   song (gets us prodid, song_id, pannings, pitch). Keep cookies.
2. Close Chrome.
3. For each track: build trackslevels with target track at 100, others
   at 0 (preserve bare-numeric edge slots — they encode flags like
   precount and changing them triggers HTTP 500); call basket.php; poll
   begin_download.html until the MP3 URL hash changes; fetch via
   `requests` with cookies.
4. Apply existing file-naming/cleanup logic to the fetched bytes.

**Risks.**
- The basket template depends on the page's prodid + pannings being
  current. If the user has special pannings or has saved a different
  default, we want to capture once per song with their actual setup.
- CSRF/anti-abuse: didn't see any token, but if the site adds one
  later, the direct-API path breaks until updated.
- Cookies expire — falls back to LoginManager re-auth.

**Compatibility with pipelining (below):** stacks. Direct API removes
the per-track ~6s overhead; pipelining removes another ~2s/track on top.
Combined: ~8s/track on a 15-track song = ~2 minutes total
(vs current ~4-5 minutes, ~50-60% reduction).

**Why not done yet.** Discovered late in the Tier 2 investigation; the
team had moved on from the parallelism dead-end and this requires a
medium-sized refactor of `download_manager`. Tier 1's smaller wins
shipped first because they were 1-line constant changes.

---

## Pipelining: overlap track N's file delivery with track N+1's solo

**Status:** Not started. Considered safe and contained.

**Background:** Tier 2 (parallel downloads) was cancelled after Phase 0 found
that the site collapses concurrent mix-gen requests on a single account to a
single mix (see `docs/plans/2026-05-08-tier2-parallel-downloads.md`). The
remaining cheap optimization is pipelining the per-track flow.

**Idea.** Each track currently runs as:

```
T=0    solo(N)
T=2    click download
T=2    server mix-gen     ← server busy, client idle for ~14s
T=16   modal opens
T=16   file delivery
T=18   file complete
T=18   solo(N+1) starts
```

Once the modal opens at ~T=16 the mix file is already finalized as a static
asset on `c13.recis.io`. State changes after that point cannot affect the
already-generated file — it's a plain CDN GET. So `solo(N+1)` can start the
moment the modal opens, in parallel with the file delivery for track N:

```
T=0    solo(N)
T=2    click download (N)
T=16   modal opens for N (mix already on CDN); START solo(N+1) HERE
T=18   click download (N+1) (file N still arriving)
T=18   file N done           ← overlaps with solo(N+1) and click(N+1)
```

**Expected savings.** ~2s/track × 15 tracks ≈ **30s on a 15-track song
(~12%).** Not exciting, but contained and risk-free.

**Risk.** Low. Mix N is a static file once the modal opens; soloing the next
track cannot retroactively corrupt it. The only edge is if download N fails
after modal-open (rare — at that point it's just a CDN GET) and we need to
retry: at retry time the mixer state has already moved on to N+1, so we'd
need to redo solo(N) + click(N). Cheap enough to handle by capturing the URL
at modal-open and retrying the GET directly without redoing the UI flow.

**Where to wire it.**
- Hook in `download_manager._wait_for_download_readiness()` —
  when the readiness text is detected, emit a "ready" signal back to the
  orchestrator.
- Orchestrator runs file-delivery monitoring on a background thread and
  immediately starts `solo(N+1)` on the foreground.
- Either share one Chrome (single-tab pipelining inside the orchestrator) or
  two tabs (one for delivery, one for next solo). Single-tab is simpler if
  the file delivery doesn't need driver attention.

**Why not done yet.** Tier 2 was the higher-priority win and consumed the
parallelism budget. This is the consolation prize.
