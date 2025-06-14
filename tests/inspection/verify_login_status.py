#!/usr/bin/env python3
"""
Verify current login status and test access to protected content
"""

import time
import logging
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def verify_login_and_access():
    """Verify login status and test access to song page"""
    print("🔍 VERIFYING LOGIN STATUS AND ACCESS")
    print("="*60)
    
    # Setup Chrome driver
    chrome_options = Options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Step 1: Check homepage login status
        print("\n1️⃣ Checking homepage login status...")
        driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        print(f"Page title: {driver.title}")
        
        # Look specifically for "Hello" greeting
        hello_elements = driver.find_elements(By.XPATH, "//*[starts-with(normalize-space(text()), 'Hello')]")
        
        if hello_elements:
            for elem in hello_elements:
                text = elem.text.strip()
                if text.startswith('Hello') and len(text) < 50:  # Reasonable length for greeting
                    print(f"✅ Found login greeting: '{text}'")
                    logged_in = True
                    break
            else:
                print("⚠️ Found 'Hello' elements but none look like login greetings")
                logged_in = False
        else:
            print("❌ No 'Hello' greeting found")
            logged_in = False
        
        # Alternative check: look for "Log In" links
        login_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Log in')]")
        if login_links:
            print(f"❌ Found {len(login_links)} 'Log in' links - appears NOT logged in")
            logged_in = False
        else:
            print("✅ No 'Log in' links found - appears logged in")
            logged_in = True
        
        # Step 2: Test access to protected song page
        print(f"\n2️⃣ Testing access to song page...")
        test_song_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        print(f"Navigating to: {test_song_url}")
        
        driver.get(test_song_url)
        time.sleep(5)
        
        current_url = driver.current_url
        print(f"Current URL: {current_url}")
        
        # Check if we were redirected to login
        if "login" in current_url.lower():
            print("❌ Redirected to login page - not logged in")
            song_access = False
        else:
            print("✅ Not redirected to login page")
            song_access = True
        
        # Step 3: Check for track elements (indicates proper access)
        print(f"\n3️⃣ Checking for track elements...")
        track_elements = driver.find_elements(By.CSS_SELECTOR, ".track")
        
        if track_elements:
            print(f"✅ Found {len(track_elements)} track elements - have access to content")
            
            # Show first few tracks
            print("Track details:")
            for i, track in enumerate(track_elements[:5]):
                try:
                    track_name = track.find_element(By.CSS_SELECTOR, ".track__caption").text
                    data_index = track.get_attribute('data-index')
                    print(f"  {i+1}. Track {data_index}: '{track_name}'")
                except:
                    print(f"  {i+1}. Track element found but couldn't extract details")
            
            if len(track_elements) > 5:
                print(f"  ... and {len(track_elements) - 5} more tracks")
                
            track_access = True
        else:
            print("❌ No track elements found - may not have access")
            track_access = False
        
        # Step 4: Look for any login prompts on the page
        print(f"\n4️⃣ Checking for login prompts...")
        page_source = driver.page_source.lower()
        
        login_keywords = ["please log in", "sign in to access", "login required", "please sign in"]
        login_prompts_found = []
        
        for keyword in login_keywords:
            if keyword in page_source:
                login_prompts_found.append(keyword)
        
        if login_prompts_found:
            print(f"❌ Found login prompts: {login_prompts_found}")
            requires_login = True
        else:
            print("✅ No login prompts found")
            requires_login = False
        
        # Final assessment
        print(f"\n" + "="*60)
        print("📊 FINAL ASSESSMENT")
        print("="*60)
        print(f"Login Status Detection: {'✅ PASS' if logged_in else '❌ FAIL'}")
        print(f"Song Page Access: {'✅ PASS' if song_access else '❌ FAIL'}")
        print(f"Track Content Access: {'✅ PASS' if track_access else '❌ FAIL'}")
        print(f"No Login Required: {'✅ PASS' if not requires_login else '❌ FAIL'}")
        
        overall_success = logged_in and song_access and track_access and not requires_login
        
        if overall_success:
            print(f"\n🎉 OVERALL: SUCCESS - You are logged in with full access!")
        else:
            print(f"\n⚠️ OVERALL: ISSUES DETECTED - Login or access problems")
        
        # Keep browser open for manual verification
        print(f"\n🔍 Browser staying open for 30 seconds for manual verification...")
        print("Please manually verify the login status and content access.")
        time.sleep(30)
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    success = verify_login_and_access()
    print(f"\nVerification result: {'SUCCESS' if success else 'FAILED'}")