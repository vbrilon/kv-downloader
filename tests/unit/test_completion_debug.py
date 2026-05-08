#!/usr/bin/env python3
"""
Test completion detection logic
"""

import tempfile
from pathlib import Path
import time

# Add project root to path
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
from packages.file_operations import FileManager

def test_completion_detection():
    """Test completion detection with actual filenames"""
    print("🧪 Testing completion detection logic")
    print("="*50)
    
    test_filename = "Deep_Purple_Black_Night(Drum_Kit_Custom_Backing_Track).mp3"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        file_manager = FileManager()
        
        # Create test file
        test_file = temp_path / test_filename
        test_file.write_text("test mp3 content")
        
        print(f"Created test file: {test_filename}")
        print(f"File length: {len(test_filename)}")
        
        # Test the logic manually
        filename = test_file.name.lower()
        print(f"Filename lowercase: {filename}")
        
        # Check individual conditions
        is_audio = any(filename.endswith(ext) for ext in ['.mp3', '.aif', '.wav', '.m4a'])
        is_recent = (time.time() - test_file.stat().st_mtime) < 120
        might_be_karaoke = any(keyword in filename for keyword in [
            'custom', 'backing', 'track', 'karaoke'
        ]) or len(test_file.name) > 25
        
        print(f"is_audio: {is_audio}")
        print(f"is_recent: {is_recent}")
        print(f"might_be_karaoke: {might_be_karaoke}")
        
        keyword_matches = [keyword for keyword in ['custom', 'backing', 'track', 'karaoke'] if keyword in filename]
        print(f"Keyword matches: {keyword_matches}")
        
        # Test file manager
        print("\nTesting FileManager.check_for_completed_downloads():")
        completed_files = file_manager.check_for_completed_downloads(temp_path, "Drum_Kit")
        print(f"Completed files found: {len(completed_files)}")
        for f in completed_files:
            print(f"  - {f.name}")
        
        # Test filename cleanup
        print("\nTesting FileManager.clean_downloaded_filename():")
        result = file_manager.clean_downloaded_filename(test_file)
        print(f"Cleanup result: {result.name}")
        print(f"File exists after cleanup: {result.exists()}")


def test_monitor_progress_scans_before_first_sleep(mocker):
    """When the file is already present, completion must be detected before any
    interval sleep on iteration 0. Verifies via call ordering, not wall time
    (mocked sleeps don't actually wait)."""
    from packages.download_management.download_manager import DownloadManager

    call_order = []

    def _record(name, value):
        call_order.append(name)
        return value

    dm = mocker.Mock(spec=DownloadManager)
    dm._wait_for_download_readiness = mocker.Mock(return_value=True)
    dm._wait_for_check_interval = mocker.Mock(side_effect=lambda i: call_order.append('sleep'))
    dm._check_for_in_progress_downloads = mocker.Mock(side_effect=lambda p: _record('check_in_progress', []))
    dm._check_for_new_downloads = mocker.Mock(side_effect=lambda c: _record('check_completed', ["fake_completed_file"]))
    dm._handle_completed_download = mocker.Mock(side_effect=lambda *a, **k: call_order.append('handle_completed'))
    dm._update_progress_if_needed = mocker.Mock()
    dm._handle_timeout = mocker.Mock(side_effect=lambda *a: call_order.append('timeout'))

    context = {
        'track_name': 'Bass', 'song_name': 'Test', 'song_path': mocker.Mock(),
        'max_wait': 90, 'check_interval': 3, 'waited': 0, 'initial_files': set()
    }

    DownloadManager._monitor_download_progress(dm, context, track_index=3)

    # The first scan must complete before any sleep on the fast path.
    # Old (broken) order would be: ['sleep', 'check_in_progress', 'check_completed', 'handle_completed']
    # New (fixed) order is:        ['check_in_progress', 'check_completed', 'handle_completed']
    assert 'handle_completed' in call_order, "Should have handled the completed file"
    handle_idx = call_order.index('handle_completed')
    sleeps_before_handle = [c for c in call_order[:handle_idx] if c == 'sleep']
    assert sleeps_before_handle == [], (
        f"Expected zero interval sleeps before handling the already-present file, "
        f"got: {call_order}"
    )
    dm._handle_timeout.assert_not_called()


def test_monitor_progress_times_out_when_no_file_appears(mocker):
    """When max_wait elapses without a completed file, _handle_timeout must fire
    exactly once with the right args."""
    from packages.download_management.download_manager import DownloadManager

    dm = mocker.Mock(spec=DownloadManager)
    dm._wait_for_download_readiness = mocker.Mock(return_value=True)
    dm._wait_for_check_interval = mocker.Mock()
    dm._check_for_in_progress_downloads = mocker.Mock(return_value=[])
    dm._check_for_new_downloads = mocker.Mock(return_value=[])  # never finds a file
    dm._handle_completed_download = mocker.Mock()
    dm._update_progress_if_needed = mocker.Mock()
    dm._handle_timeout = mocker.Mock()

    context = {
        'track_name': 'Bass', 'song_name': 'Test', 'song_path': mocker.Mock(),
        'max_wait': 10, 'check_interval': 3, 'waited': 0, 'initial_files': set()
    }

    DownloadManager._monitor_download_progress(dm, context, track_index=3)

    dm._handle_completed_download.assert_not_called()
    dm._handle_timeout.assert_called_once_with('Bass', 3, 'Test')

if __name__ == "__main__":
    test_completion_detection()