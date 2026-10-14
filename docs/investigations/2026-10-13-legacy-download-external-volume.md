# 2026-10-13 — Legacy (Selenium) downloads silently failing

## Symptom

With `--legacy-selenium-download` (or the automatic fallback from the
direct-API path), every track logged the site's "download ready" modal, then
waited out the full timeout:

```
✅ Download ready signal detected for Intro count Click
🔍 Checking for NEW downloads in …/Heartbreaker (waited 0s … 90s)
✅ Completion monitoring finished for Intro count Click (success=False)
```

Nothing appeared in the song folder — not even a `.crdownload`.

## Root cause: macOS blocked Chrome from writing to the external drive

`~/Dropbox` is a symlink to `/Volumes/RayCueSSD/Dropbox` (since 2026-08-04,
after the legacy path was last validated in May). Chrome downloaded each file
**in full** into a hidden temp file in `~/Downloads`
(`.com.google.Chrome.XXXXXX`, 8,482,922 bytes — the real track size) and then
could not move it onto the external volume. The direct-API path was
unaffected because Python (the terminal app) already had access.

Fixed by granting Chrome access in macOS Privacy & Security (user action,
2026-10-13). No code change.

**If the legacy path stops producing files again:** look for
`.com.google.Chrome.*` temp files in `~/Downloads`. A full-size one means the
download worked and only the final move to the target folder failed →
permissions.

## How it was isolated (one variable at a time)

`modal_probe` style: solo a track, click `a.download`, record the modal and
the download folder. Each run changed one thing:

| Download folder | Command | Popup | Result |
|---|---|---|---|
| internal scratch dir | `Browser.setDownloadBehavior` | left open | ✅ file in ~5 s |
| internal scratch dir | `Page.setDownloadBehavior` (what the code uses) | left open | ✅ — the CDP command is fine on Chrome 155 |
| internal scratch dir | `Page.setDownloadBehavior` | closed immediately (what the code does) | ✅ — closing the modal doesn't cancel it |
| dir on the external SSD | same | left open | ❌ nothing; full-size temp file stuck in `~/Downloads` |
| dir on the external SSD, after the permission grant | same | left open | ✅ |

## Also found in the same session

- **Re-run misdetection (fixed, PR #4):** `wait_for_download_to_start`'s
  pre-wait check accepted any long-ish audio filename, so finished tracks
  (`Lead Electric Guitar.mp3`) on a re-run were reported as "Download
  started". Now only `.crdownload` or the server's raw
  `*_Custom_Backing_Track*` filename count.
- **Server-side render stalls:** some legacy attempts got no modal at all
  ("Download modal overlay did not open within 30s"). This is the site being
  slow, the same thing that makes `basket.php` return 503s; the per-song and
  end-of-run retries recovered every one.
- **Slow direct-API transfers (open):** three tracks took 317–481 s with no
  retries and complete files. PR #5 logs `basket/render/transfer` per track;
  see `docs/known-issues.md`.
- **Same-size files ≠ complete, different size ≠ truncated:** within a song
  most tracks have identical byte counts, but some differ by 1,024 bytes —
  entirely in the ID3v2 tag padding; the audio payload was byte-identical in
  length and durations matched. Check decoded duration, not file size.
