#!/usr/bin/env python3
"""
Test script to verify login functionality and identify login selectors.
Success indicator: "Log In" text changes to "Hello <username>"
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LoginTester:
    def __init__(self):
        self.setup_driver()
        
    def setup_driver(self):
        """Initialize Chrome driver for login testing"""
        chrome_options = Options()
        # Don't run headless so we can see the login process
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)
        
    def check_login_status(self):
        """Check if we're already logged in by looking for Hello message"""
        try:
            # Look for "Hello" text that indicates we're logged in
            hello_indicators = [
                "//text()[contains(., 'Hello')]",
                "//*[contains(text(), 'Hello')]",
                "//*[contains(text(), config.USERNAME)]" if config.USERNAME else None
            ]
            
            for indicator in hello_indicators:
                if indicator:
                    try:
                        element = self.driver.find_element(By.XPATH, indicator)
                        if element and element.text:
                            logging.info(f"Found logged-in indicator: '{element.text}'")
                            return True
                    except:
                        continue
                        
            # Also check for absence of "Log In" text
            try:
                login_links = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Log In')]")
                if not login_links:
                    logging.info("No 'Log In' links found - might be logged in")
                    return True
                else:
                    logging.info(f"Found {len(login_links)} 'Log In' links - not logged in")
                    return False
            except:
                pass
                
            return False
            
        except Exception as e:
            logging.error(f"Error checking login status: {e}")
            return False
    
    def find_login_elements(self):
        """Find and test different login form selectors"""
        if not config.USERNAME or not config.PASSWORD:
            logging.error("Please set KV_USERNAME and KV_PASSWORD in your .env file")
            return False
            
        logging.info("Looking for login form elements...")
        
        # Try to find "Log In" link first
        login_link_selectors = [
            "//a[contains(text(), 'Log In')]",
            "//a[contains(text(), 'Login')]",
            "//a[contains(text(), 'Sign In')]",
            "//button[contains(text(), 'Log In')]",
            ".login-link",
            "#login-link",
            "[href*='login']"
        ]
        
        login_link = None
        for selector in login_link_selectors:
            try:
                if selector.startswith("//"):
                    element = self.driver.find_element(By.XPATH, selector)
                else:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                if element and element.is_displayed():
                    login_link = element
                    logging.info(f"Found login link with selector: {selector}")
                    logging.info(f"Link text: '{element.text}'")
                    logging.info(f"Link href: '{element.get_attribute('href')}'")
                    break
            except:
                continue
                
        if login_link:
            logging.info("Clicking login link...")
            login_link.click()
            time.sleep(3)
        else:
            logging.info("No login link found, assuming we're on login page or form is visible")
        
        # Now look for username/email field
        username_selectors = [
            (By.NAME, "username"),
            (By.NAME, "email"),
            (By.NAME, "login"),
            (By.ID, "username"),
            (By.ID, "email"),
            (By.ID, "login"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email']"),
            (By.CSS_SELECTOR, "input[placeholder*='username']"),
            (By.CSS_SELECTOR, "input[placeholder*='Username']"),
            (By.CSS_SELECTOR, ".login-form input[type='text']"),
            (By.CSS_SELECTOR, ".signin-form input[type='text']"),
            (By.CSS_SELECTOR, "form input[type='text']"),
            (By.CSS_SELECTOR, "form input[type='email']")
        ]
        
        username_field = None
        username_selector_used = None
        
        for selector_type, selector_value in username_selectors:
            try:
                element = self.wait.until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                if element and element.is_displayed():
                    username_field = element
                    username_selector_used = (selector_type, selector_value)
                    logging.info(f"Found username field: {selector_type} = '{selector_value}'")
                    logging.info(f"Placeholder: '{element.get_attribute('placeholder')}'")
                    break
            except:
                continue
                
        if not username_field:
            logging.error("Could not find username/email field")
            return False
            
        # Look for password field
        password_selectors = [
            (By.NAME, "password"),
            (By.ID, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, ".login-form input[type='password']"),
            (By.CSS_SELECTOR, ".signin-form input[type='password']"),
            (By.CSS_SELECTOR, "form input[type='password']")
        ]
        
        password_field = None
        password_selector_used = None
        
        for selector_type, selector_value in password_selectors:
            try:
                element = self.driver.find_element(selector_type, selector_value)
                if element and element.is_displayed():
                    password_field = element
                    password_selector_used = (selector_type, selector_value)
                    logging.info(f"Found password field: {selector_type} = '{selector_value}'")
                    break
            except:
                continue
                
        if not password_field:
            logging.error("Could not find password field")
            return False
            
        # Try to login
        logging.info("Attempting login...")
        username_field.clear()
        username_field.send_keys(config.USERNAME)
        password_field.clear()
        password_field.send_keys(config.PASSWORD)
        
        # Find submit button
        submit_selectors = [
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Log')]"),
            (By.XPATH, "//button[contains(text(), 'Sign')]"),
            (By.XPATH, "//input[@value*='Log']"),
            (By.XPATH, "//input[@value*='Sign']"),
            (By.CSS_SELECTOR, ".login-button"),
            (By.CSS_SELECTOR, ".signin-button"),
            (By.CSS_SELECTOR, ".submit-button")
        ]
        
        submit_button = None
        for selector_type, selector_value in submit_selectors:
            try:
                element = self.driver.find_element(selector_type, selector_value)
                if element and element.is_displayed():
                    submit_button = element
                    logging.info(f"Found submit button: {selector_type} = '{selector_value}'")
                    logging.info(f"Button text: '{element.text}'")
                    logging.info(f"Button value: '{element.get_attribute('value')}'")
                    break
            except:
                continue
                
        if not submit_button:
            logging.error("Could not find submit button")
            return False
            
        submit_button.click()
        logging.info("Login form submitted")
        
        # Wait for page to load and check login status
        time.sleep(5)
        
        # Check if login was successful
        is_logged_in = self.check_login_status()
        
        if is_logged_in:
            logging.info("✅ LOGIN SUCCESSFUL!")
            logging.info(f"Working selectors:")
            logging.info(f"  Username: {username_selector_used}")
            logging.info(f"  Password: {password_selector_used}")
        else:
            logging.error("❌ LOGIN FAILED or not detected")
            
        return is_logged_in
    
    def test_login_flow(self):
        """Test the complete login flow"""
        try:
            # Start at the main page
            logging.info("Navigating to Karaoke-Version.com...")
            self.driver.get("https://www.karaoke-version.com")
            time.sleep(3)
            
            logging.info(f"Page title: {self.driver.title}")
            
            # Check if already logged in
            if self.check_login_status():
                logging.info("Already logged in!")
                return True
                
            # Try to login
            success = self.find_login_elements()
            
            if success:
                # Test access to a song page after login
                test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
                logging.info(f"Testing access to song page: {test_url}")
                self.driver.get(test_url)
                time.sleep(3)
                
                # Check if we can see tracks (indicates successful login)
                tracks = self.driver.find_elements(By.CSS_SELECTOR, ".track")
                logging.info(f"Found {len(tracks)} tracks on song page")
                
                if tracks:
                    logging.info("✅ Can access track content - login working!")
                else:
                    logging.warning("⚠️ No tracks found - login might not be working properly")
            
            # Keep browser open for manual verification
            logging.info("Browser staying open for 30 seconds for manual verification...")
            time.sleep(30)
            
            return success
            
        except Exception as e:
            logging.error(f"Login test failed: {e}")
            return False
        finally:
            self.driver.quit()

if __name__ == "__main__":
    tester = LoginTester()
    success = tester.test_login_flow()
    print(f"\nLogin test result: {'SUCCESS' if success else 'FAILED'}")