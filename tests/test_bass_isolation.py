#!/usr/bin/env python3
"""
Test bass track isolation on "The Middle" by Jimmy Eat World
This test will login, find the bass track, and solo it for download preparation
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def test_bass_isolation():
    """Test bass track isolation on The Middle by Jimmy Eat World"""
    print("🎸 TESTING BASS TRACK ISOLATION")
    print("Song: The Middle by Jimmy Eat World")
    print("="*60)
    
    song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
    
    try:
        # Initialize automator
        print("1️⃣ Initializing automator...")
        automator = KaraokeVersionAutomator()
        
        # Login
        print("2️⃣ Logging in...")
        if not automator.login():
            print("❌ Login failed")
            return False
        
        print("✅ Login successful!")
        
        # Discover tracks
        print("3️⃣ Discovering tracks on The Middle...")
        tracks = automator.get_available_tracks(song_url)
        
        if not tracks:
            print("❌ No tracks found")
            return False
        
        print(f"✅ Found {len(tracks)} tracks:")
        for i, track in enumerate(tracks):
            print(f"  {i+1}. Track {track['index']}: {track['name']}")
        
        # Find bass track
        print("\n4️⃣ Looking for Bass track...")
        bass_tracks = [t for t in tracks if 'bass' in t['name'].lower()]
        
        if not bass_tracks:
            print("❌ No Bass track found!")
            print("Available tracks with 'bass' in name:")
            for track in tracks:
                if 'bass' in track['name'].lower():
                    print(f"  - {track['name']}")
            return False
        
        bass_track = bass_tracks[0]
        print(f"✅ Found Bass track: '{bass_track['name']}' (index: {bass_track['index']})")
        
        # Solo the bass track
        print("5️⃣ Soloing Bass track...")
        if automator.solo_track(bass_track, song_url):
            print(f"✅ Successfully isolated Bass track: {bass_track['name']}")
            print("🔇 All other tracks are now muted")
            print("🎸 Only the bass line should be audible")
        else:
            print("❌ Failed to solo Bass track")
            return False
        
        # Keep isolated for verification
        print("\n6️⃣ Bass track isolated and ready...")
        print("🎵 The bass track is now isolated and ready for download")
        print("📡 In a complete system, download would begin here")
        
        # Manual verification time
        print("\n🔍 Browser staying open for 45 seconds for verification...")
        print("Please verify:")
        print("- Only bass guitar is audible")
        print("- Solo button for bass track appears active")
        print("- Other instruments are muted")
        print("- Download button location (for future implementation)")
        
        time.sleep(45)
        
        # Clear solo before ending
        print("\n7️⃣ Cleaning up...")
        if automator.clear_all_solos(song_url):
            print("✅ Cleared bass solo - all tracks audible again")
        
        print("\n🎉 BASS ISOLATION TEST COMPLETE!")
        print("✅ Successfully found and isolated bass track")
        print("✅ Ready for download implementation")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_bass_isolation()
    print(f"\n{'='*60}")
    print(f"BASS ISOLATION TEST: {'SUCCESS' if success else 'FAILED'}")
    if success:
        print("🎸 Bass track successfully isolated and ready for download!")
    print(f"{'='*60}")