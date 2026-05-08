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
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.file_operations import FileManager
from packages.track_management import TrackManager

class TestFilenameCleanup(unittest.TestCase):
    """Test filename cleanup functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.file_manager = FileManager()
    
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
        """When `track_name` is supplied, FileManager simplifies the filename
        to ``{track_name}.{ext}``; when omitted, it just strips
        ``_Custom_Backing_Track`` patterns and any parenthetical suffixes.
        """
        test_cases = [
            ("Jimmy_Eat_World_The_Middle(Bass_Custom_Backing_Track).mp3", "Bass.mp3", "Bass"),
            ("Taylor_Swift_Shake_It_Off_Vocals_Custom_Backing_Track.mp3", "Vocals.mp3", "Vocals"),
            ("Song_Name_Guitar_Custom_Backing_Track_.mp3", "Guitar.mp3", "Guitar"),
            ("Artist_Song(Custom_Backing_Track).mp3", "Artist_Song.mp3", None),
            ("Normal_File.mp3", "Normal_File.mp3", None),  # No change
        ]

        for original, expected, track_name in test_cases:
            with self.subTest(original=original):
                # Per-case isolation: shared tempdir + identical output name
                # would block the rename ("Target filename already exists").
                case_dir = Path(tempfile.mkdtemp(dir=self.temp_dir))
                original_file = case_dir / original
                original_file.write_text("test mp3 content")

                result_path = self.file_manager.clean_downloaded_filename(original_file, track_name)

                self.assertEqual(result_path.name, expected,
                                 f"Expected filename {expected}, got {result_path.name}")
                self.assertTrue(result_path.exists(),
                                f"Expected file {expected} was not created")
                if original != expected:
                    self.assertFalse(original_file.exists(),
                                     f"Original file {original} still exists")
    
    def test_multiple_pattern_cleanup(self):
        """When ``track_name`` is supplied, the simplified output is always
        ``{track_name}.{ext}`` regardless of how messy the input is."""
        inputs = [
            "Song__Name__Custom_Backing_Track__.mp3",
            "Artist--Song--(Custom_Backing_Track).mp3",
            "File().mp3",
            "Name_Custom_Backing_Track_Custom_Backing_Track.mp3",
        ]

        for original in inputs:
            with self.subTest(original=original):
                case_dir = Path(tempfile.mkdtemp(dir=self.temp_dir))
                original_file = case_dir / original
                original_file.write_text("test mp3 content")

                result_path = self.file_manager.clean_downloaded_filename(original_file, "test")
                self.assertEqual(result_path.name, "test.mp3")
                self.assertTrue(result_path.exists())
    
    def test_file_age_filtering(self):
        """`clean_downloaded_filename` only renames the file passed in;
        unrelated files in the same directory must not be touched."""
        old_file = self.create_test_file("Old_File_Custom_Backing_Track.mp3")
        old_time = time.time() - 7200  # 2 hours ago
        import os
        os.utime(old_file, (old_time, old_time))

        new_file = self.create_test_file("New_File_Custom_Backing_Track.mp3")

        result_path = self.file_manager.clean_downloaded_filename(new_file, "test")

        self.assertTrue(old_file.exists(), "Old file should not be touched")
        self.assertEqual(result_path.name, "test.mp3")
        self.assertTrue(result_path.exists())
    
    def test_duplicate_name_handling(self):
        """Test handling of duplicate filenames"""
        # Create existing target file
        existing_file = self.create_test_file("Song_Guitar.mp3")
        
        # Create file that would rename to same name
        duplicate_source = self.create_test_file("Song_Guitar_Custom_Backing_Track.mp3")
        
        # Run cleanup on duplicate file
        result_path = self.file_manager.clean_downloaded_filename(duplicate_source, "test")
        
        # Original should remain
        self.assertTrue(existing_file.exists(), "Existing file should remain")
        
        # Duplicate should be cleaned (exact behavior depends on implementation)
        self.assertTrue(result_path.exists(), "Duplicate should be processed")
    
    def test_edge_cases(self):
        """With ``track_name`` provided, even malformed inputs simplify to
        ``{track_name}.{ext}``."""
        inputs = [
            "_Custom_Backing_Track.mp3",
            "Custom_Backing_Track_.mp3",
            ".mp3_Custom_Backing_Track.mp3",
            "File_Custom_Backing_Track",  # Missing extension → defaults to mp3
        ]

        for original in inputs:
            with self.subTest(original=original):
                case_dir = Path(tempfile.mkdtemp(dir=self.temp_dir))
                original_file = case_dir / original
                original_file.write_text("test mp3 content")

                result_path = self.file_manager.clean_downloaded_filename(original_file, "test")
                self.assertEqual(result_path.name, "test.mp3")
                self.assertTrue(result_path.exists())
    
    def test_click_track_filename_bug(self):
        """Click tracks must end up as plain ``{track_name}.{ext}`` regardless
        of leading key markers like ``(-1)`` or ``(+2)`` left in the original
        filename — they should not survive into the cleaned name."""
        inputs = [
            "(-1)_Intro count      Click.mp3",
            "(+2)_Intro count Click.mp3",
            "Intro count      Click.mp3",
            "(-1)Intro_count_Click_Custom_Backing_Track.mp3",
        ]

        for original in inputs:
            with self.subTest(original=original):
                case_dir = Path(tempfile.mkdtemp(dir=self.temp_dir))
                original_file = case_dir / original
                original_file.write_text("test mp3 content")

                result_path = self.file_manager.clean_downloaded_filename(
                    original_file, track_name="Intro count Click")

                self.assertEqual(result_path.name, "Intro count Click.mp3")
                self.assertTrue(result_path.exists())
                if original != "Intro count Click.mp3":
                    self.assertFalse(original_file.exists())
    
    def test_missing_instrument_names_bug(self):
        """When a karaoke-version download lands without the instrument name in
        the filename, supplying ``track_name`` should produce a clean
        ``{track_name}.{ext}`` even when the original is just the song title.
        """
        cases = [
            ("Jimmy_Eat_World_The_Middle(Custom_Backing_Track-1).mp3", "Bass"),
            ("Jimmy_Eat_World_The_Middle_Custom_Backing_Track.mp3", "Bass"),
            ("Chappell_Roan_Pink_Pony_Club(Custom_Backing_Track+2).mp3", "Vocals"),
            ("Artist_Song_Name_Custom_Backing_Track_.mp3", "Guitar"),
        ]

        for original, track_name in cases:
            with self.subTest(original=original):
                case_dir = Path(tempfile.mkdtemp(dir=self.temp_dir))
                original_file = case_dir / original
                original_file.write_text("test mp3 content")

                result_path = self.file_manager.clean_downloaded_filename(
                    original_file, track_name=track_name)

                self.assertEqual(result_path.name, f"{track_name}.mp3")
                self.assertTrue(result_path.exists())
                self.assertFalse(original_file.exists())

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
        file_manager = FileManager()
        
        # Create test files
        for filename in test_filenames:
            file_path = temp_path / filename
            file_path.write_text("test content")
            print(f"📁 Created: {filename}")
        
        print()
        print("Running filename cleanup...")
        
        # Run cleanup on each file
        cleaned_files = []
        for file_path in temp_path.glob("*.mp3"):
            result_path = file_manager.clean_downloaded_filename(file_path, "test")
            cleaned_files.append(result_path)
        result = f"Cleaned {len(cleaned_files)} files"
        
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