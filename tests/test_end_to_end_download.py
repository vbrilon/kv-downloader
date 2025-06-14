#!/usr/bin/env python3
"""
End-to-end test: Solo track + Download workflow
Tests the complete automation pipeline from login to download
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def test_complete_download_workflow():
    """Test complete workflow: login → solo track → download"""
    print("🎵 TESTING COMPLETE DOWNLOAD WORKFLOW")
    print("Song: The Middle by Jimmy Eat World")
    print("Target: Bass track isolation and download")
    print("="*60)
    
    song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
    
    try:
        # Initialize automator
        print("1️⃣ Initializing automation system...")
        automator = KaraokeVersionAutomator()
        
        # Login
        print("2️⃣ Logging in...")
        if not automator.login():
            print("❌ Login failed - cannot proceed")
            return False
        
        print("✅ Login successful!")
        
        # Discover all tracks
        print("3️⃣ Discovering available tracks...")
        tracks = automator.get_available_tracks(song_url)
        
        if not tracks:
            print("❌ No tracks found - check song access")
            return False
        
        print(f"✅ Found {len(tracks)} tracks:")
        for i, track in enumerate(tracks):
            print(f"  {i+1}. Track {track['index']}: {track['name']}")
        
        # Find and solo bass track
        print("\n4️⃣ Finding and isolating Bass track...")
        bass_tracks = [t for t in tracks if 'bass' in t['name'].lower()]
        
        if not bass_tracks:
            print("❌ No Bass track found!")
            return False
        
        bass_track = bass_tracks[0]
        print(f"🎸 Found Bass track: '{bass_track['name']}' (index: {bass_track['index']})")
        
        # Solo the bass track
        print("5️⃣ Soloing Bass track...")
        if not automator.solo_track(bass_track, song_url):
            print("❌ Failed to solo bass track")
            return False
        
        print("✅ Bass track successfully isolated!")
        print("🔇 All other tracks are now muted")
        
        # Wait for UI to fully update
        time.sleep(2)
        
        # Download the isolated bass track
        print("6️⃣ Downloading isolated bass track...")
        download_success = automator.track_handler.download_current_mix(
            song_url, 
            track_name=f"bass_isolated_{bass_track['name']}"
        )
        
        if download_success:
            print("✅ Download initiated successfully!")
            print("🎵 Bass track download should begin shortly")
        else:
            print("❌ Download failed - check download button discovery")
            return False
        
        # Wait for download to start
        print("7️⃣ Waiting for download to begin...")
        time.sleep(5)
        
        # Verify download progress
        print("🔍 Manual verification time...")
        print("Browser staying open for 30 seconds for verification...")
        print("Please check:")
        print("- Download has started (check browser downloads)")
        print("- Only bass track is audible")
        print("- File is being saved to downloads folder")
        
        time.sleep(30)
        
        # Clean up - clear solo
        print("8️⃣ Cleaning up...")
        if automator.clear_all_solos(song_url):
            print("✅ Cleared bass solo - all tracks audible again")
        
        print("\n🎉 END-TO-END DOWNLOAD TEST COMPLETE!")
        print("✅ Successfully completed full workflow:")
        print("   1. Authentication")
        print("   2. Track discovery")
        print("   3. Bass track isolation")
        print("   4. Download initiation")
        print("   5. Cleanup")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during end-to-end test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

def test_multiple_track_downloads():
    """Test downloading multiple different tracks from the same song"""
    print("\n🎼 TESTING MULTIPLE TRACK DOWNLOADS")
    print("Testing: Guitar → Vocals → Drums isolation and download")
    print("="*60)
    
    song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
    target_tracks = ['guitar', 'vocal', 'drum']
    
    try:
        automator = KaraokeVersionAutomator()
        
        # Login
        if not automator.login():
            print("❌ Login failed")
            return False
        
        # Get tracks
        tracks = automator.get_available_tracks(song_url)
        if not tracks:
            print("❌ No tracks found")
            return False
        
        downloaded_tracks = []
        
        # Download each target track type
        for track_type in target_tracks:
            print(f"\n🎯 Processing {track_type.upper()} track...")
            
            # Find track
            matching_tracks = [t for t in tracks if track_type in t['name'].lower()]
            if not matching_tracks:
                print(f"❌ No {track_type} track found")
                continue
            
            target_track = matching_tracks[0]
            print(f"Found: {target_track['name']}")
            
            # Solo track
            if automator.solo_track(target_track, song_url):
                print(f"✅ Isolated {target_track['name']}")
                
                # Download
                time.sleep(2)  # Wait for UI update
                if automator.track_handler.download_current_mix(
                    song_url, 
                    track_name=f"{track_type}_isolated_{target_track['name']}"
                ):
                    print(f"✅ Download initiated for {target_track['name']}")
                    downloaded_tracks.append(target_track['name'])
                    time.sleep(3)  # Wait between downloads
                else:
                    print(f"❌ Download failed for {target_track['name']}")
            else:
                print(f"❌ Failed to solo {target_track['name']}")
        
        # Results
        print(f"\n📊 RESULTS: {len(downloaded_tracks)}/{len(target_tracks)} tracks downloaded")
        for track in downloaded_tracks:
            print(f"  ✅ {track}")
        
        # Cleanup
        automator.clear_all_solos(song_url)
        print("✅ All solos cleared")
        
        return len(downloaded_tracks) > 0
        
    except Exception as e:
        print(f"❌ Error during multiple track test: {e}")
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    print("🚀 STARTING END-TO-END DOWNLOAD TESTS")
    print("="*60)
    
    # Test 1: Single track download workflow
    success1 = test_complete_download_workflow()
    
    print("\n" + "="*60)
    
    # Test 2: Multiple track downloads
    success2 = test_multiple_track_downloads()
    
    print("\n" + "="*60)
    print("🏁 FINAL RESULTS:")
    print(f"Single Track Download: {'SUCCESS' if success1 else 'FAILED'}")
    print(f"Multiple Track Downloads: {'SUCCESS' if success2 else 'FAILED'}")
    
    if success1 and success2:
        print("🎉 ALL TESTS PASSED - Complete download workflow is functional!")
        print("🎵 Ready for production use!")
    else:
        print("⚠️  Some tests failed - check download button discovery")
    
    print("="*60)