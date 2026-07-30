# Plan: verify downloaded track identity against the server's own label

**Status:** proposed (2026-07-30)
**Branch:** `feature/verify-track-identity`

## The bug (confirmed empirically, 2026-07-30)

User ran `Hold The Line` (Toto, 14 tracks). Run reported 14/14 success.
`Lead Electric Guitar.mp3` actually contains the **rhythm guitar** part.

Evidence gathered before proposing this fix:

| Check | Result |
|---|---|
| Sample-level waveform correlation, `Lead Electric Guitar.mp3` vs `Rhythm Electric Guitar (muted right).mp3` | **1.0000** — identical audio |
| Same file vs the other 12 | ~0.00 |
| User's manually-downloaded correct lead guitar vs all 14 files | ≤ 0.018 — **the real lead guitar is absent from the folder** |
| `Rhythm Electric Guitar (riff left)` vs `(riff right)` | −0.000 — genuinely distinct, correctly downloaded |
| Blast radius | **exactly one file** affected |

Method was validated with a positive control (self-correlation 1.000, known
pair 1.000, unrelated ~0.00). A loudness-envelope metric was tried first and
produced a false positive on riff L/R (0.994) — sample-level correlation is
the reliable discriminator.

Timing from `logs/automation.log`:

```
12:07:57  Rhythm Electric Guitar (muted left)  → 51.3s   <- server congested
12:08:16  Rhythm Electric Guitar (muted right) → 19.4s
12:08:24  Lead Electric Guitar                 →  7.1s   <- fastest of 14
```

A genuine fresh render is ~12s+. 7.1s means no fresh render happened.

## Root cause

`direct_downloader.py:201` `_poll_for_fresh_url` accepts a render on:

```python
if self._last_hash is None or this_hash != self._last_hash:
    return url
```

This is a **content-blind negative check** — "is this hash different from the
last one I downloaded?" It never asks "is this the track I requested?"

Under server congestion the `basket.php` cart update had not taken effect
before mix-gen fired, so the server produced a **new hash carrying the
previous track's audio**. New hash → check passes → saved under the wrong
name, silently, with a 200 and a plausible file size.

Three existing signals all failed to catch it: HTTP 200 (real file), file
size (every track is byte-identical in size), SHA-256 (differs even for
identical audio — see `docs/site-flow/mp3-encoder-nondeterminism.md`).

**The server already tells us the answer and we discard it.**
`begin_download.html` returns a URL whose filename is generated server-side
from the soloed track:

```
Toto_Hold_the_Line(Lead_Electric_Guitar_Custom_Backing_Track).mp3
```

`docs/investigations/2026-05-09-direct-api-mapping-precount-cascade.md` §1
calls this "the server's authoritative track label" and "the breakthrough"
for the *previous* mapping bug. `tools/probe_track_mapping.py` already parses
it. It was never wired into the production path — `extract_mp3_url` captures
the full URL, then `url_hash()` throws everything but the hash away.

## Design

Add a **positive identity gate** on top of the existing freshness gate.

> **Revised 2026-07-30 after adversarial review.** The first draft said
> *replace* the hash check with a label check, and keyed the accept/reject
> decision on the label alone. Both were wrong; see "Review corrections"
> below. The hash check stays.

### Accept rule: fresh hash **AND** verified label

```
accept  ⟺  hash != last_downloaded_hash        (freshness — unchanged)
       AND  server label identifies target      (identity — new)
```

Freshness is what stops a *stale* render being taken; identity is what stops
a *fresh render of the wrong track*. They are orthogonal and both are needed.

### Decision table (keyed on freshness first, then label)

Classification happens **per fresh-hash sighting**, at accept time. A
stale-hash sighting is never classified and never latches a mode.

| Hash | Label identifies | Action |
|---|---|---|
| stale | *(not examined)* | keep polling; on deadline → `MixGenTimeout` |
| fresh | target track | **accept** |
| fresh | a *different* track | re-issue `basket.php` **once**, keep polling; on deadline → `TrackMismatchError` |
| fresh | nothing recognizable | fallback: accept only if filename ≠ last accepted filename; warn |

Keying on freshness first is what preserves the stall/mismatch distinction —
during normal polling the cart holds the *previous* track's render, which
would otherwise read as "wrong track" on every single poll and turn every
ordinary slow render into a spurious `TrackMismatchError`.

### Identity by unambiguous match, not exact equality

Exact equality is wrong: the postmortem records the server labelling the
click track `"Click"` while `mixer.tracks[0].description` is
`"Intro count Click"` — verified at
`docs/investigations/2026-05-09-direct-api-mapping-precount-cascade.md:58`.
Exact-only would silently disable verification for track 0 of every song.

Containment alone is also wrong — the test fixture holds both
`"Lead Electric Guitar (left)"` and `"Lead Electric Guitar"`, and this song
holds `"Lead Vocal"` and `"Lead Vocal (ad lib)"`.

So: **exact match first; fall back to containment; accept either only when
exactly one track matches.** Ambiguous or unmatched → unknown → fallback row.
This resolves `Click` (unique containment) while keeping `Lead Vocal` exact.

### Parsing: balanced-paren scan, not a leftmost-`(` regex

`\((.+)_Custom_Backing_Track\)\.mp3` anchors on the *leftmost* `(`, so a
parenthesized **song title** poisons the capture. Verified:

```
Stones_(I_Cant_Get_No)_Satisfaction(Drum_Kit_...)  → 'I_Cant_Get_No)_Satisfaction(Drum_Kit'
Ricky_Livin_la_Vida_Loca_(Radio_Edit)(Bass_...)    → 'Radio_Edit)(Bass'
```

Instead: anchor on the fixed `_Custom_Backing_Track)` suffix and walk
**backward** with a paren-depth counter to the balancing `(`. Handles nested
track parens and title parens alike. Unquote first; NFKD-fold to ASCII so
accented names survive transliteration.

## Changes

### `packages/download_management/direct_api/direct_downloader.py`

1. `class TrackMismatchError(RuntimeError)` — distinct from `MixGenTimeout`
   so logs/stats can tell "server stalled" from "server rendered the wrong
   track".
2. `extract_track_label(url) -> Optional[str]` — pure; unquote → balanced
   backward paren scan → underscores to spaces. `None` when unparseable.
3. `normalize_label(s) -> str` — pure; NFKD→ASCII, lowercase, alphanumeric-only.
4. `identify_track(label, mixer_tracks) -> Optional[int]` — pure; unique
   exact match, else unique containment match, else `None`.
5. `_poll_for_fresh_url(...)` gains `target_index` and `trackslevels`;
   implements the decision table, re-issues `basket.php` once on the first
   fresh mismatch, and records the last-seen hash before raising so the next
   call cannot treat that render as fresh.
6. `download_track` passes both through; tracks `_last_filename` for the
   fallback comparison.

**Recovery, not just detection:** on the first fresh-hash mismatch the
downloader re-sends `basket.php`. If the cart update was *lost* (the leading
theory), re-sending it is the actual repair — polling alone would never
produce the right render. Without this the fix would trade a corrupt file
for a hard failure plus, via the 2-consecutive-failure cascade abort, the
loss of every remaining track in the song.

### `karaoke_automator.py`

6. Catch `TrackMismatchError` in `_download_single_track_direct_api`
   alongside the existing direct-API errors, count it toward
   `consecutive_failures`, and surface a distinct message. **Must not** be
   silently swallowed into the generic handler.

### Tests — `tests/unit/test_direct_downloader.py`

Existing fixture URLs carry no label, so they exercise the fallback path and
must stay green (proves the safety valve works). New realistic fixtures:

```python
CDN_URL_LEAD  = "https://c1.recis.io/sl/k/bbb1234567ffeedd/Toto_Hold_the_Line(Lead_Electric_Guitar_Custom_Backing_Track).mp3"
CDN_URL_RHYTHM= "https://c1.recis.io/sl/k/ccc7654321aabbcc/Toto_Hold_the_Line(Rhythm_Electric_Guitar_(muted_right)_Custom_Backing_Track).mp3"
```

Test list:

- `extract_track_label` — simple name; **nested parens**; **parenthesized
  song title**; percent-encoded; no-label URL → `None`; malformed → `None`.
- `normalize_label` — underscores/spaces/parens/case equivalent; accented
  name folds to ASCII.
- `identify_track` — `"Click"` resolves to `"Intro count Click"`;
  `"Lead Vocal"` resolves to the exact track, not `"Lead Vocal (ad lib)"`;
  ambiguous label → `None`; duplicate descriptions → `None`.
- **Regression (the actual bug):** request Lead Electric Guitar, server
  serves the rhythm-guitar label with a *fresh* hash → assert
  `TrackMismatchError` and **assert no file was written to `dest`**.
- **Freshness preserved (pins blocker #1):** stale hash whose label matches
  the target must NOT be accepted.
- **Stall stays a stall (pins blocker #2):** all-stale polling raises
  `MixGenTimeout`, never `TrackMismatchError`.
- Self-heal: mismatched label on poll 1, correct label on poll 2 → succeeds,
  writes the correct file, and `basket.php` was re-issued exactly once.
- `_last_hash` is recorded after a mismatch failure.
- Unknown label matching no track → fallback; identical filename must still
  be rejected even when the hash is fresh (catches the observed bug with
  zero format assumptions).

The existing label-less fixtures already exercise the fallback path, so
their staying green *is* the fallback regression test — no dedicated test
for that.

## Review corrections (adversarial review, 2026-07-30)

Changes forced by review, with the two blockers first:

1. **Accept rule regressed freshness.** Draft accepted on label match alone,
   so a stale render whose label matched the target would be taken —
   re-runs resuming on a track, and duplicate track descriptions, would
   silently reproduce the original bug. → hash AND label.
2. **Stall/mismatch conflated.** Draft classified every poll by label; the
   cart holds the previous track's render during normal polling, so every
   ordinary slow render would have raised `TrackMismatchError`. → classify
   only fresh-hash sightings.
3. **Click-track counterexample** (verified in postmortem:58) → unambiguous
   match instead of exact equality.
4. **Regex broke on parenthesized song titles** (verified empirically) →
   balanced backward paren scan.
5. **Fallback strengthened** — compare the filename verbatim, which catches
   the observed bug with no format assumptions; plus end-of-song visibility
   so degradation is reported where success is reported.
6. **Detection without recovery** → re-issue `basket.php` once on first
   mismatch.
7. Per-poll classification never latches a mode; record `_last_hash` on
   mismatch; NFKD-fold for accents; specified duplicate-description handling.

Also corrected for honesty: the correlation evidence establishes that
`Lead Electric Guitar.mp3` duplicates `Rhythm Electric Guitar (muted
right).mp3` and that the real lead guitar is absent — it does *not* prove
the muted-right file itself holds muted-right audio. Percent-encoding is
assumed, not observed. `probe_track_mapping.py` extracts the whole filename,
not the track label.

## Risks

| Risk | Mitigation |
|---|---|
| Server label format differs from the one real sample we have | Fallback on unrecognized formats; only a confident wrong-track match rejects |
| Normalization too strict → false rejection | Unique-match required *only* against known descriptions; anything unrecognized degrades to current behavior |
| Paren scan wrong for some name | Unit-tested against nested parens and title parens; unparseable → fallback |
| Real filename format unverified for parenthesized names | **Live smoke required before merge** (see below) |
| Format drift silently disables verification | Verbatim-filename check still catches the observed bug; end-of-song count reports hash-only tracks |

## Validation

1. `bin/python -m pytest tests/unit/` — full suite green (418 baseline).
2. Live smoke against `Hold The Line` — required by project rules for any
   `direct_api/` change. Confirms the real filename format for
   parenthesized track names, and should recover the missing lead guitar.
3. Re-run the audio duplicate check on the re-downloaded folder.

## Out of scope

- The unbounded legacy-Selenium timeouts in `docs/known-issues.md`.
- Promoting the audio-fingerprint script into `tools/` (offer separately).
- Re-downloading the user's other songs.
