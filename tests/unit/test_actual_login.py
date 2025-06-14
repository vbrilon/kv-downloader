#!/usr/bin/env python3
"""
Test actual login process and verify with "My Account" indicator
"""

import time
import logging
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_actual_login():
    """Test the actual login process and verify with My Account"""
    print("🔐 TESTING ACTUAL LOGIN PROCESS")
    print("="*60)
    
    if not config.USERNAME or not config.PASSWORD:
        print("❌ Credentials not configured in .env file")
        return False
    
    print(f"Using credentials: {config.USERNAME}")
    
    # Setup Chrome driver
    chrome_options = Options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 15)
    
    try:
        # Step 1: Navigate to homepage
        print("\n1️⃣ Navigating to homepage...")
        driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # Step 2: Check if already logged in by looking for "My Account"
        print("\n2️⃣ Checking if already logged in...")
        my_account_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'My Account')]")
        
        if my_account_elements:
            print("✅ Already logged in - found 'My Account' in header")
            return True
        else:
            print("❌ Not logged in - 'My Account' not found")
        
        # Step 3: Find and click Login link
        print("\n3️⃣ Looking for Login link...")
        login_selectors = [
            "//a[contains(text(), 'Log in')]",
            "//a[contains(text(), 'Login')]", 
            "//a[contains(text(), 'Sign in')]",
            "//a[contains(text(), 'Sign In')]"
        ]
        
        login_clicked = False
        for selector in login_selectors:
            try:
                login_element = driver.find_element(By.XPATH, selector)
                if login_element.is_displayed():
                    print(f"✅ Found login link: '{login_element.text}'")
                    print(f"Clicking login link...")
                    login_element.click()
                    time.sleep(3)
                    login_clicked = True
                    break
            except Exception as e:
                print(f"Selector {selector} failed: {e}")
                continue
        
        if not login_clicked:
            print("❌ Could not find or click login link")
            return False
        
        print(f"Current URL after clicking login: {driver.current_url}")
        
        # Step 4: Find login form fields
        print("\n4️⃣ Looking for login form...")
        
        # Find email/username field
        email_selectors = [
            (By.NAME, "email"),
            (By.NAME, "username"), 
            (By.ID, "email"),
            (By.ID, "username"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email']")
        ]
        
        email_field = None
        for selector_type, selector_value in email_selectors:
            try:
                email_field = wait.until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                if email_field.is_displayed():
                    print(f"✅ Found email field: {selector_type}='{selector_value}'")
                    print(f"Field placeholder: '{email_field.get_attribute('placeholder')}'")
                    break
            except Exception as e:
                print(f"Email selector {selector_type}='{selector_value}' failed: {e}")
                continue
        
        if not email_field:
            print("❌ Could not find email field")
            print("Current page source contains:")
            if "email" in driver.page_source.lower():
                print("  - 'email' text found in page")
            if "username" in driver.page_source.lower():
                print("  - 'username' text found in page")
            return False
        
        # Find password field
        password_field = None
        try:
            password_field = driver.find_element(By.NAME, "password")
            print("✅ Found password field")
        except:
            try:
                password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                print("✅ Found password field by type")
            except Exception as e:
                print(f"❌ Could not find password field: {e}")
                return False
        
        # Step 5: Fill in credentials
        print("\n5️⃣ Filling in credentials...")
        
        email_field.clear()
        email_field.send_keys(config.USERNAME)
        print(f"✅ Entered username: {config.USERNAME}")
        
        password_field.clear()
        password_field.send_keys(config.PASSWORD)
        print("✅ Entered password")
        
        # Step 6: Submit form
        print("\n6️⃣ Submitting login form...")
        
        # Find submit button
        submit_selectors = [
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Log')]"),
            (By.XPATH, "//button[contains(text(), 'Sign')]"),
            (By.XPATH, "//input[contains(@value, 'Log')]")
        ]
        
        submit_button = None
        for selector_type, selector_value in submit_selectors:
            try:
                submit_button = driver.find_element(selector_type, selector_value)
                if submit_button.is_displayed():
                    print(f"✅ Found submit button: {selector_type}='{selector_value}'")
                    print(f"Button text: '{submit_button.text}' value: '{submit_button.get_attribute('value')}'")
                    break
            except:
                continue
        
        if not submit_button:
            print("❌ Could not find submit button")
            return False
        
        print("Clicking submit button...")
        submit_button.click()
        
        # Step 7: Wait and verify login
        print("\n7️⃣ Waiting for login to complete...")
        time.sleep(5)
        
        print(f"Current URL after login: {driver.current_url}")
        
        # Check for "My Account" to verify login success
        my_account_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'My Account')]")
        
        if my_account_elements:
            print("🎉 LOGIN SUCCESS! Found 'My Account' in header")
            
            # Test access to song page
            print("\n8️⃣ Testing access to protected song page...")
            test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
            driver.get(test_url)
            time.sleep(5)
            
            tracks = driver.find_elements(By.CSS_SELECTOR, ".track")
            if tracks:
                print(f"✅ Can access song content - found {len(tracks)} tracks")
                for i, track in enumerate(tracks[:3]):
                    try:
                        name = track.find_element(By.CSS_SELECTOR, ".track__caption").text
                        print(f"  Track {i+1}: {name}")
                    except:
                        pass
            else:
                print("⚠️ No tracks found on song page")
            
            login_success = True
        else:
            print("❌ LOGIN FAILED - 'My Account' not found")
            
            # Check for error messages
            error_indicators = ["error", "invalid", "incorrect", "failed"]
            page_text = driver.page_source.lower()
            
            for indicator in error_indicators:
                if indicator in page_text:
                    print(f"Found error indicator: '{indicator}'")
            
            login_success = False
        
        # Keep browser open for manual verification
        print(f"\n🔍 Browser staying open for 30 seconds for manual verification...")
        print("Please manually check the login status and 'My Account' presence.")
        time.sleep(30)
        
        return login_success
        
    except Exception as e:
        print(f"❌ Login test failed with error: {e}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    success = test_actual_login()
    print(f"\nLogin test result: {'SUCCESS' if success else 'FAILED'}")