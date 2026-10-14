# Fastly bot challenge (2026-10-13)

## What the site does

Since ~2026-10 karaoke-version.com is behind **Fastly bot management**.

- **Normal browsers** pass a silent "verifying your browser" check.
- **The Selenium-driven browser** (headless *and* visible, with or without a
  current-version UA) is escalated to an image CAPTCHA: page title
  `Client Challenge`, assets under `/_fs-ch-<id>/`.
- **Plain HTTP clients** (`requests`) get the same challenge page as an
  **HTTP 200** `text/html` body (~3 KB) — so status-code checks don't catch it.

Symptom before handling existed: every song logged
`Page load timeout during song access verification` →
`No tracks found` (the login check still "passed", because it only looks for
the absence of a "Log in" link).

## Clearance

A human solve in the automation's own browser sets two cookies on
`www.karaoke-version.com`: `_fs_ch_cp_<id>` and `_fs_ch_st_<id>`. They
persist in `chrome_profile/`, and a later **headless** run on a different
song passed with them (verified live 2026-10-13). Lifetime unknown — when it
expires, the run stops with the CAPTCHA message again.

Solving in the user's everyday Chrome does nothing for the tool: it uses its
own profile.

## How the code handles it

`packages/utils/bot_challenge.py` — detection only. We never try to solve or
evade the challenge; it is handed to the user.

| Where | Detects via | Headless | Visible (`--debug`) |
|---|---|---|---|
| `TrackManager.verify_song_access` (every song) | page title | raise `BotChallengeError` → batch stops with instructions | wait ≤180 s for the user to solve, then continue |
| `DirectDownloader` (`basket.php`, `begin_download.html`) | `/_fs-ch-` in body | raise `BotChallengeError` | same |
| Automator, mid-song | catches the above | reload song page via `verify_song_access` (raises), stop | user solves, cookies re-copied into the HTTP session, track retried once |

## Known gaps

- The legacy Selenium download path's mid-song `driver.get(song_url)`
  reloads (solo recovery etc.) don't check for the challenge; a challenge
  there shows up as ordinary track failures, and the next song's
  `verify_song_access` catches it.
- `capture_session` navigates on its own only if not already on the song
  page (normally it is, right after `verify_song_access`).

## Related: `503 first byte timeout` from basket.php

Not a challenge — Fastly gave up waiting (~15 s) for the origin to build the
mix. Seen live 2026-10-13 as a ~1 min burst that then recovered (ordinary
pages stayed at ~0.3 s TTFB). `DirectDownloader._call_basket` retries a 503
once after `BASKET_503_RETRY_DELAY_S` (10 s); a second 503 raises
`BasketUpdateError` as before. Tracks lost to a longer burst are picked up by
re-running — existing files are skipped.
