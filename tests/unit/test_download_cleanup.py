#!/usr/bin/env python3
"""
Test download cleanup functionality
Validates that existing files are removed before new downloads
"""

import time
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.configuration import DOWNLOAD_FOLDER
from packages.file_operations.file_manager import FileManager


def _create_aged_test_files(folder, filenames, age_seconds=60):
    """Create files in folder with mtime aged past the cleanup safety guard."""
    folder = Path(folder)
    folder.mkdir(exist_ok=True)
    aged_mtime = time.time() - age_seconds
    created = []
    for filename in filenames:
        file_path = folder / filename
        file_path.write_text("test content")
        os.utime(file_path, (aged_mtime, aged_mtime))
        created.append(file_path)
        print(f"Created test file: {filename}")
    return created


def test_download_cleanup():
    """Test that the cleanup helper removes matching/backing-track files
    while preserving unrelated files."""
    print("🧹 TESTING DOWNLOAD CLEANUP FUNCTIONALITY")
    print("Testing removal of existing files before new downloads")
    print("="*60)

    download_folder = Path(DOWNLOAD_FOLDER)

    # Files: bass_cleanup_test (matches), *_backing_track_*.mp3 (suffix match —
    # the cleanup helper looks for the literal substrings 'custom_backing_track'
    # or 'backing_track'), unrelated_song.mp3 (no token overlap, no suffix →
    # preserved).
    target_track = "bass_cleanup_test"
    test_filenames = [
        "bass_cleanup_test.mp3",                                  # matches track tokens
        "jimmy_eat_world_the_middle_custom_backing_track.mp3",    # backing-track suffix
        "unrelated_song.mp3",                                     # preserved
    ]

    created = _create_aged_test_files(download_folder, test_filenames)
    try:
        file_manager = FileManager()
        file_manager.cleanup_existing_downloads(target_track, download_folder)

        remaining = {f.name for f in created if f.exists()}
        removed = {f.name for f in created if not f.exists()}

        print(f"📊 Cleanup results:")
        print(f"  Files before:  {len(created)}")
        print(f"  Files removed: {len(removed)} ({sorted(removed)})")
        print(f"  Files left:    {len(remaining)} ({sorted(remaining)})")

        assert "bass_cleanup_test.mp3" in removed, (
            "Track-name match should have been cleaned"
        )
        assert "jimmy_eat_world_the_middle_custom_backing_track.mp3" in removed, (
            "Backing-track-suffixed file should have been cleaned"
        )
        assert "unrelated_song.mp3" in remaining, (
            "Unrelated file (no token overlap, no backing-track suffix) "
            "should not have been removed"
        )

        # Files newer than the 30s safety guard must NOT be removed even when
        # they match the track name — this avoids deleting active downloads.
        recent_match = download_folder / f"{target_track}_recent.mp3"
        recent_match.write_text("recent")  # mtime = now
        try:
            file_manager.cleanup_existing_downloads(target_track, download_folder)
            assert recent_match.exists(), (
                "Recent (<30s old) matching file was removed; the safety guard "
                "must protect in-progress downloads"
            )
            print("✅ Safety guard preserved a fresh file matching the track name")
        finally:
            if recent_match.exists():
                recent_match.unlink()

    finally:
        for file_path in created:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass

def test_cleanup_patterns():
    """Test pattern matching: only files that match the track tokens (or carry
    the backing-track suffix) and that are older than the 30s safety guard
    should be removed."""
    print("\n🔍 TESTING CLEANUP PATTERNS AND SAFETY")
    print("Testing pattern matching and file age safety checks")
    print("="*50)

    download_folder = Path(DOWNLOAD_FOLDER)
    download_folder.mkdir(exist_ok=True)
    current_time = time.time()

    # (filename, age_seconds, expected_removed)
    # cleanup target is "bass_track" → tokens {"bass", "track"}.
    test_scenarios = [
        ("bass_track_aged.mp3",       60,    True),   # matches token, aged → removed
        ("bass_track_recent.mp3",     0,     False),  # matches token, fresh → preserved by safety guard
        ("important_backup.mp3",      60,    False),  # no token overlap, no suffix → preserved
        ("song_x_custom_backing_track.mp3",  60,    True),   # backing-track suffix, aged → removed
        ("old_unrelated.mp3",         7200,  False),  # 2h old but no token/suffix match → preserved
    ]

    created_files = []
    for filename, age_seconds, _expected in test_scenarios:
        file_path = download_folder / filename
        file_path.write_text("test content")
        old_time = current_time - age_seconds
        os.utime(file_path, (old_time, old_time))
        created_files.append((file_path, age_seconds))
        print(f"Created: {filename} (age: {age_seconds/3600:.2f}h)")

    try:
        file_manager = FileManager()

        print("\n🧹 Testing cleanup patterns...")
        file_manager.cleanup_existing_downloads("bass_track", download_folder)

        actual_removed = {fp.name for fp, _ in created_files if not fp.exists()}
        actual_preserved = {fp.name for fp, _ in created_files if fp.exists()}

        print(f"\n📊 Pattern cleanup results:")
        print(f"Files removed:   {sorted(actual_removed)}")
        print(f"Files preserved: {sorted(actual_preserved)}")

        violations = []
        for filename, age_seconds, expected_removed in test_scenarios:
            was_removed = filename in actual_removed
            if was_removed != expected_removed:
                violations.append(
                    f"{filename} (age={age_seconds}s): expected "
                    f"{'removed' if expected_removed else 'preserved'}, "
                    f"got {'removed' if was_removed else 'preserved'}"
                )

        assert not violations, (
            "Cleanup pattern violations:\n  - " + "\n  - ".join(violations)
        )

    finally:
        for file_path, _ in created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass

if __name__ == "__main__":
    print("🧹 DOWNLOAD CLEANUP FUNCTIONALITY TESTS")
    print("="*60)

    failures = []
    for name, fn in [
        ("Basic Cleanup", test_download_cleanup),
        ("Pattern Safety", test_cleanup_patterns),
    ]:
        try:
            fn()
            print(f"{name}: SUCCESS")
        except AssertionError as e:
            failures.append((name, e))
            print(f"{name}: FAILED — {e}")

    print("="*60)
    sys.exit(0 if not failures else 1)