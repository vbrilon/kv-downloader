#!/usr/bin/env python3
"""
Inspect mixer controls after successful login
Based on working login test to access protected content
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

class MixerInspector:
    def __init__(self):
        self.setup_driver()
        
    def setup_driver(self):
        """Initialize Chrome driver"""
        chrome_options = Options()
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)
        
    def login(self):
        """Login using working method from test_login.py"""
        if not config.USERNAME or not config.PASSWORD:
            logging.error("Username or password not configured")
            return False
            
        logging.info("Navigating to Karaoke-Version.com...")
        self.driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # Check if already logged in
        hello_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Hello')]")
        if hello_elements:
            logging.info("Already logged in!")
            return True
        
        # Find login link
        login_selectors = [
            "//a[contains(text(), 'Log In')]",
            "//a[contains(text(), 'Login')]",
            "//a[contains(text(), 'Sign In')]"
        ]
        
        for selector in login_selectors:
            try:
                element = self.driver.find_element(By.XPATH, selector)
                if element and element.is_displayed():
                    logging.info(f"Clicking login link: '{element.text}'")
                    element.click()
                    time.sleep(3)
                    break
            except:
                continue
        
        # Find username field
        username_selectors = [
            (By.NAME, "email"),
            (By.NAME, "username"),
            (By.CSS_SELECTOR, "input[type='email']")
        ]
        
        username_field = None
        for selector_type, selector_value in username_selectors:
            try:
                username_field = self.wait.until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                if username_field and username_field.is_displayed():
                    logging.info(f"Found username field: {selector_type} = '{selector_value}'")
                    break
            except:
                continue
                
        if not username_field:
            logging.error("Could not find username field")
            return False
        
        # Find password field
        password_field = self.driver.find_element(By.NAME, "password")
        
        # Login
        username_field.clear()
        username_field.send_keys(config.USERNAME)
        password_field.clear()
        password_field.send_keys(config.PASSWORD)
        
        # Submit
        submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit'] | //button[@type='submit']")
        submit_button.click()
        
        time.sleep(5)
        
        # Verify login
        hello_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Hello')]")
        if hello_elements:
            logging.info("✅ Login successful!")
            return True
        else:
            logging.error("❌ Login failed")
            return False
    
    def inspect_mixer_controls(self):
        """Inspect mixer controls on song page"""
        test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        logging.info(f"Navigating to test song: {test_url}")
        self.driver.get(test_url)
        time.sleep(5)
        
        print("\n" + "="*80)
        print("🎛️ MIXER CONTROLS INSPECTION")
        print("="*80)
        
        # First, confirm we can see tracks
        tracks = self.driver.find_elements(By.CSS_SELECTOR, ".track")
        print(f"✅ Found {len(tracks)} track elements")
        
        if not tracks:
            print("❌ No tracks found - cannot inspect mixer controls")
            return
        
        # Look for common mixer control patterns
        mixer_patterns = [
            # Buttons and controls
            "button",
            "input[type='button']",
            "input[type='checkbox']",
            "input[type='radio']",
            
            # Classes that might indicate controls
            "[class*='play']",
            "[class*='mute']",
            "[class*='solo']",
            "[class*='toggle']",
            "[class*='control']",
            "[class*='button']",
            "[class*='mix']",
            "[class*='track']",
            
            # Download related
            "[class*='download']",
            "[class*='create']",
            "[class*='export']",
            
            # Common interactive elements
            "[onclick]",
            "[data-track]",
            "[data-index]",
            "[data-toggle]"
        ]
        
        print("\n🔍 Searching for interactive elements...")
        for pattern in mixer_patterns:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                if elements:
                    print(f"\n--- Found {len(elements)} elements matching '{pattern}' ---")
                    for i, elem in enumerate(elements[:5]):  # Limit to first 5
                        try:
                            tag = elem.tag_name
                            classes = elem.get_attribute('class') or ''
                            elem_id = elem.get_attribute('id') or ''
                            onclick = elem.get_attribute('onclick') or ''
                            text = elem.text.strip() if elem.text else ''
                            
                            print(f"  {i+1}. <{tag}> class='{classes[:50]}' id='{elem_id}'")
                            if text:
                                print(f"     text='{text[:50]}'")
                            if onclick:
                                print(f"     onclick='{onclick[:100]}...'")
                        except Exception as e:
                            print(f"     Error inspecting element: {e}")
            except:
                continue
        
        # Look specifically within track elements
        print(f"\n🎵 Inspecting individual track elements...")
        for i, track in enumerate(tracks[:3]):  # First 3 tracks
            try:
                track_name = track.find_element(By.CSS_SELECTOR, ".track__caption").text
                print(f"\n--- Track {i+1}: '{track_name}' ---")
                
                # Look for all interactive elements within this track
                interactive_elements = track.find_elements(By.CSS_SELECTOR, 
                    "button, input, a, [onclick], [class*='control'], [class*='toggle'], [class*='button']")
                
                if interactive_elements:
                    print(f"  Found {len(interactive_elements)} interactive elements:")
                    for j, elem in enumerate(interactive_elements):
                        try:
                            tag = elem.tag_name
                            elem_type = elem.get_attribute('type') or ''
                            classes = elem.get_attribute('class') or ''
                            elem_id = elem.get_attribute('id') or ''
                            text = elem.text.strip() if elem.text else ''
                            
                            print(f"    {j+1}. <{tag} type='{elem_type}'> class='{classes[:30]}' text='{text[:20]}'")
                        except:
                            continue
                else:
                    print("  No interactive elements found within track")
                    
            except Exception as e:
                print(f"  Error inspecting track {i+1}: {e}")
        
        # Look for download-related elements
        print(f"\n⬇️ Searching for download controls...")
        download_patterns = [
            "//button[contains(text(), 'Download')]",
            "//a[contains(text(), 'Download')]",
            "//button[contains(text(), 'Create')]",
            "//a[contains(text(), 'Create')]",
            "//button[contains(text(), 'Export')]",
            "//input[contains(@value, 'Download')]",
            ".download",
            ".create",
            ".export"
        ]
        
        for pattern in download_patterns:
            try:
                if pattern.startswith("//"):
                    elements = self.driver.find_elements(By.XPATH, pattern)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                    
                if elements:
                    print(f"  Found {len(elements)} elements with '{pattern}':")
                    for i, elem in enumerate(elements[:3]):
                        try:
                            tag = elem.tag_name
                            classes = elem.get_attribute('class') or ''
                            text = elem.text.strip() if elem.text else ''
                            href = elem.get_attribute('href') or ''
                            
                            print(f"    {i+1}. <{tag}> class='{classes}' text='{text}' href='{href[:50]}'")
                        except:
                            continue
            except:
                continue
        
        # Keep browser open for manual inspection
        print(f"\n🔍 Browser staying open for 60 seconds for manual inspection...")
        print("Use this time to manually explore the mixer controls.")
        time.sleep(60)
    
    def run(self):
        """Main inspection flow"""
        try:
            if self.login():
                self.inspect_mixer_controls()
            else:
                print("❌ Login failed - cannot inspect mixer controls")
        except Exception as e:
            print(f"❌ Inspection failed: {e}")
        finally:
            self.driver.quit()

if __name__ == "__main__":
    inspector = MixerInspector()
    inspector.run()