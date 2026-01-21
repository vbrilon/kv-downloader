# Failed Download Retry & Summary System

## Overview

Add a two-tier retry system for failed track downloads, with a clear failure summary at the end of each run.

## Requirements

1. **Tier 1 Retry**: After each song completes, retry that song's failed tracks
2. **Tier 2 Retry**: After all songs complete, retry any still-failing tracks one final time
3. **Failure Summary**: Display minimal summary of permanent failures (track name + URL)

## Data Structure

Track failed downloads in `KaraokeVersionAutomator`:

```python
# In __init__
self.failed_downloads = []

# Each failure entry
{
    'song': {'url': '...', 'name': '...', 'key': 0},
    'track': {'name': 'Bass', 'index': 2},
    'attempt': 1,  # 1=first fail, 2=song retry fail, 3=final retry fail
    'reason': 'Download timeout'
}
```

## Retry Flow

```
For each song:
    1. Download all tracks (existing logic)
    2. Collect failures → failed_downloads list
    3. Tier 1: Retry song's failures
       - Pop song's failures from list
       - Attempt each once
       - Re-add to list if still fails (attempt=2)

After all songs:
    4. Tier 2: Final retry pass
       - Process remaining failures (attempt=2)
       - Attempt each once
       - Mark as permanent failure if still fails (attempt=3)

    5. Display failure summary
       - Show any tracks with attempt=3
       - Minimal format: track name + URL
```

## New Methods

### `_record_failed_download(self, song, track, reason)`

Add a failed download to the retry queue.

### `_retry_song_failures(self, song)`

Tier 1: Retry failures for the current song immediately after it completes.

### `_retry_all_failures(self)`

Tier 2: Final retry for all remaining failures after all songs complete.

### `_display_failure_summary(self)`

Show permanent failures in minimal format:
```
Failed Downloads (2 tracks):
  - Bass (https://karaoke-version.com/.../song.html)
  - Drums (https://karaoke-version.com/.../song.html)
```

## Integration Points

### `__init__`
- Add `self.failed_downloads = []`

### `_download_single_track`
- Return `bool` success/failure
- Call `_record_failed_download()` on failure

### `_process_single_song`
- Call `_retry_song_failures(song)` after `_download_all_tracks()`

### `run_automation`
- Call `_retry_all_failures()` after song loop (if failures exist)
- Call `_display_failure_summary()` before final reports

## Design Decisions

1. **Reuse existing download logic** - `_download_single_track()` handles retries the same as first attempts
2. **Remove-then-readd pattern** - Prevents duplicate entries in failure list
3. **Attempt counter** - Prevents infinite retry loops, enables filtering by retry tier
4. **Minimal summary format** - Just track name + URL for easy manual recovery
