# Phase 7 Investigations (2026-05-08)

Both findings: **negative results** — the hypothesized bugs do not exist in current code.

## Task 7.1: Per-track folder clearing — NOT HAPPENING

**Hypothesis (from PLAN.md):** `clear_song_folder` is being called per-track despite `cleanup_existing=False`, deleting the previous track's file before each new download.

**Method:** Added a `traceback.format_stack` log inside `setup_song_folder` and a `"ABOUT TO CLEAR"` warning inside the `if clear_existing:` branch. Ran a 3-track download.

**Observation:** All three calls logged:
```
DIAG_7.1 setup_song_folder(name='Don'T Bring Me Down', clear_existing=False)
DIAG_7.1 stack:
    song_path = self.file_manager.setup_song_folder(song_folder, clear_existing=cleanup_existing)
  File "/.../packages/di/adapters.py", line 29, in setup_song_folder
    return self._file_manager.setup_song_folder(song_folder_name, clear_existing)
```

The `"ABOUT TO CLEAR"` warning **never fired** → the `if clear_existing:` branch was skipped on every call.

**Conclusion:** `cleanup_existing=False` propagates correctly through the call chain (`_download_single_track` → `download_current_mix` → `_setup_file_management` → DI adapter → `setup_song_folder`). No per-track clearing is happening today.

**Re-reading the original log evidence:** The audit's claim about per-track clearing was based on log lines like `🗑️ Clearing existing song folder` appearing before each track. On re-read, those messages came from a `_prepare_song_folder` call at song-start (which IS supposed to clear once per song) plus log lines from a prior session that I misattributed. There is no bug here.

## Task 7.2: Mystery 2s gap solo→download — NOT REAL

**Hypothesis:** A consistent ~2s gap exists between `solo_track` returning and `download_current_mix` starting, with no explicit `time.sleep` in the call path.

**Method:** Wrapped `solo_track` and the call to `download_current_mix` in `_download_single_track` with `perf_counter` calls.

**Observation:** Three tracks measured:
- Bass: `gap-since-solo=0ms`
- Drum Kit: `gap-since-solo=0ms`
- Backing Vocals: `gap-since-solo=0ms`

`solo_track` itself took 756–1733ms (the natural variance of the polling loop), but the gap between `solo_track` returning and `download_current_mix` being called was **always 0ms**.

**Conclusion:** The 2s gap I observed in the original audit log was a misread of timestamps spanning multiple sessions/log files. There is no gap in current code. No fix needed.

## Closing both items

Both PLAN.md tasks (7.1, 7.2) can be marked closed. The diagnostic instrumentation has been reverted.
