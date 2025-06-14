#!/usr/bin/env python3
"""
Test the new modular login system
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def test_modular_login():
    """Test the modular login system"""
    print("🔐 TESTING MODULAR LOGIN SYSTEM")
    print("="*40)
    
    try:
        # Initialize automator
        print("1️⃣ Initializing modular automator...")
        automator = KaraokeVersionAutomator()
        
        # Test login
        print("2️⃣ Testing centralized login...")
        login_success = automator.login()
        
        if login_success:
            print("✅ Login successful!")
            
            # Test track discovery
            print("3️⃣ Testing track discovery...")
            test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
            tracks = automator.get_available_tracks(test_url)
            
            if tracks:
                print(f"✅ Found {len(tracks)} tracks:")
                for i, track in enumerate(tracks[:3]):
                    print(f"  {i+1}. Track {track['index']}: {track['name']}")
                if len(tracks) > 3:
                    print(f"  ... and {len(tracks) - 3} more tracks")
                
                print("\n🎉 MODULAR SYSTEM WORKING PERFECTLY!")
                success = True
            else:
                print("❌ Track discovery failed")
                success = False
        else:
            print("❌ Login failed")
            success = False
        
        return success
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_modular_login()
    print(f"\n{'='*40}")
    print(f"MODULAR TEST: {'SUCCESS' if success else 'FAILED'}")
    print(f"{'='*40}")