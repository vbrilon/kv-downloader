#!/usr/bin/env python3
"""
Test complete login cycle: logout → login to capture exact selectors
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
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_full_login_cycle():
    """Test logout then login to capture exact selectors"""
    chrome_options = Options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 15)
    
    try:
        # Go to main page
        logging.info("Navigating to Karaoke-Version.com...")
        driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # First, try to logout if we're logged in
        logout_selectors = [
            "//a[contains(text(), 'Log out')]",
            "//a[contains(text(), 'Logout')]", 
            "//a[contains(text(), 'Sign out')]",
            "//a[contains(text(), 'Signout')]",
            "[href*='logout']",
            "[href*='signout']"
        ]
        
        logout_attempted = False
        for selector in logout_selectors:
            try:
                if selector.startswith("//"):
                    element = driver.find_element(By.XPATH, selector)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    
                if element and element.is_displayed():
                    logging.info(f"Found logout link: {selector}")
                    element.click()
                    time.sleep(3)
                    logout_attempted = True
                    break
            except:
                continue
                
        if not logout_attempted:
            logging.info("No logout link found, proceeding with login test")
            
        # Now look for login elements
        logging.info("Looking for login form...")
        
        # Look for "Log In" link
        login_link_selectors = [
            "//a[contains(text(), 'Log In')]",
            "//a[contains(text(), 'Login')]",
            "//a[contains(text(), 'Sign In')]"
        ]
        
        for selector in login_link_selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                if element and element.is_displayed():
                    logging.info(f"✅ Found login link: '{element.text}' with selector: {selector}")
                    element.click()
                    time.sleep(3)
                    break
            except:
                continue
        
        # Find username field with detailed logging
        username_selectors = [
            (By.NAME, "email"),
            (By.NAME, "username"), 
            (By.NAME, "login"),
            (By.ID, "email"),
            (By.ID, "username"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email']")
        ]
        
        username_field = None
        working_username_selector = None
        
        for selector_type, selector_value in username_selectors:
            try:
                element = wait.until(EC.presence_of_element_located((selector_type, selector_value)))
                if element and element.is_displayed():
                    username_field = element
                    working_username_selector = (selector_type, selector_value)
                    logging.info(f"✅ Found username field: {selector_type.name} = '{selector_value}'")
                    logging.info(f"   Placeholder: '{element.get_attribute('placeholder')}'")
                    logging.info(f"   Name: '{element.get_attribute('name')}'")
                    logging.info(f"   ID: '{element.get_attribute('id')}'")
                    break
            except:
                continue
                
        # Find password field
        password_selectors = [
            (By.NAME, "password"),
            (By.ID, "password"), 
            (By.CSS_SELECTOR, "input[type='password']")
        ]
        
        password_field = None
        working_password_selector = None
        
        for selector_type, selector_value in password_selectors:
            try:
                element = driver.find_element(selector_type, selector_value)
                if element and element.is_displayed():
                    password_field = element
                    working_password_selector = (selector_type, selector_value)
                    logging.info(f"✅ Found password field: {selector_type.name} = '{selector_value}'")
                    break
            except:
                continue
                
        if username_field and password_field:
            # Fill in credentials
            logging.info("Filling in credentials...")
            username_field.clear()
            username_field.send_keys(config.USERNAME)
            password_field.clear()
            password_field.send_keys(config.PASSWORD)
            
            # Find submit button
            submit_selectors = [
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Log')]"),
                (By.XPATH, "//input[@value*='Log']")
            ]
            
            submit_button = None
            working_submit_selector = None
            
            for selector_type, selector_value in submit_selectors:
                try:
                    element = driver.find_element(selector_type, selector_value)
                    if element and element.is_displayed():
                        submit_button = element
                        working_submit_selector = (selector_type, selector_value)
                        logging.info(f"✅ Found submit button: {selector_type.name} = '{selector_value}'")
                        logging.info(f"   Text: '{element.text}'")
                        logging.info(f"   Value: '{element.get_attribute('value')}'")
                        break
                except:
                    continue
                    
            if submit_button:
                logging.info("Submitting login form...")
                submit_button.click()
                time.sleep(5)
                
                # Check for "Hello" indicator
                try:
                    hello_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Hello')]")
                    if hello_elements:
                        for elem in hello_elements:
                            logging.info(f"✅ LOGIN SUCCESS! Found: '{elem.text}'")
                    else:
                        logging.info("No 'Hello' text found after login")
                        
                    # Also check for absence of "Log In" links
                    login_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Log In')]")
                    if not login_links:
                        logging.info("✅ No 'Log In' links found - login successful!")
                    else:
                        logging.info(f"Still found {len(login_links)} 'Log In' links")
                        
                except Exception as e:
                    logging.error(f"Error checking login success: {e}")
                
                # Print working selectors summary
                logging.info("\n" + "="*60)
                logging.info("WORKING LOGIN SELECTORS:")
                logging.info("="*60)
                if working_username_selector:
                    logging.info(f"Username: {working_username_selector[0].name} = '{working_username_selector[1]}'")
                if working_password_selector:
                    logging.info(f"Password: {working_password_selector[0].name} = '{working_password_selector[1]}'")
                if working_submit_selector:
                    logging.info(f"Submit: {working_submit_selector[0].name} = '{working_submit_selector[1]}'")
                logging.info("="*60)
                
        # Keep browser open
        logging.info("\nBrowser staying open for 30 seconds...")
        time.sleep(30)
        
    except Exception as e:
        logging.error(f"Test failed: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_full_login_cycle()