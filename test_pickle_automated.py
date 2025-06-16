#!/usr/bin/env python3
"""
Automated Pickle Persistence Testing
Simplified version for automated testing without interactive prompts
"""

import os
import sys
import time
import pickle
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from karaoke_automator import KaraokeVersionAutomator
from packages.browser.chrome_manager import ChromeManager
from packages.authentication.login_manager import LoginManager


def test_pickle_basics():
    """Quick automated test to check if pickle persistence is functional"""
    print("🧪 Automated Pickle Persistence Test")
    print("="*50)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('pickle_test')
    
    # Check current session file
    session_file = '.cache/session_data.pkl'
    print(f"\n📁 Checking session file: {session_file}")
    
    if os.path.exists(session_file):
        print("   ✅ Session file exists")
        
        # Examine contents
        try:
            with open(session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            print(f"   📊 Session data keys: {list(session_data.keys())}")
            print(f"   📊 Cookies count: {len(session_data.get('cookies', []))}")
            print(f"   📊 localStorage count: {len(session_data.get('localStorage', {}))}")
            print(f"   📊 sessionStorage count: {len(session_data.get('sessionStorage', {}))}")
            
            # Check timestamp
            timestamp = session_data.get('timestamp', 0)
            age_hours = (time.time() - timestamp) / 3600
            print(f"   📊 Session age: {age_hours:.1f} hours")
            
            if age_hours > 24:
                print("   ⚠️  Session is expired (>24 hours)")
            else:
                print("   ✅ Session is within 24-hour window")
                
        except Exception as e:
            print(f"   ❌ Error reading session file: {e}")
            return False
            
    else:
        print("   ❌ No session file exists")
        return False
    
    print(f"\n🧪 Testing pickle restoration (headless mode)...")
    
    try:
        # Create temporary Chrome profile for isolated testing
        temp_dir = tempfile.mkdtemp(prefix="pickle_test_")
        print(f"   📁 Using temporary Chrome profile: {temp_dir}")
        
        # Patch ChromeManager to use temporary profile
        original_configure = ChromeManager._configure_chrome_options
        
        def test_configure_chrome_options(self):
            # Get base options
            options = original_configure(self)
            
            # Create new options with temporary profile
            from selenium.webdriver.chrome.options import Options
            test_options = Options()
            
            # Copy all arguments except user-data-dir
            for arg in options.arguments:
                if not arg.startswith("--user-data-dir"):
                    test_options.add_argument(arg)
            
            # Add temporary user data dir
            test_user_data = os.path.join(temp_dir, "test_profile")
            test_options.add_argument(f"--user-data-dir={test_user_data}")
            test_options.add_argument("--no-first-run")
            
            # Copy experimental options
            if hasattr(options, '_experimental_options'):
                for key, value in options._experimental_options.items():
                    test_options.add_experimental_option(key, value)
            
            print(f"   🔧 Using isolated Chrome profile: {test_user_data}")
            return test_options
            
        ChromeManager._configure_chrome_options = test_configure_chrome_options
        
        # Test restoration
        automator = KaraokeVersionAutomator(headless=True, show_progress=False)
        
        print("   🔄 Attempting load_session()...")
        start_time = time.time()
        restoration_result = automator.login_handler.load_session()
        restoration_time = time.time() - start_time
        
        print(f"   📊 load_session() returned: {restoration_result}")
        print(f"   📊 Restoration time: {restoration_time:.2f}s")
        
        # Test account page access
        print("   🔍 Testing account page access...")
        automator.driver.get("https://www.karaoke-version.com/account")
        time.sleep(3)
        
        current_url = automator.driver.current_url
        page_source = automator.driver.page_source
        
        print(f"   📍 Current URL: {current_url}")
        
        # Check login indicators
        indicators = [
            ("My Account" in page_source, "My Account text found"),
            ("login" not in current_url.lower(), "Not on login page"),
            ("account" in current_url.lower(), "On account page"),
            ("sign in" not in page_source.lower(), "No sign in prompt")
        ]
        
        passed = [desc for success, desc in indicators if success]
        failed = [desc for success, desc in indicators if not success]
        
        print(f"   ✅ Passed indicators: {passed}")
        if failed:
            print(f"   ❌ Failed indicators: {failed}")
        
        # Determine success
        success_score = len(passed) / len(indicators)
        is_working = success_score >= 0.75  # At least 3 of 4 indicators
        
        print(f"\n📊 AUTOMATED TEST RESULTS:")
        print(f"   Success rate: {success_score*100:.1f}%")
        print(f"   Restoration returned: {restoration_result}")
        print(f"   Time: {restoration_time:.2f}s")
        
        if is_working:
            print("   🎉 PICKLE PERSISTENCE APPEARS TO BE WORKING")
            recommendation = "KEEP"
        else:
            print("   ❌ PICKLE PERSISTENCE APPEARS TO BE BROKEN")
            recommendation = "REMOVE"
        
        # Cleanup
        automator.driver.quit()
        ChromeManager._configure_chrome_options = original_configure
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return recommendation
        
    except Exception as e:
        print(f"   ❌ Test failed with error: {e}")
        # Cleanup on error
        try:
            if 'automator' in locals():
                automator.driver.quit()
            if 'original_configure' in locals():
                ChromeManager._configure_chrome_options = original_configure
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
        return "ERROR"


if __name__ == "__main__":
    result = test_pickle_basics()
    print(f"\n🎯 RECOMMENDATION: {result}")
    
    if result == "KEEP":
        print("   📋 Pickle persistence is functional - maintain dual approach")
    elif result == "REMOVE":
        print("   📋 Pickle persistence is broken - simplify to Chrome-only")
    else:
        print("   📋 Test encountered errors - manual investigation needed")