#!/usr/bin/env python3
"""
Regression Test for Download Detection and File Renaming Issues

This test specifically addresses the scenario where:
1. Files download successfully from the website
2. Download detection times out after 30s (fails to detect the file)  
3. Files remain unprocessed/unrenamed
4. The system reports download failure despite successful download

This regression test ensures that the download detection and completion
monitoring systems work correctly end-to-end.
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch
from unittest import TestCase

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.file_operations.file_manager import FileManager
from packages.di.adapters import FileManagerAdapter
from packages.di.container import DIContainer
from packages.di.factory import create_container_with_dependencies


class TestDownloadDetectionRegression(TestCase):
    """Test download detection and file processing regression scenarios"""
    
    def setUp(self):
        """Set up test environment with real and adapter file managers"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.song_folder = self.temp_dir / "Journey_Any Way You Want It"
        self.song_folder.mkdir(exist_ok=True)
        
        # Create real FileManager and adapter
        self.real_file_manager = FileManager()
        self.adapter = FileManagerAdapter(self.real_file_manager)
        
        # Mock download filename that would actually be downloaded
        self.downloaded_filename = "Journey_Any_Way_You_Want_It(Intro_Count_(Click_+_Key)_Custom_Backing_Track).mp3"
        self.expected_clean_filename = "Intro Count (Click + Key).mp3"
        
        # Generic backing track filename (the bug case)
        self.generic_backing_track = "Journey_Any_Way_You_Want_It(Custom_Backing_Track).mp3"
        
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_download_detection_success_scenario(self):
        """Test that download detection works when file appears during monitoring"""
        track_name = "Intro Count (Click + Key)"
        
        # Start monitoring in a separate thread to simulate real behavior
        import threading
        detection_result = []
        
        def monitor_download():
            result = self.adapter.wait_for_download_to_start(track_name, self.song_folder, 0)
            detection_result.append(result)
        
        # Start monitoring
        monitor_thread = threading.Thread(target=monitor_download)
        monitor_thread.start()
        
        # Simulate file appearing after 2 seconds (like a real download)
        time.sleep(2)
        downloaded_file = self.song_folder / self.downloaded_filename
        downloaded_file.write_text("fake mp3 content")
        
        # Wait for monitoring to complete
        monitor_thread.join(timeout=35)  # Give it 35s max (more than the 30s timeout)
        
        # Verify detection succeeded
        self.assertTrue(len(detection_result) > 0, "Monitor thread should have completed")
        self.assertTrue(detection_result[0], "Download detection should succeed when file appears")
        
        # Verify file exists
        self.assertTrue(downloaded_file.exists(), "Downloaded file should exist")
    
    def test_download_detection_timeout_scenario(self):
        """Test the regression: download detection times out even when adapter has all methods"""
        track_name = "Intro Count (Click + Key)"
        
        # Create the file BEFORE monitoring starts (simulating the issue where file exists but isn't detected)
        downloaded_file = self.song_folder / self.downloaded_filename
        downloaded_file.write_text("fake mp3 content")
        
        # Verify file exists before we start
        self.assertTrue(downloaded_file.exists(), "File should exist before monitoring")
        
        # Test detection with a short timeout to avoid waiting 30s in tests
        with patch('packages.file_operations.file_manager.FILE_OPERATION_MAX_WAIT', 5):
            result = self.adapter.wait_for_download_to_start(track_name, self.song_folder, 0)
        
        # This should succeed but currently fails due to adapter issues
        # When the bug is fixed, this should be True
        # For now, we document the expected behavior
        if not result:
            self.fail(f"REGRESSION: Download detection failed even though file exists: {downloaded_file}")
    
    def test_file_processing_pipeline(self):
        """Test the complete file processing pipeline: detection -> completion monitoring -> renaming"""
        track_name = "Intro Count (Click + Key)"
        
        # Step 1: Create downloaded file (simulating successful download)
        downloaded_file = self.song_folder / self.downloaded_filename
        downloaded_file.write_text("fake mp3 content")
        
        # Step 2: Test download detection
        with patch('packages.file_operations.file_manager.FILE_OPERATION_MAX_WAIT', 1):
            detection_result = self.adapter.wait_for_download_to_start(track_name, self.song_folder, 0)
        
        if detection_result:
            # Step 3: Test completion monitoring (check for completed downloads)  
            completed_files = self.adapter.check_for_completed_downloads(self.song_folder, track_name)
            self.assertGreater(len(completed_files), 0, "Should find completed download files")
            
            # Step 4: Test file cleaning/renaming
            cleaned_path = self.adapter.clean_downloaded_filename(downloaded_file, track_name)
            self.assertIsNotNone(cleaned_path, "clean_downloaded_filename should return a path")
            self.assertNotEqual(str(cleaned_path), str(downloaded_file), "Cleaned path should be different from original")
        else:
            self.fail("Download detection failed - cannot test full pipeline")
    
    def test_adapter_method_coverage_for_detection(self):
        """Test that adapter has all methods needed for download detection"""
        required_methods = [
            '_get_file_info',
            '_scan_directory_cached', 
            '_is_audio_file',
            '_matches_karaoke_patterns',
            'wait_for_download_to_start',
            'check_for_completed_downloads',
            'clean_downloaded_filename'
        ]
        
        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(
                    hasattr(self.adapter, method_name),
                    f"FileManagerAdapter missing method: {method_name}"
                )
    
    def test_karaoke_pattern_detection_with_real_filename(self):
        """Test that the actual downloaded filename is properly detected as karaoke"""
        filename_lower = self.downloaded_filename.lower()
        
        # Test individual components
        is_audio = self.adapter._is_audio_file(filename_lower)
        self.assertTrue(is_audio, f"Should detect {self.downloaded_filename} as audio file")
        
        matches_karaoke = self.adapter._matches_karaoke_patterns(filename_lower)
        self.assertTrue(matches_karaoke, f"Should detect {self.downloaded_filename} as karaoke file")
        
        # Test the combined logic from wait_for_download_to_start
        is_audio_or_download = is_audio or filename_lower.endswith('.crdownload')
        might_be_karaoke = matches_karaoke or len(self.downloaded_filename) > 20
        should_be_detected = is_audio_or_download and might_be_karaoke
        
        self.assertTrue(should_be_detected, 
                       f"File {self.downloaded_filename} should be detected by download monitoring logic")
    
    def test_di_container_integration(self):
        """Test that the DI container properly wires the FileManagerAdapter"""
        mock_chrome_manager = Mock()
        
        # Create container with real FileManager
        container = create_container_with_dependencies(
            chrome_manager=mock_chrome_manager,
            file_manager=self.real_file_manager
        )
        
        # Get the file manager from container
        file_manager_from_di = container.get(type(self.adapter).__bases__[0])  # Get IFileManager
        
        # Verify it's an adapter wrapping our real file manager
        self.assertIsInstance(file_manager_from_di, FileManagerAdapter)
        self.assertEqual(file_manager_from_di._file_manager, self.real_file_manager)
        
        # Verify critical methods work
        test_filename = self.downloaded_filename.lower()
        self.assertTrue(file_manager_from_di._is_audio_file(test_filename))
        self.assertTrue(file_manager_from_di._matches_karaoke_patterns(test_filename))
    
    def test_generic_backing_track_file_renaming_bug_regression(self):
        """
        Regression test for the critical bug where generic backing track files
        were not being renamed to specific track names.
        
        Bug scenario:
        1. User solos track "Intro Count (Click + Key)"
        2. Download produces generic file "Journey_Any_Way_You_Want_It(Custom_Backing_Track).mp3"
        3. File cleanup logic skipped the file because it didn't match track name
        4. File never got renamed to "Intro Count (Click + Key).mp3"
        
        Expected behavior after fix:
        - ALL files with Custom_Backing_Track suffix should be renamed
        - Track name matching should not be required for cleanup
        """
        from packages.download_management.download_manager import DownloadManager
        
        # Create mock dependencies
        mock_driver = Mock()
        mock_wait = Mock()
        mock_chrome_manager = Mock()
        mock_progress_tracker = Mock()
        mock_stats_reporter = Mock()
        
        # Create download manager with real file manager
        download_manager = DownloadManager(
            driver=mock_driver,
            wait=mock_wait,
            progress_tracker=mock_progress_tracker,
            file_manager=self.real_file_manager,
            chrome_manager=mock_chrome_manager,
            stats_reporter=mock_stats_reporter
        )
        
        # Create the generic backing track file (the bug case)
        generic_file = self.song_folder / self.generic_backing_track
        generic_file.write_text("test audio content")
        
        # Verify file was created
        self.assertTrue(generic_file.exists(), "Generic backing track file should exist")
        
        # Test the file cleanup identification logic (this was the bug)
        files_to_check = [generic_file]
        track_name = "Intro Count (Click + Key)"
        
        files_needing_cleanup = download_manager._identify_files_needing_cleanup(
            files_to_check, track_name
        )
        
        # CRITICAL: The generic backing track file should be identified for cleanup
        # even though it doesn't match the track name
        self.assertEqual(len(files_needing_cleanup), 1, 
                        "Generic backing track file should be identified for cleanup")
        self.assertEqual(files_needing_cleanup[0], generic_file,
                        "The generic backing track file should be in cleanup list")
        
        # Test the actual cleanup process
        cleaned_paths = download_manager._clean_downloaded_files(files_needing_cleanup, track_name)
        
        # Verify the file was renamed correctly
        expected_renamed_file = self.song_folder / "Intro Count (Click + Key).mp3"
        self.assertTrue(expected_renamed_file.exists(), 
                       f"File should be renamed to '{expected_renamed_file.name}'")
        self.assertFalse(generic_file.exists(), 
                        "Original generic file should be removed after renaming")
        
        # Verify the path mapping was correct
        self.assertIn(generic_file, cleaned_paths,
                     "Original file path should be in cleaned paths mapping")
        self.assertEqual(cleaned_paths[generic_file], expected_renamed_file,
                        "Path mapping should point to renamed file")
    
    def test_track_name_mismatch_scenarios(self):
        """
        Test various scenarios where downloaded files don't match track names
        but should still be renamed (all Custom_Backing_Track files should be cleaned)
        """
        from packages.download_management.download_manager import DownloadManager
        
        # Create mock dependencies  
        mock_driver = Mock()
        mock_wait = Mock()
        mock_chrome_manager = Mock()
        mock_progress_tracker = Mock()
        mock_stats_reporter = Mock()
        
        download_manager = DownloadManager(
            driver=mock_driver,
            wait=mock_wait,
            progress_tracker=mock_progress_tracker,
            file_manager=self.real_file_manager,
            chrome_manager=mock_chrome_manager,
            stats_reporter=mock_stats_reporter
        )
        
        # Test cases: (downloaded_filename, track_name, expected_renamed)
        test_cases = [
            ("Song_Name(Custom_Backing_Track).mp3", "Bass", "Bass.mp3"),
            ("Artist_Track(Custom_Backing_Track-1).mp3", "Guitar", "Guitar.mp3"), 
            ("Generic_Backing_Track_Custom_Backing_Track.mp3", "Vocals", "Vocals.mp3"),
            ("Complex_Song_Name_Custom_Backing_Track_.mp3", "Drum Kit", "Drum Kit.mp3"),
        ]
        
        for downloaded_filename, track_name, expected_renamed in test_cases:
            with self.subTest(downloaded=downloaded_filename, track=track_name):
                # Create test file  
                test_file = self.song_folder / downloaded_filename
                test_file.write_text("test content")
                
                # Test identification 
                files_needing_cleanup = download_manager._identify_files_needing_cleanup(
                    [test_file], track_name
                )
                
                # Should always identify Custom_Backing_Track files for cleanup
                self.assertEqual(len(files_needing_cleanup), 1,
                               f"File {downloaded_filename} should be identified for cleanup")
                
                # Test cleanup
                cleaned_paths = download_manager._clean_downloaded_files(
                    files_needing_cleanup, track_name
                )
                
                # Verify renaming
                expected_file = self.song_folder / expected_renamed
                self.assertTrue(expected_file.exists(),
                               f"File should be renamed to {expected_renamed}")
                self.assertFalse(test_file.exists(),
                               f"Original file {downloaded_filename} should be removed")
                
                # Clean up for next iteration
                if expected_file.exists():
                    expected_file.unlink()
    
    def test_caching_behavior_during_detection(self):
        """Test that file caching doesn't interfere with download detection"""
        # Create initial file
        downloaded_file = self.song_folder / self.downloaded_filename
        downloaded_file.write_text("initial content")
        
        # Get initial info (should be cached)
        initial_info = self.adapter._get_file_info(downloaded_file)
        self.assertIsNotNone(initial_info)
        
        # Modify file (simulating download completion)
        time.sleep(0.1)  # Ensure different mtime
        downloaded_file.write_text("updated content - download complete with much more content to change size")
        
        # Wait for cache TTL to expire (cache TTL is 2 seconds)
        time.sleep(2.1)
        
        # Check if cache invalidation works
        updated_info = self.adapter._get_file_info(downloaded_file)
        self.assertIsNotNone(updated_info)
        
        # Size should be different if caching works correctly
        self.assertNotEqual(initial_info.get('size'), updated_info.get('size'))


if __name__ == "__main__":
    import unittest
    unittest.main()