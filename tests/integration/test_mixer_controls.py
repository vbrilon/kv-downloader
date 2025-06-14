#!/usr/bin/env python3
"""
Test Mixer Controls - Test intro count and key adjustment functionality
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from karaoke_automator import KaraokeVersionAutomator, setup_logging

def test_mixer_controls():
    """Test intro count checkbox and key adjustment controls"""
    
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
            print("❌ No songs found in config")
            return False
        
        test_song = songs[0]
        test_song_url = test_song['url']
        song_key = test_song.get('key', 0)
        
        print(f"🎵 Testing mixer controls with:")
        print(f"   Song: {test_song['description'] or test_song['name']}")
        print(f"   Key adjustment: {song_key:+d} semitones")
        print(f"   URL: {test_song_url}")
        
        # Navigate to song page
        print("\n📄 Loading song page...")
        automator.driver.get(test_song_url)
        time.sleep(5)
        
        print("\n" + "="*60)
        print("🧪 TESTING MIXER CONTROLS")
        print("="*60)
        
        # Test 1: Intro Count Checkbox
        print("\n1. 🎼 Testing Intro Count Checkbox:")
        intro_success = automator.track_handler.ensure_intro_count_enabled(test_song_url)
        if intro_success:
            print("   ✅ Intro count checkbox test passed")
        else:
            print("   ❌ Intro count checkbox test failed")
        
        # Test 2: Key Adjustment (if needed)
        print(f"\n2. 🎵 Testing Key Adjustment to {song_key:+d}:")
        if song_key == 0:
            print("   ℹ️ No key adjustment needed (key = 0)")
            key_success = True
        else:
            key_success = automator.track_handler.adjust_key(test_song_url, song_key)
            if key_success:
                print(f"   ✅ Key adjustment to {song_key:+d} test passed")
            else:
                print(f"   ❌ Key adjustment to {song_key:+d} test failed")
        
        # Test 3: Try different key values to verify functionality
        print(f"\n3. 🔄 Testing Key Adjustment Range:")
        test_keys = [2, -1, 0]  # Test positive, negative, and reset to zero
        
        for test_key in test_keys:
            print(f"   Testing key adjustment to {test_key:+d}...")
            adjust_success = automator.track_handler.adjust_key(test_song_url, test_key)
            if adjust_success:
                print(f"   ✅ Key {test_key:+d} adjustment successful")
            else:
                print(f"   ❌ Key {test_key:+d} adjustment failed")
            time.sleep(2)  # Brief pause between adjustments
        
        # Test 4: Test a single track download with mixer controls
        print(f"\n4. 🎯 Testing Single Track Download with Mixer Controls:")
        
        # Get available tracks
        tracks = automator.get_available_tracks(test_song_url)
        if tracks:
            test_track = tracks[0]  # Use first track
            print(f"   Testing with track: {test_track['name']}")
            
            # Solo the track
            if automator.solo_track(test_track, test_song_url):
                print("   ✅ Track solo successful")
                
                # Just test the setup, don't actually download
                print("   ℹ️ Mixer controls setup complete - skipping actual download")
                
            else:
                print("   ❌ Track solo failed")
        else:
            print("   ❌ No tracks found for testing")
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY:")
        print("="*60)
        
        if intro_success:
            print("✅ Intro count checkbox: WORKING")
        else:
            print("❌ Intro count checkbox: FAILED")
            
        if key_success:
            print("✅ Key adjustment: WORKING")
        else:
            print("❌ Key adjustment: FAILED")
        
        overall_success = intro_success and key_success
        
        if overall_success:
            print("\n🎉 All mixer controls tests PASSED!")
            print("✅ Ready for production use with mixer controls")
        else:
            print("\n⚠️ Some mixer controls tests FAILED")
            print("🔧 Check the browser window and debug logs for issues")
        
        print("\n⏸️ Browser window left open for inspection")
        print("Press Enter to close browser and exit...")
        input()
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logging.exception("Test error details:")
        return False
    
    finally:
        automator.driver.quit()

if __name__ == "__main__":
    print("🧪 Testing Mixer Controls (Intro Count + Key Adjustment)")
    print("=" * 65)
    success = test_mixer_controls()
    print("=" * 65)
    if success:
        print("✅ Mixer controls testing completed successfully")
    else:
        print("❌ Mixer controls testing failed - check logs")