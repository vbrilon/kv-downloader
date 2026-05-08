# Phase 8 Research Spikes (2026-05-08)

## 8.1 — Direct API call to `mixer.getMix()` instead of clicking the button

**Question:** Can we bypass the Selenium download-button click + popup flow by calling `mixer.getMix()` directly?

**Evidence (from Phase 2 live inspection):**
- `mixer.getMix` body:
  ```js
  this.parameters.trackslevels = this.getLevels();
  this.parameters.pannings = this.getPannings();
  if (typeof this.getMixCallback === "function") this.getMixCallback();
  this.editMix();
  ```
- The function returns `void`. The download URL appears asynchronously inside the modal DOM after `editMix()` completes its backend request (~14s of server time).

**Conclusion: SKIP.** There is no faster path. The existing JS click `arguments[0].click()` already fires the same `onclick="mixer.getMix();return false;"` handler — which IS the API call. Spending engineering effort on calling `getMix()` directly via `execute_script` would yield zero perceptible improvement, and we'd still need to wait for the modal to populate to extract the download URL.

## 8.3 — Move downloads out of Dropbox-synced folder

**Current state:** `.env` has `DOWNLOAD_FOLDER=/Users/victorbrilon/Library/CloudStorage/Dropbox/New_Song_Tracks`.

**Why this matters:** Every file create / delete (including `shutil.rmtree` in `clear_song_folder` and the `clean_downloaded_filename` rename step) triggers Dropbox sync events. macOS's CloudStorage layer can serialize file operations on the sync daemon, occasionally adding tens-to-hundreds of milliseconds to filesystem operations.

**Effect on the hot path:**
- `clear_song_folder` runs once per song. Cost is roughly proportional to file count being removed. Probably small.
- `clean_downloaded_filename` runs once per track (renames the downloaded file). Each rename triggers a Dropbox sync event. Again, small but adds up across 15 tracks.
- `_get_file_info` / `_scan_directory_cached` poll the song folder during `_monitor_download_progress`. Each scan iterates the directory and does `stat()` on each file. Dropbox-synced folders sometimes return slower stat results during heavy sync activity.

**Recommendation: viable, low-risk, low-effort.**

Steps to validate:
1. Edit `.env` to change `DOWNLOAD_FOLDER` to a local path:
   ```
   DOWNLOAD_FOLDER=/Users/victorbrilon/karaoke-downloads-staging
   ```
2. Run the same `python karaoke_automator.py --profile --max-tracks 5` benchmark.
3. Compare the `mean per-track` to the current 22.5s baseline.
4. If meaningfully faster, add a habit (or a wrap script) to `rsync -a /tmp/staging/ ~/Dropbox/New_Song_Tracks/` after each session — the move is incremental, and Dropbox handles it as a single batch.

I have NOT made this change because it touches the user's machine config (`.env`) and download habits. It's a one-line change you can apply yourself when you want to test it; if it shows a real speedup on a 5-track run, the answer is "yes, do it." If not, leave it as-is.

## Other spikes from PLAN.md (not pursued)

- **8.2 Speculative pre-soloing** of next track during current download: deferred. Solo state is shared on the page; concurrent state mutation while a download is in flight risks corrupting the in-flight mix. The 22.5s/track post-Phase-1-through-6 number is good enough that this risky change is hard to justify. Skip unless we hit hard requirements for further speedup.
- **8.4 Wire `--profile` into CI**: deferred. The user runs this tool manually; CI is overkill. The existing `PerformanceBaselineTester` already supports A/B comparisons for ad-hoc regression checks.
