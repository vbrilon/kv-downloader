"""Unit tests for ProgressTracker functionality"""

import unittest
from unittest.mock import Mock, patch, call
import time
import threading
from io import StringIO
import pytest

from packages.progress.progress_tracker import ProgressTracker


class TestProgressTracker(unittest.TestCase):
    """Test cases for ProgressTracker functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.progress_tracker = ProgressTracker()
        # Use the shared fixture data for consistency
        self.sample_tracks = [
            {'name': 'Electronic Drum Kit', 'index': 1},
            {'name': 'Lead Electric Guitar', 'index': 4},
            {'name': 'Lead Vocal', 'index': 10}
        ]

    def test_init(self):
        """Test ProgressTracker initialization"""
        tracker = ProgressTracker()
        
        self.assertEqual(tracker.tracks, [])
        self.assertEqual(tracker.current_song, "")
        self.assertIsInstance(tracker.lock, threading.Lock)
        self.assertIsNone(tracker._display_thread)
        self.assertFalse(tracker._stop_display)

    def test_start_song(self):
        """Test starting progress tracking for a new song"""
        song_name = "Test Song"
        
        self.progress_tracker.start_song(song_name, self.sample_tracks)
        
        self.assertEqual(self.progress_tracker.current_song, song_name)
        self.assertEqual(len(self.progress_tracker.tracks), 3)
        
        # Verify track initialization
        track = self.progress_tracker.tracks[0]
        expected_keys = {'name', 'index', 'status', 'progress', 'file_size', 
                        'downloaded', 'start_time', 'end_time'}
        self.assertEqual(set(track.keys()), expected_keys)
        
        self.assertEqual(track['name'], 'Electronic Drum Kit')
        self.assertEqual(track['index'], 1)
        self.assertEqual(track['status'], 'pending')
        self.assertEqual(track['progress'], 0)
        self.assertIsNone(track['start_time'])
        self.assertIsNone(track['end_time'])

    def test_start_song_starts_display_thread(self):
        """Test that start_song starts the display thread"""
        with patch.object(self.progress_tracker, '_display_loop') as mock_display:
            self.progress_tracker.start_song("Test Song", self.sample_tracks)
            
            # Verify display thread was started
            self.assertIsNotNone(self.progress_tracker._display_thread)
            self.assertTrue(self.progress_tracker._display_thread.daemon)
            self.assertFalse(self.progress_tracker._stop_display)

    def test_update_track_status_by_string_index(self):
        """Test updating track status using string index"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        self.progress_tracker.update_track_status("1", "isolating", progress=25)
        
        track = self.progress_tracker.tracks[0]
        self.assertEqual(track['status'], "isolating")
        self.assertEqual(track['progress'], 25)
        self.assertIsNotNone(track['start_time'])
        self.assertIsNone(track['end_time'])

    def test_update_track_status_by_int_index(self):
        """Test updating track status using integer index"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        self.progress_tracker.update_track_status(4, "downloading", progress=75, 
                                               downloaded=1024, file_size=2048)
        
        track = self.progress_tracker.tracks[1]  # Second track has index 4
        self.assertEqual(track['status'], "downloading")
        self.assertEqual(track['progress'], 75)
        self.assertEqual(track['downloaded'], 1024)
        self.assertEqual(track['file_size'], 2048)
        self.assertIsNotNone(track['start_time'])

    def test_update_track_status_completion(self):
        """Test updating track status to completion"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        # First set to downloading
        self.progress_tracker.update_track_status(1, "downloading")
        track = self.progress_tracker.tracks[0]
        start_time = track['start_time']
        
        # Then complete
        self.progress_tracker.update_track_status(1, "completed")
        
        self.assertEqual(track['status'], "completed")
        self.assertEqual(track['start_time'], start_time)  # Should not change
        self.assertIsNotNone(track['end_time'])

    def test_update_track_status_progress_bounds(self):
        """Test that progress is bounded between 0 and 100"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        # Test upper bound
        self.progress_tracker.update_track_status(1, "downloading", progress=150)
        self.assertEqual(self.progress_tracker.tracks[0]['progress'], 100)
        
        # Test lower bound
        self.progress_tracker.update_track_status(1, "downloading", progress=-25)
        self.assertEqual(self.progress_tracker.tracks[0]['progress'], 0)

    def test_update_track_status_nonexistent_track(self):
        """Test updating status for non-existent track"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        # Should not raise exception for non-existent track
        self.progress_tracker.update_track_status(999, "downloading")
        
        # All tracks should remain in pending status
        for track in self.progress_tracker.tracks:
            self.assertEqual(track['status'], "pending")

    @patch('packages.progress.progress_tracker.os.system')
    @patch('builtins.print')
    def test_update_display(self, mock_print, mock_os_system):
        """Test display update functionality"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        self.progress_tracker.update_track_status(1, "completed")
        self.progress_tracker.update_track_status(4, "failed")
        
        self.progress_tracker._update_display()
        
        # Verify screen was cleared
        mock_os_system.assert_called()
        
        # Verify output contains expected elements
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        output = '\n'.join(print_calls)
        
        self.assertIn("Test Song", output)
        self.assertIn("Progress: 1/3 completed, 1 failed", output)
        self.assertIn("Electronic Drum Kit", output)
        self.assertIn("Lead Electric Guitar", output)

    def test_display_track_progress_status_icons(self):
        """Test that correct status icons are used"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        # Test different statuses
        test_cases = [
            ('pending', '⏳'),
            ('isolating', '🎛️'),
            ('downloading', '⬇️'),
            ('processing', '⚙️'),
            ('completed', '✅'),
            ('failed', '❌'),
            ('unknown', '❓')
        ]
        
        for status, expected_icon in test_cases:
            track = {
                'name': 'Test Track',
                'status': status,
                'progress': 0,
                'file_size': 0,
                'downloaded': 0,
                'start_time': None,
                'end_time': None
            }
            
            with patch('builtins.print') as mock_print:
                self.progress_tracker._display_track_progress(track)
                
                # Get the printed output
                printed_text = mock_print.call_args[0][0]
                self.assertTrue(printed_text.startswith(expected_icon))

    def test_display_track_progress_with_progress_bar(self):
        """Test progress bar display for downloading tracks"""
        track = {
            'name': 'Test Track',
            'status': 'downloading',
            'progress': 50,
            'file_size': 2097152,  # 2MB in bytes
            'downloaded': 1048576,  # 1MB in bytes
            'start_time': time.time() - 10,
            'end_time': None
        }
        
        with patch('builtins.print') as mock_print:
            self.progress_tracker._display_track_progress(track)
            
            printed_text = mock_print.call_args[0][0]
            self.assertIn('█', printed_text)  # Progress bar filled portion
            self.assertIn('░', printed_text)  # Progress bar empty portion
            self.assertIn('50%', printed_text)
            self.assertIn('1.0/2.0 MB', printed_text)  # File size info
            self.assertIn('(10s)', printed_text)  # Time info

    def test_display_track_progress_completed(self):
        """Test progress bar for completed tracks"""
        track = {
            'name': 'Test Track',
            'status': 'completed',
            'progress': 100,
            'file_size': 1024,
            'downloaded': 1024,
            'start_time': time.time() - 15,
            'end_time': time.time() - 5
        }
        
        with patch('builtins.print') as mock_print:
            self.progress_tracker._display_track_progress(track)
            
            printed_text = mock_print.call_args[0][0]
            self.assertIn('█' * 20, printed_text)  # Full progress bar
            self.assertIn('100%', printed_text)
            self.assertIn('(10s)', printed_text)  # Duration

    def test_finish_song(self):
        """Test finishing song progress tracking"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        with patch.object(self.progress_tracker, '_final_display') as mock_final:
            self.progress_tracker.finish_song()
            
            self.assertTrue(self.progress_tracker._stop_display)
            mock_final.assert_called_once()

    @patch('builtins.print')
    def test_final_display(self, mock_print):
        """Test final summary display"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        # Set up some completed and failed tracks
        self.progress_tracker.update_track_status(1, "completed")
        self.progress_tracker.update_track_status(4, "failed")
        self.progress_tracker.tracks[0]['start_time'] = time.time() - 20
        self.progress_tracker.tracks[0]['end_time'] = time.time() - 10
        
        self.progress_tracker._final_display()
        
        # Verify summary output - handle different call argument formats
        print_calls = []
        for call in mock_print.call_args_list:
            if call[0]:  # Has positional arguments
                print_calls.append(str(call[0][0]))
            elif 'end' in call[1]:  # Has keyword arguments like end=''
                continue  # Skip empty print calls
        
        output = '\n'.join(print_calls)
        
        self.assertIn("Download Summary for: Test Song", output)
        self.assertIn("✅ Completed: 1", output)
        self.assertIn("❌ Failed: 1", output)
        self.assertIn("Success Rate: 33.3%", output)  # 1/3
        self.assertIn("Failed tracks:", output)
        self.assertIn("Average download time:", output)

    def test_final_display_all_completed(self):
        """Test final display with all tracks completed"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        # Complete all tracks
        for i, track_info in enumerate(self.sample_tracks):
            self.progress_tracker.update_track_status(track_info['index'], "completed")
            self.progress_tracker.tracks[i]['start_time'] = time.time() - 15
            self.progress_tracker.tracks[i]['end_time'] = time.time() - 5
        
        with patch('builtins.print') as mock_print:
            self.progress_tracker._final_display()
            
            # Handle different call argument formats
            print_calls = []
            for call in mock_print.call_args_list:
                if call[0]:  # Has positional arguments
                    print_calls.append(str(call[0][0]))
                elif 'end' in call[1]:  # Has keyword arguments like end=''
                    continue  # Skip empty print calls
            
            output = '\n'.join(print_calls)
            
            self.assertIn("Success Rate: 100.0%", output)
            self.assertNotIn("Failed tracks:", output)

    def test_display_loop_stops_on_flag(self):
        """Test that display loop respects stop flag"""
        with patch.object(self.progress_tracker, '_update_display') as mock_update:
            with patch('time.sleep') as mock_sleep:
                # Start the loop but immediately stop it
                self.progress_tracker._stop_display = True
                self.progress_tracker._display_loop()
                
                # Should not have called update or sleep
                mock_update.assert_not_called()
                mock_sleep.assert_not_called()

    def test_thread_safety_concurrent_updates(self):
        """Test thread safety with concurrent track updates"""
        self.progress_tracker.start_song("Test Song", self.sample_tracks)
        
        def update_track(track_index, status):
            for _ in range(10):
                self.progress_tracker.update_track_status(track_index, status)
        
        # Create multiple threads updating different tracks
        threads = []
        for track_info in self.sample_tracks:
            thread = threading.Thread(target=update_track, 
                                    args=(track_info['index'], "downloading"))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all tracks were updated
        for track in self.progress_tracker.tracks:
            self.assertEqual(track['status'], "downloading")

    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self.progress_tracker, '_display_thread') and self.progress_tracker._display_thread:
            self.progress_tracker._stop_display = True
            self.progress_tracker._display_thread.join(timeout=1)


if __name__ == '__main__':
    unittest.main()