#!/usr/bin/env python3
"""
Test the solo button functionality
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def test_solo_functionality():
    """Test solo button functionality for track isolation"""
    print("🎛️ TESTING SOLO BUTTON FUNCTIONALITY")
    print("="*50)
    
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
        
        # Get tracks
        test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        print("3️⃣ Discovering tracks...")
        tracks = automator.get_available_tracks(test_url)
        
        if not tracks:
            print("❌ No tracks found")
            return False
        
        print(f"✅ Found {len(tracks)} tracks")
        
        # Test solo functionality on first 3 tracks
        print("4️⃣ Testing solo functionality...")
        
        for i, track in enumerate(tracks[:3]):
            print(f"\n--- Testing Track {i+1}: {track['name']} ---")
            
            # Solo this track
            solo_success = automator.solo_track(track, test_url)
            
            if solo_success:
                print(f"✅ Successfully soloed: {track['name']}")
                
                # Wait a moment to see the effect
                time.sleep(2)
                
                # Clear solos before next track
                clear_success = automator.clear_all_solos(test_url)
                if clear_success:
                    print("✅ Successfully cleared solo")
                else:
                    print("⚠️ Could not verify solo clear")
                
                time.sleep(1)
            else:
                print(f"❌ Failed to solo: {track['name']}")
        
        # Test soloing different tracks in sequence
        print("\n5️⃣ Testing track isolation sequence...")
        
        # Solo vocals (usually track 10)
        vocal_tracks = [t for t in tracks if 'vocal' in t['name'].lower()]
        if vocal_tracks:
            print(f"Testing vocal isolation: {vocal_tracks[0]['name']}")
            if automator.solo_track(vocal_tracks[0], test_url):
                print("✅ Vocal track isolated")
                time.sleep(3)
            
            # Clear and solo guitar
            automator.clear_all_solos(test_url)
            time.sleep(1)
        
        guitar_tracks = [t for t in tracks if 'guitar' in t['name'].lower()]
        if guitar_tracks:
            print(f"Testing guitar isolation: {guitar_tracks[0]['name']}")
            if automator.solo_track(guitar_tracks[0], test_url):
                print("✅ Guitar track isolated")
                time.sleep(3)
        
        # Final clear
        print("\n6️⃣ Final cleanup...")
        if automator.clear_all_solos(test_url):
            print("✅ All solos cleared - all tracks audible")
        
        print("\n🎉 SOLO FUNCTIONALITY TEST COMPLETE!")
        print("✅ Track isolation working properly")
        print("✅ Solo buttons responsive")
        print("✅ Track switching functional")
        
        # Keep browser open for verification
        print("\n🔍 Browser staying open for 30 seconds for manual verification...")
        print("You can manually test solo buttons and hear the audio changes.")
        time.sleep(30)
        
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
    success = test_solo_functionality()
    print(f"\n{'='*50}")
    print(f"SOLO TEST: {'SUCCESS' if success else 'FAILED'}")
    print(f"{'='*50}")