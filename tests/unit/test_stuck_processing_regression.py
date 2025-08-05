#!/usr/bin/env python3
"""
Regression Test for "Stuck in Processing" Issue

This test specifically addresses the scenario where:
1. Download detection succeeds (finds existing file)
2. Completion monitoring starts but gets stuck indefinitely looking for "NEW" files
3. The existing file is never processed because it's not "new"
4. System hangs in "processing" state forever

This regression prevents the system from getting stuck and ensures existing files
are processed correctly in both headless and visible browser modes.
"""

import sys
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch
from unittest import TestCase

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.file_operations.file_manager import FileManager
from packages.di.adapters import FileManagerAdapter
from packages.download_management.download_manager import DownloadManager


class TestStuckProcessingRegression(TestCase):
    """Test that completion monitoring doesn't get stuck when files already exist"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.song_folder = self.temp_dir / "Test_Song"
        self.song_folder.mkdir(exist_ok=True)
        
        # Create real FileManager and adapter
        self.real_file_manager = FileManager()
        self.adapter = FileManagerAdapter(self.real_file_manager)
        
        # Mock download filename that would already exist
        self.downloaded_filename = "Test_Song(Bass_Custom_Backing_Track).mp3"
        
        # Setup mock DownloadManager dependencies
        self.mock_driver = Mock()
        self.mock_wait = Mock()
        self.mock_progress_tracker = Mock()
        self.mock_chrome_manager = Mock()
        self.mock_stats_reporter = Mock()
        
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_completion_monitoring_timeout_detection(self):
        """Test that we can detect when completion monitoring gets stuck indefinitely"""
        
        # Create DownloadManager with our adapters
        download_manager = DownloadManager(
            driver=self.mock_driver,
            wait=self.mock_wait,
            progress_tracker=self.mock_progress_tracker,
            file_manager=self.adapter,
            chrome_manager=self.mock_chrome_manager,
            stats_reporter=self.mock_stats_reporter
        )
        
        # Create file that already exists (simulating headless mode)
        downloaded_file = self.song_folder / self.downloaded_filename
        downloaded_file.write_text("existing mp3 content")
        
        # Mock the context that would be passed to completion monitoring
        context = {
            'song_path': self.song_folder,
            'track_name': 'Bass',
            'initial_files': {self.downloaded_filename},  # File is in initial snapshot
            'waited': 0,
            'song_name': 'Test Song'
        }
        
        # Test that _find_new_completed_files now finds existing unprocessed files (the fix)
        new_files = download_manager._find_new_completed_files(
            self.song_folder, 'Bass', context['initial_files']
        )
        
        # After the fix - should find existing file that needs processing
        self.assertGreater(len(new_files), 0, 
            "FIX: Should find existing file that needs processing")
        
        # Verify the file actually exists and should be processed
        self.assertTrue(downloaded_file.exists(), "Test file should exist")
        
        # Test that regular check_for_completed_downloads would find it
        completed_files = self.adapter.check_for_completed_downloads(self.song_folder, 'Bass')
        self.assertGreater(len(completed_files), 0, 
            "check_for_completed_downloads should find the existing file")
        
        print(f"✅ FIX VALIDATED: completion monitoring now works correctly")
        print(f"   - Existing file: {downloaded_file.name}")
        print(f"   - Found for processing: {len(new_files)} files")
        print(f"   - Total processable: {len(completed_files)} files")
    
    def test_completion_monitoring_finds_files_quickly(self):
        """Test that completion monitoring finds existing files quickly after the fix"""
        
        # Create DownloadManager 
        download_manager = DownloadManager(
            driver=self.mock_driver,
            wait=self.mock_wait,
            progress_tracker=self.mock_progress_tracker,
            file_manager=self.adapter,
            chrome_manager=self.mock_chrome_manager,
            stats_reporter=self.mock_stats_reporter
        )
        
        # Create file that already exists
        downloaded_file = self.song_folder / self.downloaded_filename
        downloaded_file.write_text("existing mp3 content")
        
        # Mock initial file snapshot (file exists at start)
        initial_files = {self.downloaded_filename}
        
        # Test completion monitoring with a very short timeout
        start_time = time.time()
        result = False
        timeout_seconds = 5  # Short timeout for testing
        
        def run_completion_check():
            nonlocal result
            waited = 0
            while waited < timeout_seconds:
                new_files = download_manager._find_new_completed_files(
                    self.song_folder, 'Bass', initial_files
                )
                if new_files:
                    result = True
                    break
                time.sleep(1)
                waited += 1
        
        # Run the test
        thread = threading.Thread(target=run_completion_check)
        thread.start()
        thread.join(timeout=timeout_seconds + 1)
        
        elapsed_time = time.time() - start_time
        
        # After the fix - completion monitoring should find the file quickly
        self.assertTrue(result, "Should find existing files that need processing")
        self.assertLess(elapsed_time, timeout_seconds, 
            "Should find file quickly, not timeout")
        
        print(f"✅ FIX VALIDATED: Completion monitoring finds file in {elapsed_time:.1f}s")
        print(f"   No longer hangs indefinitely - system works correctly")
    
    def test_fix_should_process_existing_files(self):
        """Test what the fix should do - process existing files even if not 'new'"""
        
        # Create file that already exists
        downloaded_file = self.song_folder / self.downloaded_filename
        downloaded_file.write_text("existing mp3 content")
        
        # Simulate what the fix should do: check for completed downloads regardless of "new" status
        completed_files = self.adapter.check_for_completed_downloads(self.song_folder, 'Bass')
        
        self.assertGreater(len(completed_files), 0, 
            "Fix should find existing completed files")
        
        # Test that file can be cleaned
        if completed_files:
            original_path = completed_files[0]
            cleaned_path = self.adapter.clean_downloaded_filename(original_path, 'Bass')
            
            self.assertNotEqual(cleaned_path.name, original_path.name,
                "Fix should be able to clean existing file names")
            
            print(f"✅ FIX VALIDATION: Can process existing files")
            print(f"   - Found: {len(completed_files)} completed files")
            print(f"   - Cleaned: {original_path.name} → {cleaned_path.name}")
    
    def test_fix_handles_existing_unprocessed_files(self):
        """Test that the fix correctly identifies existing files that need processing"""
        
        # Create DownloadManager
        download_manager = DownloadManager(
            driver=self.mock_driver, wait=self.mock_wait,
            progress_tracker=self.mock_progress_tracker,
            file_manager=self.adapter,
            chrome_manager=self.mock_chrome_manager,
            stats_reporter=self.mock_stats_reporter
        )
        
        # Create file with Custom_Backing_Track suffix (needs processing)
        downloaded_file = self.song_folder / self.downloaded_filename
        downloaded_file.write_text("existing mp3 content")
        
        # Simulate headless mode - file exists in initial snapshot
        initial_files = {self.downloaded_filename}
        
        # Test that the fix finds this existing unprocessed file
        found_files = download_manager._find_new_completed_files(
            self.song_folder, 'Bass', initial_files
        )
        
        self.assertEqual(len(found_files), 1, 
            "Fix should find existing file that needs processing")
        
        self.assertEqual(found_files[0].name, self.downloaded_filename,
            "Should find the correct file")
        
        # Test that a clean file (already processed) is not processed again
        clean_filename = "Bass.mp3"
        clean_file = self.song_folder / clean_filename
        clean_file.write_text("clean mp3 content")
        
        # Add clean file to initial files  
        initial_files_with_clean = initial_files | {clean_filename}
        
        found_files_with_clean = download_manager._find_new_completed_files(
            self.song_folder, 'Bass', initial_files_with_clean
        )
        
        # Should still only find the unprocessed file, not the clean one
        self.assertEqual(len(found_files_with_clean), 1,
            "Should not reprocess already clean files")
        
        self.assertEqual(found_files_with_clean[0].name, self.downloaded_filename,
            "Should only find the file that needs processing")
        
        print(f"✅ FIX VALIDATION: Correctly handles existing vs processed files")
        print(f"   - Unprocessed file found: {found_files_with_clean[0].name}")
        print(f"   - Clean file ignored: {clean_filename}")
    
    def test_headless_vs_visible_mode_simulation(self):
        """Test simulation of headless vs visible mode behavior"""
        
        print("\n🔍 SIMULATING DIFFERENT BROWSER MODES:")
        
        # Simulate VISIBLE mode (file appears after monitoring starts)
        print("\n1️⃣ VISIBLE MODE SIMULATION:")
        visible_initial_files = set()  # No files initially
        
        # Start monitoring, then file appears
        downloaded_file = self.song_folder / self.downloaded_filename
        downloaded_file.write_text("new download in visible mode")
        
        # Create DownloadManager for testing
        download_manager = DownloadManager(
            driver=self.mock_driver, wait=self.mock_wait,
            progress_tracker=self.mock_progress_tracker,
            file_manager=self.adapter,
            chrome_manager=self.mock_chrome_manager,
            stats_reporter=self.mock_stats_reporter
        )
        
        visible_new_files = download_manager._find_new_completed_files(
            self.song_folder, 'Bass', visible_initial_files
        )
        print(f"   - Initial files: {len(visible_initial_files)}")
        print(f"   - New files found: {len(visible_new_files)}")
        print(f"   - Result: {'SUCCESS - file processed' if visible_new_files else 'FAILED - stuck'}")
        
        # Clean up for next test  
        downloaded_file.unlink()
        
        # Simulate HEADLESS mode (file exists before monitoring starts)
        print("\n2️⃣ HEADLESS MODE SIMULATION:")
        downloaded_file.write_text("instant download in headless mode")
        headless_initial_files = {self.downloaded_filename}  # File already exists
        
        headless_new_files = download_manager._find_new_completed_files(
            self.song_folder, 'Bass', headless_initial_files
        )
        print(f"   - Initial files: {len(headless_initial_files)}")
        print(f"   - New files found: {len(headless_new_files)}")
        print(f"   - Result: {'SUCCESS - file processed' if headless_new_files else 'FAILED - stuck'}")
        
        # Validate that both modes work after the fix
        self.assertGreater(len(visible_new_files), 0, "Visible mode should work")
        self.assertGreater(len(headless_new_files), 0, "Headless mode should work after fix")
        
        if len(headless_new_files) > 0:
            print(f"\n🎯 CONCLUSION: ✅ FIX SUCCESSFUL - Both modes work correctly!")
        else:
            print(f"\n🎯 CONCLUSION: ❌ Headless mode still gets stuck")


if __name__ == "__main__":
    import unittest
    unittest.main()