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
song passed with them (verified live 2026-10-13).

**They last about an hour** (solved ~18:06, gone by ~19:08 on 2026-10-13).
After they expired the picture flipped:

- The **browser** was trusted on every page (song page and
  `begin_download.html`) with **no** `_fs_ch_*` cookies at all — no CAPTCHA.
- **Plain HTTP** (`requests` with the browser's cookies copied in) was
  challenged on every call.

So with no clearance cookie there is nothing for the user to solve, and the
direct-API path stays blocked until the browser is challenged and solved
again. Watch the cookie count in `capture_session: snapshotted N cookies`:
it dropped 8 → 7 when one `_fs_ch_*` cookie expired.

Solving in the user's everyday Chrome does nothing for the tool: it uses its
own profile.

## How the code handles it

`packages/utils/bot_challenge.py` — detection only. We never try to solve or
evade the challenge; it is handed to the user.

| Where | Detects via | Headless | Visible (`--debug`) |
|---|---|---|---|
| `TrackManager.verify_song_access` (every song) | page title | **pop up a visible Chrome window** (same profile) at the challenged page, alert the user (macOS notification + terminal bell), wait ≤180 s for the solve, then swap back to headless | alert, wait ≤180 s in the existing window |
| `DirectDownloader` (`basket.php`, `begin_download.html`) | `/_fs-ch-` in body | raise `BotChallengeError` | same |
| Automator, mid-song | catches the above | reload song page via `verify_song_access` (pops up the CAPTCHA if the browser is challenged), cookies re-copied, track retried once | same, solved in the existing window |
| Automator, retry still challenged | browser fine, HTTP not | **switch the rest of the run to legacy Selenium downloads** (`self.direct_api = False`), starting with this track | same |

Unsolved within 180 s → `BotChallengeError`, which stops the run (a headless
run is swapped back to headless first). Still challenged right after a solve →
`BotChallengeError` too, so it can't loop. The pop-up lives in
`KaraokeVersionAutomator._solve_bot_challenge` / `_swap_browser`, passed to
`TrackManager` as `challenge_solver`; standalone tools that build a
`TrackManager` without one still get the "re-run with --debug" error. Chrome
can't open one profile twice, so the swap is quit → relaunch, and the new
driver is handed to the login, track and download managers.

The switch is sticky for the run: without a fresh solve the fast path can't
recover, so re-trying it per song would only waste a reload and two
challenged calls. A new run tries the fast path again first. Verified live
2026-10-13 (`Heartbreaker`, clearance expired: challenged → reload → still
challenged → switched → both tracks downloaded via the browser).

The legacy path writes through Chrome, which needs macOS permission to write
to the download folder's volume — see
`docs/investigations/2026-10-13-legacy-download-external-volume.md`.

## Known gaps

- The legacy Selenium download path's mid-song `driver.get(song_url)`
  reloads (solo recovery etc.) don't check for the challenge; a challenge
  there shows up as ordinary track failures, and the next song's
  `verify_song_access` catches it.
- `capture_session` navigates on its own only if not already on the song
  page (normally it is, right after `verify_song_access`).

## Related: `503 first byte timeout` from basket.php

Not a challenge — Fastly gave up waiting (~15 s) for the origin to build the
mix. **The origin may still render it late**, which shifted the next one or
two direct-API tracks' audio by one (label-verified, wrong audio). A 503 now
moves the rest of that song to browser downloads; see
`docs/investigations/2026-10-13-basket-503-shifted-audio.md`.
