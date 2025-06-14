#!/usr/bin/env python3
"""
Manual step-by-step login test with explicit actions
"""

import time
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

def manual_login_test():
    """Perform manual login with explicit steps"""
    print("🔐 MANUAL LOGIN TEST")
    print("="*40)
    
    if not config.USERNAME or not config.PASSWORD:
        print("❌ No credentials configured")
        return
    
    print(f"Using: {config.USERNAME}")
    
    # Setup Chrome
    chrome_options = Options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 10)
    
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
        
        print(f"Current URL: {driver.current_url}")
        
        # Step 3: Find email field - try multiple approaches
        print("📧 Looking for email field...")
        
        email_field = None
        
        # Try by name="email"
        try:
            email_field = driver.find_element(By.NAME, "email")
            print("✅ Found email field by name='email'")
        except:
            print("❌ No field with name='email'")
        
        # Try by id="email" 
        if not email_field:
            try:
                email_field = driver.find_element(By.ID, "email")
                print("✅ Found email field by id='email'")
            except:
                print("❌ No field with id='email'")
        
        # Try by type="email"
        if not email_field:
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
                print("✅ Found email field by type='email'")
            except:
                print("❌ No field with type='email'")
        
        # Try by placeholder containing "email"
        if not email_field:
            try:
                email_field = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'email')]")
                print("✅ Found email field by placeholder containing 'email'")
            except:
                print("❌ No field with placeholder containing 'email'")
        
        if not email_field:
            print("❌ COULD NOT FIND EMAIL FIELD")
            print("Available input fields:")
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for i, inp in enumerate(inputs):
                print(f"  {i}: type='{inp.get_attribute('type')}' name='{inp.get_attribute('name')}' id='{inp.get_attribute('id')}'")
            return
        
        # Step 4: Find password field
        print("🔒 Looking for password field...")
        try:
            password_field = driver.find_element(By.NAME, "password")
            print("✅ Found password field by name='password'")
        except:
            try:
                password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                print("✅ Found password field by type='password'")
            except:
                print("❌ COULD NOT FIND PASSWORD FIELD")
                return
        
        # Step 5: Clear and fill email
        print("✏️ Filling email field...")
        email_field.clear()
        email_field.send_keys(config.USERNAME)
        print(f"✅ Entered: {config.USERNAME}")
        
        # Step 6: Clear and fill password  
        print("✏️ Filling password field...")
        password_field.clear()
        password_field.send_keys(config.PASSWORD)
        print("✅ Entered password (hidden)")
        
        # Step 7: Find and click submit
        print("🚀 Looking for submit button...")
        
        submit_button = None
        
        # Try input type="submit"
        try:
            submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
            print("✅ Found submit by input[type='submit']")
        except:
            print("❌ No input[type='submit']")
        
        # Try button type="submit"
        if not submit_button:
            try:
                submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                print("✅ Found submit by button[type='submit']")
            except:
                print("❌ No button[type='submit']")
        
        # Try button with login text
        if not submit_button:
            try:
                submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log')]")
                print("✅ Found submit by button text containing 'Log'")
            except:
                print("❌ No button with 'Log' text")
        
        if not submit_button:
            print("❌ COULD NOT FIND SUBMIT BUTTON")
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for i, btn in enumerate(buttons):
                print(f"  Button {i}: type='{btn.get_attribute('type')}' text='{btn.text}'")
            return
        
        # Step 8: Click submit
        print("🎯 Clicking submit button...")
        submit_button.click()
        
        # Step 9: Wait and check for "My Account"
        print("⏳ Waiting for login to complete...")
        time.sleep(5)
        
        print(f"URL after login: {driver.current_url}")
        
        # Check for "My Account"
        my_account = driver.find_elements(By.XPATH, "//*[contains(text(), 'My Account')]")
        if my_account:
            print("🎉 LOGIN SUCCESS! Found 'My Account'")
            return True
        else:
            print("❌ LOGIN FAILED - No 'My Account' found")
            
            # Check for error messages
            if "error" in driver.page_source.lower():
                print("⚠️ Page contains 'error' text")
            if "invalid" in driver.page_source.lower():
                print("⚠️ Page contains 'invalid' text")
            
            return False
        
        # Keep browser open
        print("🔍 Browser staying open for 30 seconds...")
        time.sleep(30)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    success = manual_login_test()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")