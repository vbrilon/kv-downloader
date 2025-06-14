#!/usr/bin/env python3
"""
Test only the login function from main.py to debug the issue
"""

import time
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
import main

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_main_login_only():
    """Test only the login function"""
    print("🔐 TESTING MAIN.PY LOGIN FUNCTION")
    print("="*40)
    
    try:
        # Initialize automator
        automator = main.KaraokeVersionAutomator()
        
        # Test just the login function
        print("Calling automator.login()...")
        login_result = automator.login()
        
        print(f"Login result: {login_result}")
        
        if login_result:
            print("✅ Login reported success!")
            
            # Double-check login status
            status_check = automator.check_login_status()
            print(f"Status check result: {status_check}")
            
            if status_check:
                print("✅ Login status confirmed!")
            else:
                print("❌ Login status check failed")
        else:
            print("❌ Login reported failure")
        
        # Keep browser open for manual verification
        print("\n🔍 Browser staying open for 30 seconds...")
        print("Please manually verify if login worked")
        time.sleep(30)
        
        return login_result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_main_login_only()
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")