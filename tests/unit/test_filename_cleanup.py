#!/usr/bin/env python3
"""
Test filename cleanup functionality
Validates removal of "_Custom_Backing_Track" and similar suffixes
"""

import time
import sys
import tempfile
from pathlib import Path
import unittest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionTracker

class TestFilenameCleanup(unittest.TestCase):
    """Test filename cleanup functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.tracker = KaraokeVersionTracker(None, None)  # Mock driver/wait
    
    def tearDown(self):
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, filename):
        """Create a test file with current timestamp"""
        file_path = self.temp_path / filename
        file_path.write_text("test mp3 content")
        return file_path
    
    def test_custom_backing_track_removal(self):
        """Test removal of '_Custom_Backing_Track' suffix"""
        test_cases = [
            ("Jimmy_Eat_World_The_Middle(Bass_Custom_Backing_Track).mp3", 
             "Jimmy_Eat_World_The_Middle(Bass).mp3"),
            ("Taylor_Swift_Shake_It_Off_Vocals_Custom_Backing_Track.mp3",
             "Taylor_Swift_Shake_It_Off_Vocals.mp3"),
            ("Song_Name_Guitar_Custom_Backing_Track_.mp3",
             "Song_Name_Guitar.mp3"),
            ("Artist_Song(Custom_Backing_Track).mp3",
             "Artist_Song.mp3"),
            ("Normal_File.mp3",
             "Normal_File.mp3")  # Should not change
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                # Create test file
                self.create_test_file(original)
                
                # Run cleanup
                result = self.tracker._cleanup_downloaded_filenames(self.temp_path, "test")
                
                # Check if file was renamed correctly
                expected_path = self.temp_path / expected
                original_path = self.temp_path / original
                
                if original != expected:
                    self.assertTrue(expected_path.exists(), f"Expected file {expected} was not created")
                    self.assertFalse(original_path.exists(), f"Original file {original} still exists")
                    self.assertTrue(result, "Cleanup should return True when files are renamed")
                else:
                    self.assertTrue(original_path.exists(), f"File {original} should remain unchanged")
    
    def test_multiple_pattern_cleanup(self):
        """Test cleanup of files with multiple unwanted patterns"""
        test_cases = [
            ("Song__Name__Custom_Backing_Track__.mp3", "Song_Name.mp3"),
            ("Artist--Song--(Custom_Backing_Track).mp3", "Artist-Song.mp3"),
            ("File().mp3", "File.mp3"),
            ("Name_Custom_Backing_Track_Custom_Backing_Track.mp3", "Name.mp3")
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                self.create_test_file(original)
                self.tracker._cleanup_downloaded_filenames(self.temp_path, "test")
                
                expected_path = self.temp_path / expected
                self.assertTrue(expected_path.exists(), f"Expected cleaned file {expected}")
    
    def test_file_age_filtering(self):
        """Test that only recent files are processed"""
        # Create an old file (simulate by setting old timestamp)
        old_file = self.create_test_file("Old_File_Custom_Backing_Track.mp3")
        
        # Set file to be 2 hours old
        old_time = time.time() - 7200  # 2 hours ago
        old_file.touch(times=(old_time, old_time))
        
        # Create a new file
        new_file = self.create_test_file("New_File_Custom_Backing_Track.mp3")
        
        # Run cleanup
        self.tracker._cleanup_downloaded_filenames(self.temp_path, "test")
        
        # Old file should not be renamed
        self.assertTrue(old_file.exists(), "Old file should not be renamed")
        
        # New file should be renamed
        expected_new = self.temp_path / "New_File.mp3"
        self.assertTrue(expected_new.exists(), "New file should be renamed")
    
    def test_duplicate_name_handling(self):
        """Test handling of duplicate filenames"""
        # Create existing target file
        existing_file = self.create_test_file("Song_Guitar.mp3")
        
        # Create file that would rename to same name
        duplicate_source = self.create_test_file("Song_Guitar_Custom_Backing_Track.mp3")
        
        # Run cleanup
        self.tracker._cleanup_downloaded_filenames(self.temp_path, "test")
        
        # Original should remain
        self.assertTrue(existing_file.exists(), "Existing file should remain")
        
        # Duplicate should be renamed with counter
        expected_duplicate = self.temp_path / "Song_Guitar_1.mp3"
        self.assertTrue(expected_duplicate.exists(), "Duplicate should be renamed with counter")
    
    def test_edge_cases(self):
        """Test edge cases and malformed filenames"""
        test_cases = [
            ("_Custom_Backing_Track.mp3", ".mp3"),  # Only suffix
            ("Custom_Backing_Track_.mp3", ".mp3"),  # Starts with suffix  
            (".mp3_Custom_Backing_Track.mp3", ".mp3"),  # Extension in middle
            ("File_Custom_Backing_Track", "File.mp3"),  # Missing extension
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                self.create_test_file(original)
                self.tracker._cleanup_downloaded_filenames(self.temp_path, "test")
                
                expected_path = self.temp_path / expected
                self.assertTrue(expected_path.exists(), f"Expected cleaned file {expected}")
    
    def test_click_track_filename_bug(self):
        """Test for click track filename bug - should not have key adjustment"""
        test_cases = [
            # Bug case: Click track getting key adjustment when it shouldn't
            ("(-1)_Intro count      Click.mp3", "Intro count Click.mp3"),
            ("(+2)_Intro count Click.mp3", "Intro count Click.mp3"),
            ("Intro count      Click.mp3", "Intro count Click.mp3"),  # Fix extra spaces
            ("(-1)Intro_count_Click_Custom_Backing_Track.mp3", "Intro count Click.mp3"),
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                self.create_test_file(original)
                # Special handling for click tracks - they should not get key adjustments
                # The bug is that key adjustment is being applied to click tracks when it shouldn't be
                result_path = self.tracker._clean_filename_after_download(
                    self.temp_path / original, 
                    track_name="Intro count Click",
                    key_adjustment=0  # Click tracks should always have key_adjustment=0
                )
                
                # Check that the result file has the expected name
                self.assertEqual(result_path.name, expected, f"Expected cleaned filename {expected}, got {result_path.name}")
                self.assertTrue(result_path.exists(), f"Expected cleaned file {expected} to exist")
                # Original file should be gone (renamed)
                original_path = self.temp_path / original
                if original != expected:  # Only check if names actually changed
                    self.assertFalse(original_path.exists(), f"Original file {original} should be removed")
    
    def test_missing_instrument_names_bug(self):
        """Test for missing instrument names in filenames"""
        test_cases = [
            # Bug case: Missing instrument names, showing full song name instead
            ("Jimmy_Eat_World_The_Middle(Custom_Backing_Track-1).mp3", "Bass(-1).mp3"),
            ("Jimmy_Eat_World_The_Middle_Custom_Backing_Track.mp3", "Bass.mp3"),
            ("Chappell_Roan_Pink_Pony_Club(Custom_Backing_Track+2).mp3", "Vocals(+2).mp3"),
            ("Artist_Song_Name_Custom_Backing_Track_.mp3", "Guitar.mp3"),
        ]
        
        track_names = ["Bass", "Bass", "Vocals", "Guitar"]
        key_adjustments = [-1, 0, 2, 0]
        
        for i, (original, expected) in enumerate(test_cases):
            with self.subTest(original=original):
                # Set up folder structure to simulate song folder
                song_folder = self.temp_path / "Jimmy Eat World_The Middle"
                song_folder.mkdir(exist_ok=True)
                
                # Create file in song folder
                original_file = song_folder / original
                original_file.write_text("test mp3 content")
                
                # Use clean filename method with proper track name and key adjustment
                result_path = self.tracker._clean_filename_after_download(
                    original_file,
                    track_name=track_names[i],
                    key_adjustment=key_adjustments[i]
                )
                
                # Check that the result file has the expected name
                self.assertEqual(result_path.name, expected, f"Expected cleaned filename {expected}, got {result_path.name}")
                self.assertTrue(result_path.exists(), f"Expected cleaned file {expected} to exist")
                # Original file should be gone (renamed) if names changed
                if original != expected:
                    self.assertFalse(original_file.exists(), f"Original file {original} should be removed")

def run_manual_test():
    """Manual test showing before/after filename examples"""
    print("🧹 FILENAME CLEANUP TEST")
    print("Testing removal of '_Custom_Backing_Track' suffixes")
    print("="*60)
    
    test_filenames = [
        "Jimmy_Eat_World_The_Middle(Bass_Custom_Backing_Track).mp3",
        "Taylor_Swift_Shake_It_Off_Vocals_Custom_Backing_Track.mp3", 
        "Chappell_Roan_Pink_Pony_Club(Guitar_Custom_Backing_Track).mp3",
        "Normal_Song_Drums.mp3",  # Should not change
        "Artist_Song_Piano_custom_backing_track.mp3",
    ]
    
    print("Before and after filename cleanup:")
    print()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tracker = KaraokeVersionTracker(None, None)
        
        # Create test files
        for filename in test_filenames:
            file_path = temp_path / filename
            file_path.write_text("test content")
            print(f"📁 Created: {filename}")
        
        print()
        print("Running filename cleanup...")
        
        # Run cleanup
        result = tracker._cleanup_downloaded_filenames(temp_path, "test")
        
        print(f"Cleanup result: {result}")
        print()
        print("After cleanup:")
        
        # Show results
        for file_path in sorted(temp_path.glob("*.mp3")):
            print(f"📝 Result: {file_path.name}")
    
    print()
    print("✅ Manual filename cleanup test completed")

if __name__ == "__main__":
    print("Testing filename cleanup functionality...")
    
    # Run unit tests
    unittest.main(argv=[''], verbosity=2, exit=False)
    
    print("\n" + "="*60)
    
    # Run manual test
    run_manual_test()