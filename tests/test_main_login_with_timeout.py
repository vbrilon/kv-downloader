#!/usr/bin/env python3
"""
Test main.py login with timeout and better error handling
"""

import time
import logging
import sys
import signal
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
import main

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Test timed out")

def test_main_login_with_timeout():
    """Test main.py login with 60 second timeout"""
    print("🔐 TESTING MAIN.PY LOGIN WITH TIMEOUT")
    print("="*40)
    
    # Set 60 second timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)  # 60 second timeout
    
    try:
        # Initialize automator
        print("Initializing automator...")
        automator = main.KaraokeVersionAutomator()
        
        # Test login function
        print("Starting login process...")
        start_time = time.time()
        
        login_result = automator.login()
        
        end_time = time.time()
        print(f"Login completed in {end_time - start_time:.2f} seconds")
        print(f"Login result: {login_result}")
        
        if login_result:
            print("✅ Login reported success!")
            
            # Verify with status check
            status = automator.check_login_status()
            print(f"Status verification: {status}")
            
            if status:
                print("🎉 LOGIN FULLY SUCCESSFUL!")
                
                # Quick test of song access
                print("Testing song access...")
                test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
                automator.driver.get(test_url)
                time.sleep(3)
                
                tracks = automator.driver.find_elements(main.By.CSS_SELECTOR, ".track")
                if tracks:
                    print(f"✅ Can access song content - found {len(tracks)} tracks")
                else:
                    print("⚠️ No tracks found on song page")
                
                return True
            else:
                print("❌ Login status verification failed")
                return False
        else:
            print("❌ Login reported failure")
            return False
        
    except TimeoutError:
        print("❌ TEST TIMED OUT (60 seconds)")
        return False
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    finally:
        signal.alarm(0)  # Cancel timeout
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_main_login_with_timeout()
    print(f"\n{'='*40}")
    print(f"FINAL RESULT: {'SUCCESS' if success else 'FAILED'}")
    print(f"{'='*40}")