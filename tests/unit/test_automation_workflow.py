"""
Unit tests for KaraokeVersionAutomator helper methods extracted during Phase 2 refactoring.

These tests cover the 12 helper methods that were extracted from the run_automation() method
to improve code maintainability and testability.
"""

import pytest
import logging
from unittest.mock import Mock, patch, call
from tests.mock_standards import MockPatterns


class TestKaraokeVersionAutomatorWorkflow:
    """Test the automation workflow helper methods"""
    
    def setup_method(self):
        """Set up test fixtures for each test method"""
        # Mock all dependencies to isolate the automator
        with patch('karaoke_automator.ConfigurationManager'), \
             patch('karaoke_automator.ChromeManager'), \
             patch('karaoke_automator.LoginManager'), \
             patch('karaoke_automator.ProgressTracker'), \
             patch('karaoke_automator.StatsReporter'), \
             patch('karaoke_automator.FileManager'), \
             patch('karaoke_automator.TrackManager'), \
             patch('karaoke_automator.DownloadManager'):
            
            from karaoke_automator import KaraokeVersionAutomator
            self.automator = KaraokeVersionAutomator()
            
            # Mock internal components
            self.automator.login_handler = Mock()
            self.automator.progress = Mock()
            self.automator.stats = Mock()
            self.automator.file_manager = Mock()
            self.automator.track_manager = Mock()
            self.automator.download_manager = Mock()
    
    def test_setup_automation_session_success(self):
        """Test successful automation session setup"""
        # Arrange
        self.automator.login = Mock(return_value=True)
        
        # Act
        result = self.automator._setup_automation_session()
        
        # Assert
        assert result is True
        self.automator.login.assert_called_once()
    
    def test_setup_automation_session_login_failure(self):
        """Test automation session setup when login fails"""
        # Arrange
        self.automator.login = Mock(return_value=False)
        
        # Act
        with patch('logging.error') as mock_log_error:
            result = self.automator._setup_automation_session()
        
        # Assert
        assert result is False
        self.automator.login.assert_called_once()
        mock_log_error.assert_called_once_with("Login failed - cannot proceed")
    
    def test_log_song_configuration_with_key_adjustment(self):
        """Test logging song configuration with key adjustment"""
        # Act
        with patch('logging.info') as mock_log_info:
            self.automator._log_song_configuration(3)
        
        # Assert
        mock_log_info.assert_called_once_with("🎵 Song configuration - Key: +3 semitones")
    
    def test_log_song_configuration_negative_key_adjustment(self):
        """Test logging song configuration with negative key adjustment"""
        # Act
        with patch('logging.info') as mock_log_info:
            self.automator._log_song_configuration(-2)
        
        # Assert
        mock_log_info.assert_called_once_with("🎵 Song configuration - Key: -2 semitones")
    
    def test_log_song_configuration_no_adjustment(self):
        """Test logging song configuration with no key adjustment"""
        # Act
        with patch('logging.info') as mock_log_info:
            self.automator._log_song_configuration(0)
        
        # Assert
        mock_log_info.assert_called_once_with("🎵 Song configuration - Key: no adjustment")
    
    def test_verify_login_session_already_logged_in(self):
        """Test login session verification when already logged in"""
        # Arrange
        self.automator.is_logged_in = Mock(return_value=True)
        
        # Act
        result = self.automator._verify_login_session()
        
        # Assert
        assert result is True
        self.automator.is_logged_in.assert_called_once()
    
    def test_verify_login_session_expired_successful_relogin(self):
        """Test login session verification when session expired but relogin succeeds"""
        # Arrange
        self.automator.is_logged_in = Mock(return_value=False)
        self.automator.login = Mock(return_value=True)
        
        # Act
        with patch('logging.error') as mock_log_error:
            result = self.automator._verify_login_session()
        
        # Assert
        assert result is True
        self.automator.is_logged_in.assert_called_once()
        self.automator.login.assert_called_once()
        mock_log_error.assert_called_once_with("Login session expired")
    
    def test_verify_login_session_expired_failed_relogin(self):
        """Test login session verification when session expired and relogin fails"""
        # Arrange
        self.automator.is_logged_in = Mock(return_value=False)
        self.automator.login = Mock(return_value=False)
        
        # Act
        with patch('logging.error') as mock_log_error:
            result = self.automator._verify_login_session()
        
        # Assert
        assert result is False
        self.automator.is_logged_in.assert_called_once()
        self.automator.login.assert_called_once()
        assert mock_log_error.call_count == 2
        mock_log_error.assert_any_call("Login session expired")
        mock_log_error.assert_any_call("Re-login failed")
    
    def test_start_song_tracking_with_progress(self):
        """Test starting song tracking when progress tracker is available"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        tracks = [{'name': 'Track 1', 'index': 0}, {'name': 'Track 2', 'index': 1}]
        
        # Act
        self.automator._start_song_tracking(song, tracks)
        
        # Assert
        self.automator.progress.start_song.assert_called_once_with('Test Song', tracks)
        self.automator.stats.start_song.assert_called_once_with('Test Song', 'http://example.com', 2)
    
    def test_start_song_tracking_without_progress(self):
        """Test starting song tracking when progress tracker is None"""
        # Arrange
        self.automator.progress = None
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        tracks = [{'name': 'Track 1', 'index': 0}]
        
        # Act
        self.automator._start_song_tracking(song, tracks)
        
        # Assert
        # Only stats should be called, not progress
        self.automator.stats.start_song.assert_called_once_with('Test Song', 'http://example.com', 1)
    
    def test_setup_mixer_controls_no_key_adjustment(self):
        """Test setting up mixer controls with no key adjustment"""
        # Arrange
        song = {'url': 'http://example.com'}
        self.automator.track_manager.ensure_intro_count_enabled.return_value = True
        
        # Act
        with patch('logging.info') as mock_log_info:
            self.automator._setup_mixer_controls(song, 0)
        
        # Assert
        mock_log_info.assert_called_once_with("🎛️ Setting up mixer controls...")
        self.automator.track_manager.ensure_intro_count_enabled.assert_called_once_with('http://example.com')
        self.automator.track_manager.adjust_key.assert_not_called()
    
    def test_setup_mixer_controls_with_key_adjustment(self):
        """Test setting up mixer controls with key adjustment"""
        # Arrange
        song = {'url': 'http://example.com'}
        self.automator.track_manager.ensure_intro_count_enabled.return_value = True
        self.automator.track_manager.adjust_key.return_value = True
        
        # Act
        with patch('logging.info') as mock_log_info, \
             patch('logging.warning') as mock_log_warning:
            self.automator._setup_mixer_controls(song, 3)
        
        # Assert
        mock_log_info.assert_called_once_with("🎛️ Setting up mixer controls...")
        self.automator.track_manager.ensure_intro_count_enabled.assert_called_once_with('http://example.com')
        self.automator.track_manager.adjust_key.assert_called_once_with('http://example.com', 3)
        mock_log_warning.assert_not_called()
    
    def test_setup_mixer_controls_intro_count_failure(self):
        """Test setting up mixer controls when intro count setup fails"""
        # Arrange
        song = {'url': 'http://example.com'}
        self.automator.track_manager.ensure_intro_count_enabled.return_value = False
        
        # Act
        with patch('logging.info') as mock_log_info, \
             patch('logging.warning') as mock_log_warning:
            self.automator._setup_mixer_controls(song, 0)
        
        # Assert
        mock_log_warning.assert_called_once_with("⚠️ Could not enable intro count - continuing anyway")
    
    def test_setup_mixer_controls_key_adjustment_failure(self):
        """Test setting up mixer controls when key adjustment fails"""
        # Arrange
        song = {'url': 'http://example.com'}
        self.automator.track_manager.ensure_intro_count_enabled.return_value = True
        self.automator.track_manager.adjust_key.return_value = False
        
        # Act
        with patch('logging.info') as mock_log_info, \
             patch('logging.warning') as mock_log_warning:
            self.automator._setup_mixer_controls(song, -2)
        
        # Assert
        mock_log_warning.assert_called_once_with("⚠️ Could not adjust key to -2 - continuing with default key")
    
    def test_prepare_song_folder_with_explicit_name(self):
        """Test preparing song folder when song has explicit name"""
        # Arrange
        song = {'name': 'Explicit_Song_Name', 'url': 'http://example.com'}
        
        # Act
        self.automator._prepare_song_folder(song)
        
        # Assert
        self.automator.file_manager.clear_song_folder.assert_called_once_with('Explicit_Song_Name')
        self.automator.download_manager.extract_song_folder_name.assert_not_called()
    
    def test_prepare_song_folder_without_name(self):
        """Test preparing song folder when song has no explicit name"""
        # Arrange
        song = {'url': 'http://example.com'}
        self.automator.download_manager.extract_song_folder_name.return_value = 'Extracted_Name'
        
        # Act
        self.automator._prepare_song_folder(song)
        
        # Assert
        self.automator.download_manager.extract_song_folder_name.assert_called_once_with('http://example.com')
        self.automator.file_manager.clear_song_folder.assert_called_once_with('Extracted_Name')
    
    def test_download_all_tracks(self):
        """Test downloading all tracks for a song"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        tracks = [
            {'name': 'Track 1', 'index': 0},
            {'name': 'Track 2', 'index': 1}
        ]
        
        # Mock the single track download method
        self.automator._download_single_track = Mock()
        
        # Act
        with patch('time.sleep') as mock_sleep:
            self.automator._download_all_tracks(song, tracks, 2)
        
        # Assert
        assert self.automator._download_single_track.call_count == 2
        expected_calls = [
            call(song, tracks[0], 2),
            call(song, tracks[1], 2)
        ]
        self.automator._download_single_track.assert_has_calls(expected_calls)
        
        # Verify sleep was called after each track (including the last one)
        assert mock_sleep.call_count == 2  # Called after each of the two tracks
        mock_sleep.assert_called_with(2)
    
    @patch('time.sleep')
    def test_download_single_track_success(self, mock_sleep):
        """Test successful single track download"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        track = {'name': 'Lead Guitar', 'index': 4}
        
        self.automator.sanitize_filename = Mock(return_value='Lead_Guitar')
        self.automator.solo_track = Mock(return_value=True)
        self.automator.download_manager.download_current_mix.return_value = True
        
        # Act
        self.automator._download_single_track(song, track, 2)
        
        # Assert
        self.automator.sanitize_filename.assert_called_once_with('Lead Guitar')
        self.automator.progress.update_track_status.assert_called_once_with(4, 'isolating')
        self.automator.stats.record_track_start.assert_called_once_with('Test Song', 'Lead_Guitar', 4)
        self.automator.solo_track.assert_called_once_with(track, 'http://example.com')
        
        self.automator.download_manager.download_current_mix.assert_called_once_with(
            'http://example.com',
            'Lead_Guitar',
            cleanup_existing=False,
            song_folder='Test Song',  # Uses song.get('name') which returns 'Test Song'
            key_adjustment=2,
            track_index=4
        )
    
    @patch('time.sleep')
    def test_download_single_track_solo_failure(self, mock_sleep):
        """Test single track download when solo operation fails"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        track = {'name': 'Lead Guitar', 'index': 4}
        
        self.automator.sanitize_filename = Mock(return_value='Lead_Guitar')
        self.automator.solo_track = Mock(return_value=False)
        
        # Act
        with patch('logging.error') as mock_log_error:
            self.automator._download_single_track(song, track, 0)
        
        # Assert
        mock_log_error.assert_called_once_with("Failed to solo track Lead_Guitar")
        self.automator.progress.update_track_status.assert_any_call(4, 'failed')
        
        self.automator.stats.record_track_completion.assert_called_once_with(
            'Test Song', 'Lead_Guitar', success=False, error_message="Failed to solo track"
        )
        
        # Download should not be attempted
        self.automator.download_manager.download_current_mix.assert_not_called()
    
    @patch('time.sleep')
    def test_download_single_track_download_failure(self, mock_sleep):
        """Test single track download when download operation fails"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        track = {'name': 'Lead Guitar', 'index': 4}
        
        self.automator.sanitize_filename = Mock(return_value='Lead_Guitar')
        self.automator.solo_track = Mock(return_value=True)
        self.automator.download_manager.download_current_mix.return_value = False
        
        # Act
        with patch('logging.error') as mock_log_error:
            self.automator._download_single_track(song, track, 0)
        
        # Assert
        mock_log_error.assert_called_once_with("Failed to download Lead_Guitar")
        # Solo was successful but download failed
        self.automator.solo_track.assert_called_once()
        self.automator.download_manager.download_current_mix.assert_called_once()
    
    def test_finish_song_processing_with_progress(self):
        """Test finishing song processing when progress tracker is available"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        self.automator.clear_all_solos = Mock()
        
        # Act
        self.automator._finish_song_processing(song)
        
        # Assert
        self.automator.clear_all_solos.assert_called_once_with('http://example.com')
        self.automator.progress.finish_song.assert_called_once()
        self.automator.stats.finish_song.assert_called_once_with('Test Song')
    
    def test_finish_song_processing_without_progress(self):
        """Test finishing song processing when progress tracker is None"""
        # Arrange
        self.automator.progress = None
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        self.automator.clear_all_solos = Mock()
        
        # Act
        self.automator._finish_song_processing(song)
        
        # Assert
        self.automator.clear_all_solos.assert_called_once_with('http://example.com')
        self.automator.stats.finish_song.assert_called_once_with('Test Song')
    
    def test_handle_no_tracks_found(self):
        """Test handling case where no tracks are found"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        
        # Act
        with patch('logging.error') as mock_log_error:
            self.automator._handle_no_tracks_found(song)
        
        # Assert
        mock_log_error.assert_called_once_with("No tracks found for Test Song")
        self.automator.stats.start_song.assert_called_once_with('Test Song', 'http://example.com', 0)
        self.automator.stats.finish_song.assert_called_once_with('Test Song')
    
    def test_process_song_with_tracks(self):
        """Test processing a song that has available tracks"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        tracks = [{'name': 'Track 1', 'index': 0}]
        
        # Mock all the helper methods
        self.automator._start_song_tracking = Mock()
        self.automator._setup_mixer_controls = Mock()
        self.automator._prepare_song_folder = Mock()
        self.automator._download_all_tracks = Mock()
        self.automator._finish_song_processing = Mock()
        
        # Act
        with patch('logging.info') as mock_log_info:
            self.automator._process_song_with_tracks(song, tracks, 2)
        
        # Assert
        mock_log_info.assert_called_once_with("Found 1 tracks for Test Song")
        self.automator._start_song_tracking.assert_called_once_with(song, tracks)
        self.automator._setup_mixer_controls.assert_called_once_with(song, 2)
        self.automator._prepare_song_folder.assert_called_once_with(song)
        self.automator._download_all_tracks.assert_called_once_with(song, tracks, 2)
        self.automator._finish_song_processing.assert_called_once_with(song)
    
    def test_process_single_song_with_tracks(self):
        """Test processing a single song that has tracks available"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com', 'key': 3}
        tracks = [{'name': 'Track 1', 'index': 0}]
        
        # Mock dependencies
        self.automator._log_song_configuration = Mock()
        self.automator._verify_login_session = Mock(return_value=True)
        self.automator.get_available_tracks = Mock(return_value=tracks)
        self.automator._process_song_with_tracks = Mock()
        self.automator._handle_no_tracks_found = Mock()
        
        # Act
        with patch('logging.info') as mock_log_info:
            self.automator._process_single_song(song)
        
        # Assert
        mock_log_info.assert_called_once_with("Processing: Test Song")
        self.automator._log_song_configuration.assert_called_once_with(3)
        self.automator._verify_login_session.assert_called_once()
        self.automator.get_available_tracks.assert_called_once_with('http://example.com')
        self.automator._process_song_with_tracks.assert_called_once_with(song, tracks, 3)
        self.automator._handle_no_tracks_found.assert_not_called()
    
    def test_process_single_song_no_tracks(self):
        """Test processing a single song that has no tracks available"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com', 'key': 0}
        
        # Mock dependencies
        self.automator._log_song_configuration = Mock()
        self.automator._verify_login_session = Mock(return_value=True)
        self.automator.get_available_tracks = Mock(return_value=[])
        self.automator._process_song_with_tracks = Mock()
        self.automator._handle_no_tracks_found = Mock()
        
        # Act
        self.automator._process_single_song(song)
        
        # Assert
        self.automator._log_song_configuration.assert_called_once_with(0)
        self.automator._verify_login_session.assert_called_once()
        self.automator.get_available_tracks.assert_called_once_with('http://example.com')
        self.automator._process_song_with_tracks.assert_not_called()
        self.automator._handle_no_tracks_found.assert_called_once_with(song)
    
    def test_process_single_song_login_verification_failure(self):
        """Test processing a single song when login verification fails"""
        # Arrange
        song = {'name': 'Test Song', 'url': 'http://example.com'}
        
        # Mock dependencies
        self.automator._log_song_configuration = Mock()
        self.automator._verify_login_session = Mock(return_value=False)
        self.automator.get_available_tracks = Mock()
        
        # Act
        result = self.automator._process_single_song(song)
        
        # Assert
        assert result is False
        self.automator._verify_login_session.assert_called_once()
        # Should not proceed to track discovery
        self.automator.get_available_tracks.assert_not_called()
    
    @patch('builtins.print')
    def test_generate_final_reports_success(self, mock_print):
        """Test generating final reports for successful automation"""
        # Arrange
        self.automator.stats.generate_final_report.return_value = "Final Report Content"
        self.automator.stats.save_detailed_report.return_value = True
        
        # Act
        with patch('logging.error') as mock_log_error:
            self.automator._generate_final_reports(failed=False)
        
        # Assert
        self.automator.stats.generate_final_report.assert_called_once()
        self.automator.stats.save_detailed_report.assert_called_once_with("logs/automation_stats.json")
        
        # Check print calls
        assert mock_print.call_count >= 3
        mock_print.assert_any_call("\n" + "="*80)
        mock_print.assert_any_call("📊 GENERATING FINAL STATISTICS REPORT...")
        mock_print.assert_any_call("Final Report Content")
        mock_print.assert_any_call("\n📁 Detailed statistics saved to: logs/automation_stats.json")
        
        mock_log_error.assert_not_called()
    
    @patch('builtins.print')
    def test_generate_final_reports_failure(self, mock_print):
        """Test generating final reports for failed automation"""
        # Arrange
        self.automator.stats.generate_final_report.return_value = "Failure Report Content"
        self.automator.stats.save_detailed_report.return_value = False
        
        # Act
        self.automator._generate_final_reports(failed=True)
        
        # Assert
        self.automator.stats.save_detailed_report.assert_called_once_with("logs/automation_stats_failed.json")
        
        # Check print calls for failure case
        mock_print.assert_any_call("📊 GENERATING FINAL STATISTICS REPORT (AUTOMATION FAILED)")
        
        # Should not print the "saved to" message when save failed
        saved_message_printed = any(
            "Detailed statistics saved to" in str(call) 
            for call in mock_print.call_args_list
        )
        assert not saved_message_printed
    
    @patch('builtins.print')
    def test_generate_final_reports_exception_handling(self, mock_print):
        """Test generating final reports when an exception occurs"""
        # Arrange
        self.automator.stats.generate_final_report.side_effect = Exception("Test error")
        
        # Act
        with patch('logging.error') as mock_log_error:
            self.automator._generate_final_reports(failed=False)
        
        # Assert
        mock_log_error.assert_called_once_with("Error generating final statistics report: Test error")