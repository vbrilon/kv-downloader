#!/usr/bin/env python3
"""
Login test with correct selectors discovered from form inspection
"""

import time
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
import config

def working_login_test():
    """Login with the correct selectors"""
    print("🔐 WORKING LOGIN TEST")
    print("="*40)
    
    if not config.USERNAME or not config.PASSWORD:
        print("❌ No credentials configured")
        return False
    
    print(f"Using: {config.USERNAME}")
    
    # Setup Chrome
    chrome_options = Options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Step 1: Go to homepage
        print("\n📱 Going to homepage...")
        driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # Step 2: Click login
        print("🔗 Clicking login link...")
        login_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Log in')]")
        login_link.click()
        time.sleep(3)
        
        print(f"Login page: {driver.current_url}")
        
        # Step 3: Find fields with correct names
        print("📧 Finding login fields with correct selectors...")
        
        try:
            email_field = driver.find_element(By.NAME, "frm_login")
            print("✅ Found email field: name='frm_login'")
        except:
            print("❌ Could not find frm_login field")
            return False
        
        try:
            password_field = driver.find_element(By.NAME, "frm_password")
            print("✅ Found password field: name='frm_password'")
        except:
            print("❌ Could not find frm_password field")
            return False
        
        try:
            submit_button = driver.find_element(By.NAME, "sbm")
            print("✅ Found submit button: name='sbm'")
        except:
            print("❌ Could not find sbm button")
            return False
        
        # Step 4: Fill in credentials
        print("✏️ Filling credentials...")
        
        email_field.clear()
        email_field.send_keys(config.USERNAME)
        print(f"✅ Entered email: {config.USERNAME}")
        
        password_field.clear()
        password_field.send_keys(config.PASSWORD)
        print("✅ Entered password")
        
        # Step 5: Submit
        print("🚀 Submitting login form...")
        submit_button.click()
        
        # Step 6: Wait and verify
        print("⏳ Waiting for login to complete...")
        time.sleep(5)
        
        print(f"URL after login: {driver.current_url}")
        
        # Check for "My Account" to verify login success
        my_account_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'My Account')]")
        
        if my_account_elements:
            print("🎉 LOGIN SUCCESS! Found 'My Account' in header")
            
            # Test access to protected content
            print("\n🎵 Testing access to song page...")
            test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
            driver.get(test_url)
            time.sleep(5)
            
            # Check for tracks
            tracks = driver.find_elements(By.CSS_SELECTOR, ".track")
            if tracks:
                print(f"✅ SUCCESS! Can access song content - found {len(tracks)} tracks")
                
                # Show first few tracks
                print("Available tracks:")
                for i, track in enumerate(tracks[:5]):
                    try:
                        track_name = track.find_element(By.CSS_SELECTOR, ".track__caption").text
                        data_index = track.get_attribute('data-index')
                        print(f"  {i+1}. Track {data_index}: {track_name}")
                    except:
                        print(f"  {i+1}. Track {i} (couldn't get name)")
                
                if len(tracks) > 5:
                    print(f"  ... and {len(tracks) - 5} more tracks")
                
                login_success = True
            else:
                print("⚠️ Logged in but no tracks found on song page")
                login_success = True  # Still consider login successful
                
        else:
            print("❌ LOGIN FAILED - 'My Account' not found")
            login_success = False
        
        # Keep browser open for verification
        print("\n🔍 Browser staying open for 30 seconds for manual verification...")
        print("Please verify login status and track access manually.")
        time.sleep(30)
        
        return login_success
        
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    success = working_login_test()
    print(f"\n{'='*40}")
    print(f"FINAL RESULT: {'SUCCESS' if success else 'FAILED'}")
    print(f"{'='*40}")