# 2026-07-30 — "Lead Electric Guitar.mp3" contained the rhythm guitar

> Moved here on 2026-10-23 from the untracked `WORKING_NOTES.md` of the session
> that fixed it (PR #2, squash-merged as `72baf71`). Its "next actions" are
> historical: the merge happened; `bin/ruff` now exists. The design plan (with its
> adversarial-review corrections) landed and was pruned; read it in git history:
> `git show 72baf71:docs/plans/2026-07-30-verify-track-identity.md`.

## Task

Root-cause and fix: `Hold The Line` downloaded 14/14 "successfully", but
`Lead Electric Guitar.mp3` contained rhythm-guitar audio.

## Status: DONE — merged to main

PR #2 squash-merged as `72baf71`; branch deleted. Verified on `main`:
439 tests pass (exit 0), `direct_api/` passes ruff clean.

- 439 unit tests pass (418 baseline + 21 new), no regressions.
- **Live smoke passed** — both assumptions closed against the real site:
  - `[verified 'Lead Electric Guitar']`
  - `[verified 'Rhythm Electric Guitar (muted right)']` ← parenthesized
    name, which a leftmost-`(` regex would have mangled.
- **Missing lead guitar recovered and verified** against the user's
  manually-downloaded reference: identical duration (239.880567s),
  identical size, envelope correlation 1.0000. Correlates 0.001 with the
  rhythm guitar that was wrongly in its place.
- Folder re-swept: 14 files, no duplicates.
- Plan + adversarial-review corrections: pruned after landing (see the note at the top).

## What was wrong

`DirectDownloader._poll_for_fresh_url` accepted any render whose CDN URL
hash differed from the previous download's — content-blind, never checked
the render matched the requested track. Under congestion the server
returned a NEW hash carrying the PREVIOUS track's audio.

Confirmed empirically: `Lead Electric Guitar.mp3` correlates 1.0000
(sample-level waveform) with `Rhythm Electric Guitar (muted right).mp3`;
the real lead guitar is absent from the folder (≤0.018 vs all 14 files).
Only that one file was affected.

## Fix

Accept only when **fresh hash AND server label identifies the target**.
The CDN filename carries the server's authoritative track label. Classify
only fresh-hash sightings (so stalls stay `MixGenTimeout`); re-issue
`basket.php` once on first mismatch; unresolvable labels fall back to
hash-only and are counted with an end-of-song warning.

## Gotchas worth remembering

- **MP3 hashes are useless for content comparison** here — encoder
  nondeterminism. Use decoded-PCM correlation. A loudness envelope is too
  coarse (false-positived riff L/R at 0.994); sample-level correlation
  discriminates cleanly (~1.0 vs ~0.00). Always run a positive control.
- Server says `"Click"` where the DOM says `"Intro count Click"` — exact
  equality would silently disable verification for track 0 of every song.
- A leftmost-`(` regex breaks on parenthesized song titles; parse the
  label by walking backward from the `_Custom_Backing_Track)` suffix.
- Existing test fixtures use label-less CDN URLs — they exercise the
  fallback path, which is why they must stay green.

## Also learned during the smoke

- **The server intermittently refuses to render**: the first smoke attempt
  failed both tracks with `last_url=None` (13-14 polls, no MP3 URL at all),
  then an immediate retry succeeded 14/14. This is the documented cascade
  flakiness in `docs/site-flow/trackslevels-format.md`, unrelated to the
  identity fix — that path never sees a URL, so verification never runs.
  Treat a `last_url=None` run as "retry", not "broken code".
- **Two different renders of the same track do NOT correlate at sample
  level** (~0.41 for lead guitar) — encoder dither dominates the silent
  stretches. Use the loudness envelope to compare *different renders*, and
  sample-level only to detect *the same render served twice*. Neither
  metric alone is sufficient: the envelope false-positives riff L/R at
  0.994 where sample-level gives -0.000.

## Next actions

1. Merge to `main` only after user approval (project rule).
2. Not done: **ruff not installed** in the venv, no ephemeral runner
   available — code was never linted. Modules compile clean.
3. Optional: promote the audio duplicate-checker into `tools/` (currently
   scratchpad only). If promoted it needs BOTH metrics per the note above —
   the current envelope-only threshold false-positives on riff L/R.
4. Consider a `docs/investigations/` entry for this bug; the diagnostic
   method (server label as ground truth + dual-metric audio comparison) is
   the reusable part.
