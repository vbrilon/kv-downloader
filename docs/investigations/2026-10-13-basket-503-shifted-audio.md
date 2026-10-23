# 2026-10-13 — Direct-API tracks with the previous track's audio after a basket.php 503

## Symptom

User spot-check: in *Heartbreaker* "Bass has the drums, Drum Kit has the
click"; same in *Are You Gonna Be My Girl*. Every affected file had been
**label-verified** (`[verified 'Drum Kit']`): the server's own CDN filename
named the requested track, the audio was a different one.

## Evidence

Loudness-envelope correlation (stdlib + ffmpeg; 50 ms RMS windows). Ground
truth = the same tracks re-downloaded through the legacy browser path, whose
files matched correctly in every comparison. Each suspect file was matched
against every fresh track of its song; best match 1.000, next best ≤ 0.79:

| Song | basket.php 503 on | Wrong files that followed (→ actual content) | Then correct from |
|---|---|---|---|
| Heartbreaker | Intro count Click | Drum Kit → Click; Bass → Drum Kit | Rhythm EG 1 |
| White Room | Timpani | Bass → Timpani; Rhythm EG (left) → Bass | Rhythm EG (right) |
| White Room | Rhythm EG (right) | none (Lead EG correct) | — |
| White Room | Arr. EG 3 | Distorted EG → Arr. EG 3; Organ → Distorted EG | String Section |
| Are You Gonna Be My Girl | Percussion | Bass → Percussion; Rhythm EG (left) → Bass | Rhythm EG (right) |
| Are You Gonna Be My Girl | Lead EG | Lead Vocal → Lead EG (last track) | — |

**9 wrong files, all within two tracks after a 503.** Every direct-API file
outside those windows was correct, including the songs with no mid-song 503
(*Living Loving Maid*, *Mary Jane's Last Dance*, *Sweet Child O Mine*;
*Hit Me With Your Best Shot*'s 503s were its last two tracks). The user
confirmed by ear that only these songs were wrong.

Envelope correlation can false-positive on near-identical parts (riff L/R
scored 0.994 on 2026-07-30). Here the pairs are different instruments at
1.000 (click vs drums, timpani vs bass), with the user's ear as a second
check. Sample-level correlation can't help: the suspect and reference files
are different renders, which never match sample-for-sample.

## Mechanism (inferred, not observed server-side)

A 503 from basket.php is Fastly's "first byte timeout": Fastly stopped
waiting, but the origin still processes the request and renders that mix
**late**. The next tracks' polls then see a fresh CDN hash whose filename
label names the *new* request while the audio is the *late* render: one
behind. It resynchronises after one or two tracks. Download time doesn't
reliably mark the bad files: most were fast (3.5–7 s), one took 11 s.

This is also the 2026-07-30 *Hold The Line* bug (congestion; the next file
held the previous track's audio). That fix
([`2026-07-30-wrong-track-audio.md`](2026-07-30-wrong-track-audio.md)) assumed a stale render
would carry the stale label; today shows the label can be fresh while the
audio is stale. **The label proves what was requested, not what was
rendered.**

## Fix

- `DirectDownloader._call_basket`: a 503 raises `BasketTimeoutError`
  (deliberately not a `BasketUpdateError`, so it escapes the per-track
  handler). The 10 s single retry added earlier the same day is removed:
  re-sending puts a second render in flight on a server already processing
  the first.
- `_download_all_tracks_direct_api`: on `BasketTimeoutError`, that track and
  the **rest of the song** go through the legacy browser path, which waits
  for the site's own "download ready" modal. Per song, not per run: the
  shift never crossed songs (*Living Loving Maid*, right after *Rock And
  Roll*'s 503s, was clean).

## Repair done

The 24 direct-API files of the three songs were moved aside, the songs were
re-downloaded via the browser path (duplicate scan of all three: none), and
the old files were then deleted at the user's request. The evidence table
above is the only record of their content.

## Diagnostic recipe (when a user reports "track X has instrument Y")

1. Duplicate scan per song folder: decode each MP3
   (`ffmpeg -ac 1 -ar 4000 -f s16le`), 50 ms RMS envelope, pairwise Pearson
   correlation; flag pairs > 0.95. A shift only shows up as a duplicate where
   a neighbouring track came from a different path. A fully-shifted folder
   has no duplicates.
2. For ground truth, re-download through the browser path into a separate
   folder and match each suspect file against every fresh track.
3. Line the wrong files up against the run's 503s and slow renders. Note that
   `logs/automation.log` is overwritten by every run.
