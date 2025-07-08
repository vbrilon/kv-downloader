"""Unit tests for StatsReporter functionality"""

import unittest
from unittest.mock import Mock, patch, mock_open
import time
import json
import tempfile
import os

from packages.progress.stats_reporter import StatsReporter


class TestStatsReporter(unittest.TestCase):
    """Test cases for StatsReporter functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.stats_reporter = StatsReporter()
        self.sample_song_name = "Test Song"
        self.sample_song_url = "https://example.com/test-song"

    def test_init(self):
        """Test StatsReporter initialization"""
        reporter = StatsReporter()
        
        self.assertIsInstance(reporter.session_start_time, float)
        self.assertEqual(reporter.songs_data, [])
        self.assertEqual(reporter.total_tracks_attempted, 0)
        self.assertEqual(reporter.total_tracks_completed, 0)
        self.assertEqual(reporter.total_tracks_failed, 0)
        self.assertEqual(reporter.total_download_time, 0)
        self.assertEqual(reporter.errors_encountered, [])

    def test_start_song(self):
        """Test starting song tracking"""
        track_count = 5
        
        with patch('time.time', return_value=1000.0):
            self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, track_count)
        
        self.assertEqual(len(self.stats_reporter.songs_data), 1)
        
        song_data = self.stats_reporter.songs_data[0]
        self.assertEqual(song_data['name'], self.sample_song_name)
        self.assertEqual(song_data['url'], self.sample_song_url)
        self.assertEqual(song_data['track_count'], track_count)
        self.assertEqual(song_data['start_time'], 1000.0)
        self.assertIsNone(song_data['end_time'])
        self.assertEqual(song_data['completed_tracks'], 0)
        self.assertEqual(song_data['failed_tracks'], 0)
        self.assertEqual(song_data['status'], 'in_progress')
        self.assertEqual(song_data['tracks'], [])

    def test_record_track_start(self):
        """Test recording track start"""
        self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 3)
        
        track_name = "Electronic Drum Kit"
        track_index = 1
        
        with patch('time.time', return_value=1010.0):
            self.stats_reporter.record_track_start(self.sample_song_name, track_name, track_index)
        
        self.assertEqual(self.stats_reporter.total_tracks_attempted, 1)
        
        song_data = self.stats_reporter.songs_data[0]
        self.assertEqual(len(song_data['tracks']), 1)
        
        track_data = song_data['tracks'][0]
        self.assertEqual(track_data['name'], track_name)
        self.assertEqual(track_data['index'], track_index)
        self.assertEqual(track_data['start_time'], 1010.0)
        self.assertIsNone(track_data['end_time'])
        self.assertEqual(track_data['status'], 'in_progress')
        self.assertEqual(track_data['download_time'], 0)
        self.assertIsNone(track_data['error_message'])
        self.assertEqual(track_data['file_size'], 0)

    def test_record_track_completion_success(self):
        """Test recording successful track completion"""
        self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 3)
        
        track_name = "Electronic Drum Kit"
        
        # Start the track
        with patch('time.time', return_value=1010.0):
            self.stats_reporter.record_track_start(self.sample_song_name, track_name, 1)
        
        # Complete the track successfully
        file_size = 2048000  # 2MB
        with patch('time.time', return_value=1025.0):
            self.stats_reporter.record_track_completion(
                self.sample_song_name, track_name, success=True, file_size=file_size
            )
        
        # Verify counters
        self.assertEqual(self.stats_reporter.total_tracks_completed, 1)
        self.assertEqual(self.stats_reporter.total_tracks_failed, 0)
        self.assertEqual(self.stats_reporter.total_download_time, 15.0)
        
        # Verify song data
        song_data = self.stats_reporter.songs_data[0]
        self.assertEqual(song_data['completed_tracks'], 1)
        self.assertEqual(song_data['failed_tracks'], 0)
        self.assertEqual(song_data['total_download_time'], 15.0)
        
        # Verify track data
        track_data = song_data['tracks'][0]
        self.assertEqual(track_data['status'], 'completed')
        self.assertEqual(track_data['end_time'], 1025.0)
        self.assertEqual(track_data['download_time'], 15.0)
        self.assertEqual(track_data['file_size'], file_size)
        self.assertIsNone(track_data['error_message'])

    def test_record_track_completion_failure(self):
        """Test recording failed track completion"""
        self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 3)
        
        track_name = "Electronic Drum Kit"
        error_message = "Download timeout"
        
        # Start the track
        with patch('time.time', return_value=1010.0):
            self.stats_reporter.record_track_start(self.sample_song_name, track_name, 1)
        
        # Fail the track
        with patch('time.time', return_value=1030.0):
            self.stats_reporter.record_track_completion(
                self.sample_song_name, track_name, success=False, error_message=error_message
            )
        
        # Verify counters
        self.assertEqual(self.stats_reporter.total_tracks_completed, 0)
        self.assertEqual(self.stats_reporter.total_tracks_failed, 1)
        self.assertEqual(self.stats_reporter.total_download_time, 20.0)
        
        # Verify error was recorded
        self.assertEqual(len(self.stats_reporter.errors_encountered), 1)
        error = self.stats_reporter.errors_encountered[0]
        self.assertEqual(error['song'], self.sample_song_name)
        self.assertEqual(error['track'], track_name)
        self.assertEqual(error['error'], error_message)
        
        # Verify song data
        song_data = self.stats_reporter.songs_data[0]
        self.assertEqual(song_data['completed_tracks'], 0)
        self.assertEqual(song_data['failed_tracks'], 1)
        
        # Verify track data
        track_data = song_data['tracks'][0]
        self.assertEqual(track_data['status'], 'failed')
        self.assertEqual(track_data['error_message'], error_message)

    def test_record_track_completion_nonexistent_song(self):
        """Test recording track completion for non-existent song"""
        # Should not raise exception
        self.stats_reporter.record_track_completion("Non-existent Song", "Track", True)
        
        # Counters should remain unchanged
        self.assertEqual(self.stats_reporter.total_tracks_completed, 0)
        self.assertEqual(self.stats_reporter.total_tracks_failed, 0)

    def test_record_track_completion_nonexistent_track(self):
        """Test recording track completion for non-existent track"""
        self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 3)
        
        # Should not raise exception
        self.stats_reporter.record_track_completion(self.sample_song_name, "Non-existent Track", True)
        
        # Counters should remain unchanged
        self.assertEqual(self.stats_reporter.total_tracks_completed, 0)
        self.assertEqual(self.stats_reporter.total_tracks_failed, 0)

    def test_finish_song_all_completed(self):
        """Test finishing song with all tracks completed"""
        # Mock start time for song
        with patch('time.time', return_value=1000.0):
            self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 2)
        
        # Add and complete tracks
        with patch('time.time', return_value=1010.0):
            self.stats_reporter.record_track_start(self.sample_song_name, "Track 1", 1)
            self.stats_reporter.record_track_start(self.sample_song_name, "Track 2", 2)
        
        with patch('time.time', return_value=1020.0):
            self.stats_reporter.record_track_completion(self.sample_song_name, "Track 1", True)
            self.stats_reporter.record_track_completion(self.sample_song_name, "Track 2", True)
        
        # Finish the song
        with patch('time.time', return_value=1030.0):
            self.stats_reporter.finish_song(self.sample_song_name)
        
        song_data = self.stats_reporter.songs_data[0]
        self.assertEqual(song_data['status'], 'completed')
        self.assertEqual(song_data['end_time'], 1030.0)
        self.assertEqual(song_data['total_time'], 30.0)  # 1030 - 1000

    def test_finish_song_partial_completion(self):
        """Test finishing song with partial completion"""
        self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 2)
        
        # Add tracks
        self.stats_reporter.record_track_start(self.sample_song_name, "Track 1", 1)
        self.stats_reporter.record_track_start(self.sample_song_name, "Track 2", 2)
        
        # Complete one, fail one
        self.stats_reporter.record_track_completion(self.sample_song_name, "Track 1", True)
        self.stats_reporter.record_track_completion(self.sample_song_name, "Track 2", False)
        
        self.stats_reporter.finish_song(self.sample_song_name)
        
        song_data = self.stats_reporter.songs_data[0]
        self.assertEqual(song_data['status'], 'partial')

    def test_finish_song_all_failed(self):
        """Test finishing song with all tracks failed"""
        self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 2)
        
        # Add and fail all tracks
        self.stats_reporter.record_track_start(self.sample_song_name, "Track 1", 1)
        self.stats_reporter.record_track_start(self.sample_song_name, "Track 2", 2)
        self.stats_reporter.record_track_completion(self.sample_song_name, "Track 1", False)
        self.stats_reporter.record_track_completion(self.sample_song_name, "Track 2", False)
        
        self.stats_reporter.finish_song(self.sample_song_name)
        
        song_data = self.stats_reporter.songs_data[0]
        self.assertEqual(song_data['status'], 'failed')

    def test_generate_final_report(self):
        """Test generating final statistics report"""
        # Set up session with sample data
        with patch('time.time', return_value=1000.0):
            self.stats_reporter.session_start_time = 1000.0
        
        # Add a song
        self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 2)
        self.stats_reporter.record_track_start(self.sample_song_name, "Track 1", 1)
        self.stats_reporter.record_track_start(self.sample_song_name, "Track 2", 2)
        self.stats_reporter.record_track_completion(self.sample_song_name, "Track 1", True)
        self.stats_reporter.record_track_completion(self.sample_song_name, "Track 2", False, "Network error")
        self.stats_reporter.finish_song(self.sample_song_name)
        
        # Generate report
        with patch('time.time', return_value=1100.0):
            report = self.stats_reporter.generate_final_report()
        
        # Verify report content
        self.assertIn("KARAOKE AUTOMATION - FINAL STATISTICS REPORT", report)
        self.assertIn("SESSION OVERVIEW", report)
        self.assertIn("Total Session Time: 1m 40.0s", report)
        self.assertIn("Songs Processed: 1", report)
        self.assertIn("Tracks Attempted: 2", report)
        self.assertIn("Tracks Completed: 1", report)
        self.assertIn("Tracks Failed: 1", report)
        self.assertIn("Overall Success Rate: 50.0%", report)
        self.assertIn("SONG SUMMARY", report)
        self.assertIn("Partially Completed: 1", report)
        self.assertIn("DETAILED SONG RESULTS", report)
        self.assertIn(self.sample_song_name, report)
        self.assertIn("ERROR SUMMARY", report)
        self.assertIn("Network error: 1 occurrences", report)

    def test_generate_final_report_empty_session(self):
        """Test generating final report with no data"""
        with patch('time.time', return_value=1060.0):
            self.stats_reporter.session_start_time = 1000.0
            report = self.stats_reporter.generate_final_report()
        
        self.assertIn("Total Session Time: 1m 0.0s", report)
        self.assertIn("Songs Processed: 0", report)
        self.assertIn("Tracks Attempted: 0", report)
        self.assertIn("Overall Success Rate: 0.0%", report)

    def test_save_detailed_report_success(self):
        """Test saving detailed report to JSON file"""
        # Add sample data
        self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 1)
        self.stats_reporter.record_track_start(self.sample_song_name, "Track 1", 1)
        self.stats_reporter.record_track_completion(self.sample_song_name, "Track 1", True)
        self.stats_reporter.finish_song(self.sample_song_name)
        
        # Mock file operations
        mock_file_data = {}
        def mock_json_dump(data, file_obj, **kwargs):
            mock_file_data.update(data)
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump', side_effect=mock_json_dump) as mock_json:
                result = self.stats_reporter.save_detailed_report("test_stats.json")
        
        self.assertTrue(result)
        mock_file.assert_called_once_with("test_stats.json", 'w')
        
        # Verify JSON structure
        self.assertIn('session_metadata', mock_file_data)
        self.assertIn('songs', mock_file_data)
        self.assertIn('errors', mock_file_data)
        
        session_meta = mock_file_data['session_metadata']
        self.assertEqual(session_meta['total_tracks_attempted'], 1)
        self.assertEqual(session_meta['total_tracks_completed'], 1)
        self.assertEqual(session_meta['total_tracks_failed'], 0)

    def test_save_detailed_report_failure(self):
        """Test handling of file save errors"""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            result = self.stats_reporter.save_detailed_report("test_stats.json")
        
        self.assertFalse(result)

    def test_get_current_song_data(self):
        """Test retrieving current song data"""
        # Add multiple songs
        self.stats_reporter.start_song("Song 1", "url1", 1)
        self.stats_reporter.start_song("Song 2", "url2", 1)
        
        # Should return most recent song with matching name
        song_data = self.stats_reporter._get_current_song_data("Song 1")
        self.assertIsNotNone(song_data)
        self.assertEqual(song_data['name'], "Song 1")
        
        # Non-existent song should return None
        song_data = self.stats_reporter._get_current_song_data("Non-existent")
        self.assertIsNone(song_data)

    def test_get_track_data(self):
        """Test retrieving track data"""
        self.stats_reporter.start_song(self.sample_song_name, self.sample_song_url, 2)
        self.stats_reporter.record_track_start(self.sample_song_name, "Track 1", 1)
        self.stats_reporter.record_track_start(self.sample_song_name, "Track 2", 2)
        
        song_data = self.stats_reporter._get_current_song_data(self.sample_song_name)
        
        # Should return most recent track with matching name
        track_data = self.stats_reporter._get_track_data(song_data, "Track 1")
        self.assertIsNotNone(track_data)
        self.assertEqual(track_data['name'], "Track 1")
        
        # Non-existent track should return None
        track_data = self.stats_reporter._get_track_data(song_data, "Non-existent")
        self.assertIsNone(track_data)
        
        # None song data should return None
        track_data = self.stats_reporter._get_track_data(None, "Track 1")
        self.assertIsNone(track_data)

    def test_format_duration(self):
        """Test duration formatting"""
        # Test seconds
        self.assertEqual(self.stats_reporter._format_duration(30.5), "30.5s")
        
        # Test minutes
        self.assertEqual(self.stats_reporter._format_duration(90.0), "1m 30.0s")
        self.assertEqual(self.stats_reporter._format_duration(125.7), "2m 5.7s")
        
        # Test hours
        self.assertEqual(self.stats_reporter._format_duration(3661.0), "1h 1m 1.0s")
        self.assertEqual(self.stats_reporter._format_duration(7323.5), "2h 2m 3.5s")

    def test_multiple_songs_session(self):
        """Test session with multiple songs"""
        # Add multiple songs with different outcomes
        songs = [
            ("Song 1", "url1", 2),  # Track 0,1 -> Track 0 succeeds (i%2==0)
            ("Song 2", "url2", 3),  # Track 0,1,2 -> Track 0,2 succeed (i%2==0)
            ("Song 3", "url3", 1)   # Track 0 -> Track 0 succeeds (i%2==0)
        ]
        
        for song_name, url, track_count in songs:
            self.stats_reporter.start_song(song_name, url, track_count)
            
            for i in range(track_count):
                track_name = f"Track {i+1}"
                self.stats_reporter.record_track_start(song_name, track_name, i+1)
                
                # Vary success/failure
                success = (i % 2 == 0)  # Every other track succeeds (Track 1, 3, 5 succeed; Track 2, 4, 6 fail)
                self.stats_reporter.record_track_completion(song_name, track_name, success)
            
            self.stats_reporter.finish_song(song_name)
        
        # Verify totals
        # Song 1: Track 1 (i=0, succeeds), Track 2 (i=1, fails) -> 1 success
        # Song 2: Track 1 (i=0, succeeds), Track 2 (i=1, fails), Track 3 (i=2, succeeds) -> 2 successes  
        # Song 3: Track 1 (i=0, succeeds) -> 1 success
        # Total: 4 successes, 2 failures
        self.assertEqual(len(self.stats_reporter.songs_data), 3)
        self.assertEqual(self.stats_reporter.total_tracks_attempted, 6)  # 2+3+1
        self.assertEqual(self.stats_reporter.total_tracks_completed, 4)  # 1+2+1 successes
        self.assertEqual(self.stats_reporter.total_tracks_failed, 2)     # 1+1+0 failures
        
        # Test report generation
        report = self.stats_reporter.generate_final_report()
        self.assertIn("Songs Processed: 3", report)
        self.assertIn("Tracks Attempted: 6", report)
        self.assertIn("Overall Success Rate: 66.7%", report)  # 4/6


if __name__ == '__main__':
    unittest.main()