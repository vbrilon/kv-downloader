#!/usr/bin/env python3
"""
Test click interception fixes for solo buttons and download button
Validates JavaScript click fallback functionality
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def test_click_interception_fixes():
    """Test that click interception issues are resolved"""
    print("🔧 TESTING CLICK INTERCEPTION FIXES") 
    print("Validating JavaScript click fallbacks")
    print("="*60)
    
    song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
    
    try:
        # Initialize and login
        automator = KaraokeVersionAutomator()
        
        if not automator.login():
            print("❌ Login failed")
            return False
        
        print("✅ Login successful!")
        
        # Get tracks
        tracks = automator.get_available_tracks(song_url)
        print(f"✅ Found {len(tracks)} tracks")
        
        # Test tracks that previously had click interception issues
        test_tracks = []
        
        # Find bass track (worked before)
        bass_tracks = [t for t in tracks if 'bass' in t['name'].lower()]
        if bass_tracks:
            test_tracks.append(("Bass", bass_tracks[0]))
        
        # Find guitar track (had interception issue)
        guitar_tracks = [t for t in tracks if 'guitar' in t['name'].lower()]
        if guitar_tracks:
            test_tracks.append(("Guitar", guitar_tracks[0]))
        
        # Find vocal track (had interception issue) 
        vocal_tracks = [t for t in tracks if 'vocal' in t['name'].lower()]
        if vocal_tracks:
            test_tracks.append(("Vocals", vocal_tracks[0]))
        
        success_count = 0
        download_success_count = 0
        
        for track_type, track_info in test_tracks:
            print(f"\n🎯 Testing {track_type}: {track_info['name']}")
            
            # Test solo functionality with click interception fix
            if automator.solo_track(track_info, song_url):
                print(f"✅ Successfully soloed {track_info['name']}")
                success_count += 1
                
                # Test download functionality with click interception fix
                time.sleep(2)  # Wait for UI update
                print(f"⬇️ Testing download for {track_info['name']}...")
                
                if automator.track_handler.download_current_mix(
                    song_url, 
                    track_name=f"{track_type.lower()}_test_{track_info['name']}"
                ):
                    print(f"✅ Download initiated for {track_info['name']}")
                    download_success_count += 1
                    time.sleep(3)  # Wait between downloads
                else:
                    print(f"❌ Download failed for {track_info['name']}")
                
                # Clear solo before next test
                automator.clear_all_solos(song_url)
                time.sleep(1)
            else:
                print(f"❌ Failed to solo {track_info['name']}")
        
        # Results
        print(f"\n📊 CLICK INTERCEPTION FIX RESULTS:")
        print(f"Solo Tests: {success_count}/{len(test_tracks)} successful")
        print(f"Download Tests: {download_success_count}/{len(test_tracks)} successful")
        
        overall_success = success_count == len(test_tracks) and download_success_count >= 1
        
        if overall_success:
            print("🎉 Click interception fixes are working!")
            print("✅ JavaScript fallback clicks are functional")
        else:
            print("⚠️ Some click interception issues remain")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Error during click fix test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_click_interception_fixes()
    print(f"\n{'='*60}")
    print(f"CLICK INTERCEPTION FIX TEST: {'SUCCESS' if success else 'FAILED'}")
    print(f"{'='*60}")