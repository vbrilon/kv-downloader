#!/usr/bin/env python3
"""
Test song-specific folder creation and organization
Validates that downloads are organized into song-specific folders
"""

import time
import sys
import os
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator
from packages.configuration import DOWNLOAD_FOLDER


@pytest.mark.live
def test_song_folder_extraction():
    """Test extracting song information from URLs"""
    print("📁 TESTING SONG FOLDER EXTRACTION")
    print("Testing URL parsing and folder name generation")
    print("="*60)

    automator = None
    try:
        try:
            automator = KaraokeVersionAutomator(headless=True)
        except Exception as e:
            pytest.skip(f"Could not initialize KaraokeVersionAutomator: {e}")

        test_cases = [
            {
                'url': 'https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html',
                'expected_song': 'The Middle',
                'expected_artist': 'Jimmy Eat World'
            },
            {
                'url': 'https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html',
                'expected_song': 'Pink Pony Club',
                'expected_artist': 'Chappell Roan'
            },
            {
                'url': 'https://www.karaoke-version.com/custombackingtrack/taylor-swift/shake-it-off.html',
                'expected_song': 'Shake It Off',
                'expected_artist': 'Taylor Swift'
            }
        ]

        failures = []

        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}️⃣ Testing URL: {test_case['url']}")

            folder_name = automator.download_manager.extract_song_folder_name(test_case['url'])
            print(f"   Generated folder: '{folder_name}'")

            folder_normalized = folder_name.lower().replace(' ', '').replace('-', '')
            song_normalized = test_case['expected_song'].lower().replace(' ', '').replace('-', '')
            artist_normalized = test_case['expected_artist'].lower().replace(' ', '').replace('-', '')

            song_only_match = song_normalized in folder_normalized and artist_normalized not in folder_normalized
            full_match = song_normalized in folder_normalized and artist_normalized in folder_normalized

            if song_only_match or full_match:
                format_type = "song-only" if song_only_match else "artist-song"
                print(f"   ✅ Valid folder name ({format_type} format)")
            else:
                failures.append(
                    f"{test_case['url']}: generated {folder_name!r}, expected to contain "
                    f"{test_case['expected_song']!r}"
                )
                print(f"   ❌ Invalid folder name (expected song: '{test_case['expected_song']}')")

        print(f"\n📊 URL Extraction Results: {len(test_cases) - len(failures)}/{len(test_cases)} successful")
        assert not failures, "Folder extraction failures:\n  - " + "\n  - ".join(failures)

    finally:
        if automator is not None:
            try:
                automator.driver.quit()
            except Exception:
                pass

def _driver_is_alive(driver):
    """Return True if the ChromeDriver session is still responsive."""
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


@pytest.mark.live
def test_song_folder_creation():
    """Test actual song folder creation and download organization."""
    from selenium.common.exceptions import WebDriverException

    print("\n📂 TESTING SONG FOLDER CREATION")
    print("Testing folder creation and download organization")
    print("="*60)

    automator = None
    try:
        try:
            automator = KaraokeVersionAutomator(headless=True)
        except Exception as e:
            pytest.skip(f"Could not initialize KaraokeVersionAutomator: {e}")

        try:
            login_ok = automator.login()
        except Exception as e:
            pytest.skip(f"Live login raised an exception: {e}")
        if not login_ok:
            pytest.skip("Live login to karaoke-version.com failed (credentials/network)")
        print("✅ Login successful")

        song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
        try:
            tracks = automator.get_available_tracks(song_url)
        except Exception as e:
            pytest.skip(f"Track discovery raised an exception: {e}")
        assert tracks, f"No tracks found at {song_url}"
        print(f"✅ Found {len(tracks)} tracks")

        bass_tracks = [t for t in tracks if 'bass' in t['name'].lower()]
        assert bass_tracks, "No bass track found in track list"
        bass_track = bass_tracks[0]
        print(f"🎸 Using bass track: {bass_track['name']}")

        try:
            soloed = automator.solo_track(bass_track, song_url)
        except WebDriverException as e:
            pytest.skip(f"WebDriver lost while soloing track: {e}")
        if not soloed and not _driver_is_alive(automator.driver):
            pytest.skip("Chrome session died during solo — treating as environmental")
        assert soloed, f"solo_track failed for {bass_track['name']}"
        print("✅ Bass track soloed")

        print("📁 Testing download with song folder...")
        time.sleep(2)  # Wait for UI update

        # track_index is required so the manager skips the legacy fallback path
        # that relies on a `tracks` attribute the DI ProgressTrackerAdapter does
        # not expose. track_name must match the soloed track because the
        # download manager verifies the active selection before downloading.
        try:
            auto_ok = automator.download_manager.download_current_mix(
                song_url,
                track_name=bass_track['name'],
                cleanup_existing=True,
                song_folder=None,  # auto-extract
                track_index=bass_track['index'],
            )
        except WebDriverException as e:
            pytest.skip(f"WebDriver lost during auto-folder download: {e}")
        if not auto_ok and not _driver_is_alive(automator.driver):
            pytest.skip("Chrome session died during download — treating as environmental")
        assert auto_ok, "download_current_mix returned False (auto-extracted folder)"
        print("✅ Download initiated with song folder")

        base_download_folder = Path(DOWNLOAD_FOLDER)
        song_folders = [f for f in base_download_folder.iterdir() if f.is_dir()]

        print(f"\n📊 Song folder creation results:")
        print(f"Base download folder: {base_download_folder}")
        print(f"Created folders: {len(song_folders)}")
        for folder in song_folders:
            print(f"  📁 {folder.name}")

        middle_folders = [
            f for f in song_folders
            if 'middle' in f.name.lower()
            or ('jimmy' in f.name.lower() and 'eat' in f.name.lower())
        ]
        assert middle_folders, (
            f"Auto-extracted song folder for The Middle not found in {base_download_folder}; "
            f"existing folders: {[f.name for f in song_folders]}"
        )
        print(f"✅ Found song folder: {middle_folders[0].name}")

        print("\n📂 Testing custom folder name...")
        try:
            custom_ok = automator.download_manager.download_current_mix(
                song_url,
                track_name=bass_track['name'],
                cleanup_existing=False,
                song_folder="Custom Test Folder",
                track_index=bass_track['index'],
            )
        except WebDriverException as e:
            pytest.skip(f"WebDriver lost during custom-folder download: {e}")
        if not custom_ok and not _driver_is_alive(automator.driver):
            pytest.skip("Chrome session died during custom-folder download — treating as environmental")
        assert custom_ok, "download_current_mix returned False (custom folder)"
        custom_folder = base_download_folder / "Custom Test Folder"
        assert custom_folder.exists(), (
            f"Custom folder {custom_folder} was not created during download"
        )
        print(f"✅ Custom folder created: {custom_folder.name}")

    finally:
        if automator is not None:
            try:
                automator.driver.quit()
            except Exception:
                pass

@pytest.mark.live
def test_folder_cleanup_integration():
    """Test that cleanup works correctly within song folders.

    cleanup_existing_downloads only removes files older than 30 seconds (a guard
    against deleting in-progress downloads), so the test files are aged past
    that threshold via os.utime before invoking cleanup.
    """
    print("\n🧹 TESTING FOLDER CLEANUP INTEGRATION")
    print("Testing cleanup functionality within song-specific folders")
    print("="*60)

    base_download_folder = Path(DOWNLOAD_FOLDER)
    base_download_folder.mkdir(exist_ok=True)
    test_song_folder = base_download_folder / "Test Song Folder"
    test_song_folder.mkdir(exist_ok=True)

    # cleanup_existing_downloads matches files whose names contain ANY token of
    # the track name (split on '_'). For track_name="bass_solo" the matching
    # tokens are {"bass", "solo"}. We pick a preserved file whose name shares
    # no token with the track name and lacks the backing-track suffix.
    test_files = [
        "bass_solo.mp3",                       # matches token "bass"/"solo" → cleaned
        "piano.mp3",                           # no shared token, no suffix  → preserved
        "old_custom_backing_track_file.mp3",   # has backing_track suffix    → cleaned
    ]

    created_files = []
    aged_mtime = time.time() - 60  # 60s ago, past the 30s safety threshold
    for filename in test_files:
        file_path = test_song_folder / filename
        file_path.write_text("test content")
        os.utime(file_path, (aged_mtime, aged_mtime))
        created_files.append(file_path)

    print(f"📁 Created {len(test_files)} test files in: {test_song_folder.name}")

    from packages.file_operations.file_manager import FileManager
    file_manager = FileManager()

    try:
        file_manager.cleanup_existing_downloads("bass_solo", test_song_folder)

        remaining = [f.name for f in created_files if f.exists()]
        removed = [f.name for f in created_files if not f.exists()]

        print(f"📊 Cleanup results in song folder:")
        print(f"  Files before:    {len(created_files)}")
        print(f"  Files removed:   {len(removed)} ({removed})")
        print(f"  Files remaining: {len(remaining)} ({remaining})")

        assert "bass_solo.mp3" not in remaining, (
            "bass_solo.mp3 was not cleaned despite matching the bass_solo track name"
        )
        assert "old_custom_backing_track_file.mp3" not in remaining, (
            "Backing-track-suffixed file was not cleaned"
        )
        assert "piano.mp3" in remaining, (
            "piano.mp3 was incorrectly removed; cleanup should not affect files "
            "that share no token with the track name"
        )

    finally:
        try:
            if test_song_folder.exists():
                for file_path in test_song_folder.iterdir():
                    file_path.unlink()
                test_song_folder.rmdir()
                print(f"🧹 Cleaned up test folder: {test_song_folder.name}")
        except Exception:
            pass

def test_apostrophe_titlecase_in_generated_names():
    """Folder names from URLs must NOT capitalize letters after apostrophes.

    Regression: str.title() treats apostrophes as word boundaries, so it would
    turn "don't" into "Don'T". We use string.capwords (split on whitespace only)
    so contractions render correctly.
    """
    from packages.configuration.config_manager import ConfigurationManager
    cm = ConfigurationManager()

    # Song-only mode (typical case when names don't conflict)
    name = cm._generate_name_from_url(
        "https://www.karaoke-version.com/custombackingtrack/electric-light-orchestra/don-t-bring-me-down.html"
    )
    assert name == "Don't Bring Me Down", f"Expected 'Don't Bring Me Down', got {name!r}"

    # Same with several other contractions to lock the behavior
    cases = [
        ("https://www.karaoke-version.com/custombackingtrack/billie-eilish/i-m-not-ok.html",
         "I'm Not Ok"),
        ("https://www.karaoke-version.com/custombackingtrack/the-temptations/it-s-getting-better.html",
         "It's Getting Better"),
        ("https://www.karaoke-version.com/custombackingtrack/queen/we-re-the-champions.html",
         "We're The Champions"),
    ]
    for url, expected in cases:
        got = cm._generate_name_from_url(url)
        assert got == expected, f"For {url}: expected {expected!r}, got {got!r}"

    # Artist-mode (when conflicts force include_artist=True): apostrophe handling
    # must work in both halves of the "Artist - Song" string.
    artist_song = cm._generate_name_from_url(
        "https://www.karaoke-version.com/custombackingtrack/d-angelo/don-t-leave-me.html",
        include_artist=True,
    )
    # Only assert that the song half doesn't have "Don'T"
    assert "Don't" in artist_song, f"Song half should be 'Don't', got {artist_song!r}"
    assert "Don'T" not in artist_song, f"Got the title()-style miscapitalization: {artist_song!r}"


def test_cleanup_partial_downloads_removes_only_crdownload(tmp_path, monkeypatch):
    """cleanup_partial_downloads must wipe .crdownload files but leave .mp3
    files intact (so re-runs can skip already-completed tracks)."""
    from packages.file_operations.file_manager import FileManager
    import packages.configuration.config as cfg

    monkeypatch.setattr(cfg, 'DOWNLOAD_FOLDER', str(tmp_path))

    song_dir = tmp_path / "Test Song"
    song_dir.mkdir()
    (song_dir / "Bass.mp3").write_bytes(b"x" * 100)              # finished
    (song_dir / "Drum Kit.mp3").write_bytes(b"x" * 100)          # finished
    (song_dir / "Piano.mp3.crdownload").write_bytes(b"y" * 50)   # partial
    (song_dir / "Vocal.mp3.crdownload").write_bytes(b"y" * 50)   # partial

    FileManager().cleanup_partial_downloads("Test Song")

    remaining = sorted(p.name for p in song_dir.iterdir())
    assert remaining == ["Bass.mp3", "Drum Kit.mp3"], f"Got {remaining}"


def test_cleanup_partial_downloads_handles_missing_folder(tmp_path, monkeypatch):
    """Not an error if the song folder doesn't exist yet."""
    from packages.file_operations.file_manager import FileManager
    import packages.configuration.config as cfg

    monkeypatch.setattr(cfg, 'DOWNLOAD_FOLDER', str(tmp_path))
    # Should not raise
    FileManager().cleanup_partial_downloads("Nonexistent Song")


def test_track_file_already_exists(tmp_path, monkeypatch):
    """_track_file_already_exists checks the right path: <DOWNLOAD_FOLDER>/<song name>/<track>.mp3."""
    import packages.configuration.config as cfg
    monkeypatch.setattr(cfg, 'DOWNLOAD_FOLDER', str(tmp_path))

    # Build only the parts of KaraokeVersionAutomator we need — full init wants a real driver.
    from karaoke_automator import KaraokeVersionAutomator
    automator = KaraokeVersionAutomator.__new__(KaraokeVersionAutomator)
    # download_manager.extract_song_folder_name is the fallback; not used here
    # because song['name'] is set.
    automator.download_manager = None

    song = {'name': 'Test Song', 'url': 'https://example.com/song'}
    (tmp_path / "Test Song").mkdir()
    (tmp_path / "Test Song" / "Bass.mp3").write_bytes(b"x" * 100)

    assert automator._track_file_already_exists(song, "Bass") is True
    assert automator._track_file_already_exists(song, "Drum Kit") is False


if __name__ == "__main__":
    print("📁 SONG FOLDER FUNCTIONALITY TESTS")
    print("="*60)

    failures = []
    for name, fn in [
        ("URL Extraction", test_song_folder_extraction),
        ("Folder Creation", test_song_folder_creation),
        ("Cleanup Integration", test_folder_cleanup_integration),
    ]:
        try:
            fn()
            print(f"{name}: SUCCESS")
        except (AssertionError, pytest.skip.Exception) as e:
            failures.append((name, e))
            print(f"{name}: FAILED — {e}")

    print("="*60)
    sys.exit(0 if not failures else 1)