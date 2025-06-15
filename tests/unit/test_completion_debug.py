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

if __name__ == "__main__":
    test_completion_detection()