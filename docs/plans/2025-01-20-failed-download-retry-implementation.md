# Failed Download Retry System - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two-tier retry system for failed track downloads with failure summary at end of run.

**Architecture:** Track failures in a list with attempt counters. Retry at song-level (Tier 1), then globally (Tier 2). Display minimal summary of permanent failures.

**Tech Stack:** Python, existing KaraokeVersionAutomator class

---

## Task 1: Add Failed Downloads Data Structure

**Files:**
- Modify: `karaoke_automator.py:34` (in `__init__`)

**Step 1: Add failed_downloads list to __init__**

In `karaoke_automator.py`, find line ~49 where `self.stats = StatsReporter()` is defined. Add the new list after it:

```python
        self.stats = StatsReporter()  # Always track stats
        self.failed_downloads = []  # Track failures for retry
```

**Step 2: Verify syntax**

Run: `python -m py_compile karaoke_automator.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add karaoke_automator.py
git commit -m "feat: add failed_downloads list for retry tracking"
```

---

## Task 2: Add _record_failed_download Method

**Files:**
- Modify: `karaoke_automator.py` (add method after `_download_single_track`)

**Step 1: Add the method**

Add after `_download_single_track` method (around line 290):

```python
    def _record_failed_download(self, song, track, reason):
        """Record a failed download for later retry

        Args:
            song (dict): Song configuration with url, name, key
            track (dict): Track info with name and index
            reason (str): Failure reason for logging
        """
        self.failed_downloads.append({
            'song': song,
            'track': track,
            'attempt': 1,
            'reason': reason
        })
        logging.info(f"📋 Queued for retry: {track['name']} (reason: {reason})")
```

**Step 2: Verify syntax**

Run: `python -m py_compile karaoke_automator.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add karaoke_automator.py
git commit -m "feat: add _record_failed_download method"
```

---

## Task 3: Modify _download_single_track to Record Failures

**Files:**
- Modify: `karaoke_automator.py:254-289` (`_download_single_track` method)

**Step 1: Update the method to record failures and return bool**

Replace the existing `_download_single_track` method:

```python
    @profile_timing("_download_single_track", "system", "method")
    def _download_single_track(self, song, track, song_key):
        """Download a single track

        Returns:
            bool: True if download succeeded, False otherwise
        """
        track_name = self.sanitize_filename(track['name'])
        success = False

        if self.progress:
            self.progress.update_track_status(track['index'], 'isolating')

        self.stats.record_track_start(song['name'], track_name, track['index'])

        # Smart solo management - only clear conflicting tracks
        logging.debug(f"Ensuring clean solo state for {track_name} (track {track['index']})")
        self.ensure_only_track_active(track['index'], song['url'])

        if self.solo_track(track, song['url']):
            try:
                success = self.download_manager.download_current_mix(
                    song['url'],
                    track_name,
                    cleanup_existing=False,
                    song_folder=song.get('name'),
                    key_adjustment=song_key,
                    track_index=track['index']
                )
            except Exception as e:
                logging.error(f"Exception during download for {track_name}: {e}")
                success = False

            if not success:
                logging.error(f"Failed to download {track_name}")
                self._record_failed_download(song, track, "Download failed")
        else:
            logging.error(f"Failed to solo track {track_name}")
            if self.progress:
                self.progress.update_track_status(track['index'], 'failed')
            self.stats.record_track_completion(song['name'], track_name, success=False,
                                             error_message="Failed to solo track")
            self._record_failed_download(song, track, "Failed to solo track")

        return success
```

**Step 2: Verify syntax**

Run: `python -m py_compile karaoke_automator.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add karaoke_automator.py
git commit -m "feat: update _download_single_track to record failures and return bool"
```

---

## Task 4: Add _retry_song_failures Method (Tier 1)

**Files:**
- Modify: `karaoke_automator.py` (add method after `_record_failed_download`)

**Step 1: Add the Tier 1 retry method**

```python
    def _retry_song_failures(self, song):
        """Tier 1: Retry failed downloads for the current song

        Called after each song completes to give failed tracks a second chance
        before moving to the next song.

        Args:
            song (dict): Song configuration
        """
        # Find failures for this song with attempt=1
        song_failures = [f for f in self.failed_downloads
                        if f['song']['url'] == song['url'] and f['attempt'] == 1]

        if not song_failures:
            return

        logging.info(f"🔄 Tier 1 Retry: {len(song_failures)} failed track(s) for {song['name']}")

        for failure in song_failures:
            # Remove from list before retry
            self.failed_downloads.remove(failure)

            track = failure['track']
            track_name = self.sanitize_filename(track['name'])
            logging.info(f"🔄 Retrying: {track_name}")

            # Re-attempt download
            success = self._attempt_track_download(song, track, song.get('key', 0))

            if not success:
                # Still failed - mark as attempt 2 for Tier 2 retry
                failure['attempt'] = 2
                self.failed_downloads.append(failure)
                logging.warning(f"⚠️ Retry failed for {track_name} - queued for final retry")
            else:
                logging.info(f"✅ Retry successful for {track_name}")
```

**Step 2: Verify syntax**

Run: `python -m py_compile karaoke_automator.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add karaoke_automator.py
git commit -m "feat: add _retry_song_failures method for Tier 1 retry"
```

---

## Task 5: Add _attempt_track_download Helper Method

**Files:**
- Modify: `karaoke_automator.py` (add method before `_retry_song_failures`)

**Step 1: Add helper method that doesn't record failures (for retries)**

```python
    def _attempt_track_download(self, song, track, song_key):
        """Attempt to download a track without recording failure

        Used by retry methods to avoid double-recording failures.

        Args:
            song (dict): Song configuration
            track (dict): Track info with name and index
            song_key (int): Key adjustment

        Returns:
            bool: True if download succeeded, False otherwise
        """
        track_name = self.sanitize_filename(track['name'])
        success = False

        if self.progress:
            self.progress.update_track_status(track['index'], 'isolating')

        # Smart solo management
        self.ensure_only_track_active(track['index'], song['url'])

        if self.solo_track(track, song['url']):
            try:
                success = self.download_manager.download_current_mix(
                    song['url'],
                    track_name,
                    cleanup_existing=False,
                    song_folder=song.get('name'),
                    key_adjustment=song_key,
                    track_index=track['index']
                )
            except Exception as e:
                logging.error(f"Exception during retry download for {track_name}: {e}")
                success = False
        else:
            logging.error(f"Failed to solo track {track_name} during retry")
            if self.progress:
                self.progress.update_track_status(track['index'], 'failed')

        return success
```

**Step 2: Verify syntax**

Run: `python -m py_compile karaoke_automator.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add karaoke_automator.py
git commit -m "feat: add _attempt_track_download helper for retry logic"
```

---

## Task 6: Add _retry_all_failures Method (Tier 2)

**Files:**
- Modify: `karaoke_automator.py` (add method after `_retry_song_failures`)

**Step 1: Add the Tier 2 final retry method**

```python
    def _retry_all_failures(self):
        """Tier 2: Final retry for all remaining failed downloads

        Called after all songs complete. Gives each remaining failure
        one final attempt before marking as permanent failure.
        """
        # Find failures with attempt=2 (already failed Tier 1)
        remaining_failures = [f for f in self.failed_downloads if f['attempt'] == 2]

        if not remaining_failures:
            return

        logging.info(f"🔄 Tier 2 Final Retry: {len(remaining_failures)} track(s) remaining")
        print(f"\n{'='*60}")
        print(f"🔄 FINAL RETRY PASS: {len(remaining_failures)} failed track(s)")
        print(f"{'='*60}\n")

        for failure in remaining_failures:
            # Remove from list before retry
            self.failed_downloads.remove(failure)

            song = failure['song']
            track = failure['track']
            track_name = self.sanitize_filename(track['name'])

            logging.info(f"🔄 Final retry: {track_name} from {song['name']}")

            # Re-attempt download
            success = self._attempt_track_download(song, track, song.get('key', 0))

            if not success:
                # Permanent failure - mark as attempt 3
                failure['attempt'] = 3
                self.failed_downloads.append(failure)
                logging.error(f"❌ Final retry failed for {track_name}")
            else:
                logging.info(f"✅ Final retry successful for {track_name}")
```

**Step 2: Verify syntax**

Run: `python -m py_compile karaoke_automator.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add karaoke_automator.py
git commit -m "feat: add _retry_all_failures method for Tier 2 final retry"
```

---

## Task 7: Add _display_failure_summary Method

**Files:**
- Modify: `karaoke_automator.py` (add method after `_retry_all_failures`)

**Step 1: Add the failure summary display method**

```python
    def _display_failure_summary(self):
        """Display summary of permanently failed downloads

        Shows minimal info for each failure: track name and song URL
        for easy manual recovery.
        """
        # Get permanent failures (attempt=3)
        permanent_failures = [f for f in self.failed_downloads if f['attempt'] == 3]

        if not permanent_failures:
            if self.show_progress:
                print("\n✅ All tracks downloaded successfully!")
            else:
                logging.info("All tracks downloaded successfully!")
            return

        # Display failure summary
        if self.show_progress:
            print(f"\n{'='*60}")
            print(f"❌ FAILED DOWNLOADS ({len(permanent_failures)} track(s)):")
            print(f"{'='*60}")
            for f in permanent_failures:
                print(f"  - {f['track']['name']} ({f['song']['url']})")
            print(f"{'='*60}\n")
        else:
            logging.error(f"Failed downloads ({len(permanent_failures)} tracks):")
            for f in permanent_failures:
                logging.error(f"  - {f['track']['name']} ({f['song']['url']})")
```

**Step 2: Verify syntax**

Run: `python -m py_compile karaoke_automator.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add karaoke_automator.py
git commit -m "feat: add _display_failure_summary method"
```

---

## Task 8: Integrate Tier 1 Retry into _process_single_song

**Files:**
- Modify: `karaoke_automator.py:204-212` (`_process_song_with_tracks` method)

**Step 1: Add Tier 1 retry call after track downloads**

Find `_process_song_with_tracks` method and add the retry call:

```python
    def _process_song_with_tracks(self, song, tracks, song_key):
        """Process a song that has available tracks"""
        logging.info(f"Found {len(tracks)} tracks for {song['name']}")

        self._start_song_tracking(song, tracks)
        self._setup_mixer_controls(song, song_key)
        self._prepare_song_folder(song)
        self._download_all_tracks(song, tracks, song_key)

        # Tier 1: Retry any failures for this song
        self._retry_song_failures(song)

        self._finish_song_processing(song)
```

**Step 2: Verify syntax**

Run: `python -m py_compile karaoke_automator.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add karaoke_automator.py
git commit -m "feat: integrate Tier 1 retry into song processing"
```

---

## Task 9: Integrate Tier 2 Retry and Summary into run_automation

**Files:**
- Modify: `karaoke_automator.py:128-162` (`run_automation` method)

**Step 1: Add Tier 2 retry and failure summary**

Update `run_automation` method to add retry and summary before final reports:

```python
    @profile_timing("run_automation", "system", "system")
    def run_automation(self):
        """Run complete automation workflow"""
        try:
            if not self._setup_automation_session():
                return False

            songs = self.load_songs_config()
            if not songs:
                logging.error("No songs configured")
                return False

            logging.info(f"Processing {len(songs)} songs...")

            for song in songs:
                self._process_single_song(song)

            logging.info("Automation completed")

            # Tier 2: Final retry for any remaining failures
            if self.failed_downloads:
                self._retry_all_failures()

            # Display failure summary
            self._display_failure_summary()

            # Run final cleanup pass to catch any files that weren't cleaned up
            try:
                logging.info("🧹 Running final cleanup pass...")
                self.file_manager.final_cleanup_pass()
            except Exception as e:
                logging.error(f"Error during final cleanup pass: {e}")

            self._generate_final_reports()
            return True

        except Exception as e:
            logging.error(f"Automation failed: {e}")
            self._display_failure_summary()  # Show failures even on error
            self._generate_final_reports(failed=True)
            return False
        finally:
            pass
```

**Step 2: Verify syntax**

Run: `python -m py_compile karaoke_automator.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add karaoke_automator.py
git commit -m "feat: integrate Tier 2 retry and failure summary into run_automation"
```

---

## Task 10: Manual Integration Test

**Step 1: Run a quick test with --debug flag**

Run: `python karaoke_automator.py --debug --max-tracks 2`

**Step 2: Verify the retry system**

Check that:
- No Python errors occur
- If a track fails, it shows "Queued for retry" message
- After song completes, "Tier 1 Retry" message appears (if there were failures)
- At the end, either "All tracks downloaded successfully!" or failure summary appears

**Step 3: Final commit if needed**

If any fixes were needed, commit them:
```bash
git add karaoke_automator.py
git commit -m "fix: address integration issues in retry system"
```

---

## Summary

**Files modified:**
- `karaoke_automator.py`

**New methods added:**
1. `_record_failed_download()` - Queue failed track for retry
2. `_attempt_track_download()` - Download helper for retries (no failure recording)
3. `_retry_song_failures()` - Tier 1 retry after each song
4. `_retry_all_failures()` - Tier 2 final retry
5. `_display_failure_summary()` - Show permanent failures

**Modified methods:**
1. `__init__` - Add `self.failed_downloads = []`
2. `_download_single_track()` - Record failures, return bool
3. `_process_song_with_tracks()` - Call Tier 1 retry
4. `run_automation()` - Call Tier 2 retry and display summary
