#!/usr/bin/env python3
"""
Test script to verify the download logic fixes
- Tests single track download with simplified logic
- No cleanup, direct download to song folder only
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from karaoke_automator import KaraokeVersionAutomator, setup_logging

def test_single_track_download():
    """Test downloading a single track with the fixed logic"""
    
    # Setup debug logging
    setup_logging(debug_mode=True)
    
    # Initialize automator in debug mode (visible browser)
    automator = KaraokeVersionAutomator(headless=False, show_progress=True)
    
    try:
        # Login
        print("🔐 Logging in...")
        if not automator.login():
            print("❌ Login failed")
            return False
        
        # Get test song from config
        songs = automator.load_songs_config()
        if not songs:
            print("❌ No songs found in config - add a song to songs.yaml first")
            return False
        
        test_song = songs[0]  # Use first configured song
        test_song_url = test_song['url']
        print(f"🎵 Testing with song: {test_song['description'] or test_song['name']}")
        print(f"🔗 URL: {test_song_url}")
        
        # Get available tracks
        print("🔍 Discovering tracks...")
        tracks = automator.get_available_tracks(test_song_url)
        
        if not tracks:
            print("❌ No tracks found")
            return False
        
        print(f"✅ Found {len(tracks)} tracks:")
        for i, track in enumerate(tracks):
            print(f"  {i+1}. {track['name']} (index: {track['index']})")
        
        # Test with first track
        test_track = tracks[0]
        print(f"\n🎯 Testing download of: {test_track['name']}")
        
        # Check song folder before download
        song_folder_name = automator.download_manager.extract_song_folder_name(test_song_url)
        # Use the default download folder
        try:
            from packages.configuration import DOWNLOAD_FOLDER
        except ImportError:
            DOWNLOAD_FOLDER = "./downloads"
        song_path = Path(DOWNLOAD_FOLDER) / song_folder_name
        
        print(f"📁 Song folder: {song_path}")
        initial_files = list(song_path.glob("*")) if song_path.exists() else []
        print(f"📊 Initial files in folder: {len(initial_files)}")
        
        # Solo the track
        print(f"🎛️ Soloing track: {test_track['name']}")
        if not automator.solo_track(test_track, test_song_url):
            print("❌ Failed to solo track")
            return False
        
        print("✅ Track soloed successfully")
        
        # Attempt download with our fixed logic
        print("⬇️ Starting download...")
        track_name = automator.sanitize_filename(test_track['name'])
        
        download_success = automator.download_manager.download_current_mix(
            test_song_url,
            track_name,
            cleanup_existing=True,  # This is now commented out in the code
            song_folder=song_folder_name
        )
        
        if download_success:
            print("✅ Download started successfully!")
            print("📊 Monitoring download progress...")
            
            # Wait a bit to see progress updates
            import time
            for i in range(30):  # Check for 30 seconds
                time.sleep(1)
                
                # Check for current files in song folder
                current_files = list(song_path.glob("*")) if song_path.exists() else []
                crdownload_files = [f for f in current_files if f.name.endswith('.crdownload')]
                completed_files = [f for f in current_files if not f.name.endswith('.crdownload') and f.is_file()]
                
                if i % 5 == 0:  # Every 5 seconds
                    print(f"⏱️ {i+1}s: .crdownload files: {len(crdownload_files)}, completed: {len([f for f in completed_files if f not in initial_files])}")
                
                # If we have completed files that weren't there before, show progress
                new_completed = [f for f in completed_files if f not in initial_files and 'custom_backing_track' in f.name.lower()]
                if new_completed:
                    print(f"🎉 Download completed!")
                    for f in new_completed:
                        print(f"  📁 {f.name}")
                    break
            
            # Final check
            final_files = list(song_path.glob("*")) if song_path.exists() else []
            new_files = [f for f in final_files if f not in initial_files]
            
            print(f"\n📊 Final files in folder: {len(final_files)}")
            if new_files:
                print("🆕 New files detected:")
                for f in new_files:
                    file_age = time.time() - f.stat().st_mtime
                    is_crdownload = f.name.endswith('.crdownload')
                    status = "🔄 downloading" if is_crdownload else "✅ complete"
                    print(f"  - {f.name} ({file_age:.1f}s old) {status}")
            else:
                print("⚠️ No new files detected in song folder")
                
        else:
            print("❌ Download failed")
            return False
        
        print("\n🎉 Test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logging.exception("Test error details:")
        return False
    
    finally:
        # Keep browser open for inspection
        print("\n⏸️ Browser window left open for inspection")
        print("Automatically closing in 3 seconds...")
        time.sleep(3)
        automator.driver.quit()

if __name__ == "__main__":
    print("🧪 Testing download logic fixes...")
    print("=" * 50)
    success = test_single_track_download()
    print("=" * 50)
    if success:
        print("✅ Test completed - check results above")
    else:
        print("❌ Test failed - check logs for details")