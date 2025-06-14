#!/usr/bin/env python3
"""
Test script to inspect a specific Karaoke-Version.com page
and identify available backing tracks.

This will help us understand the site structure and identify
the correct selectors for track discovery.
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

class PageInspector:
    def __init__(self):
        self.setup_driver()
        
    def setup_driver(self):
        """Initialize Chrome driver for inspection"""
        chrome_options = Options()
        # Don't run headless so we can see what's happening
        # chrome_options.add_argument("--headless")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def login(self):
        """Login to Karaoke-Version.com"""
        if not config.USERNAME or not config.PASSWORD:
            logging.error("Please set KV_USERNAME and KV_PASSWORD in your .env file")
            return False
            
        logging.info("Logging in...")
        self.driver.get(config.LOGIN_URL)
        
        try:
            # Try common login form selectors
            selectors_to_try = [
                (By.NAME, "username"),
                (By.NAME, "email"),
                (By.ID, "username"),
                (By.ID, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='Email']")
            ]
            
            username_field = None
            for selector_type, selector_value in selectors_to_try:
                try:
                    username_field = self.wait.until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    logging.info(f"Found username field with selector: {selector_type} = '{selector_value}'")
                    break
                except:
                    continue
                    
            if not username_field:
                logging.error("Could not find username/email field")
                return False
                
            # Try common password selectors
            password_selectors = [
                (By.NAME, "password"),
                (By.ID, "password"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]
            
            password_field = None
            for selector_type, selector_value in password_selectors:
                try:
                    password_field = self.driver.find_element(selector_type, selector_value)
                    logging.info(f"Found password field with selector: {selector_type} = '{selector_value}'")
                    break
                except:
                    continue
                    
            if not password_field:
                logging.error("Could not find password field")
                return False
                
            # Fill in credentials
            username_field.send_keys(config.USERNAME)
            password_field.send_keys(config.PASSWORD)
            
            # Try to find and click submit button
            submit_selectors = [
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Log')]"),
                (By.XPATH, "//input[@value*='Log']")
            ]
            
            for selector_type, selector_value in submit_selectors:
                try:
                    submit_button = self.driver.find_element(selector_type, selector_value)
                    logging.info(f"Found submit button with selector: {selector_type} = '{selector_value}'")
                    submit_button.click()
                    break
                except:
                    continue
            
            time.sleep(3)
            logging.info("Login attempt completed")
            return True
            
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False
    
    def inspect_page(self, url):
        """Inspect a specific page and identify track elements"""
        logging.info(f"Inspecting page: {url}")
        self.driver.get(url)
        time.sleep(3)  # Let the page load
        
        # Print page title and URL for confirmation
        logging.info(f"Page title: {self.driver.title}")
        logging.info(f"Current URL: {self.driver.current_url}")
        
        # Look for common track-related elements
        track_selectors = [
            "input[type='checkbox']",
            ".track",
            ".instrument",
            "[data-track]",
            "[data-instrument]",
            ".mixer",
            ".track-toggle",
            ".track-mixer",
            ".instrument-toggle",
            "label[for*='track']",
            "label[for*='instrument']"
        ]
        
        found_tracks = []
        
        for selector in track_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logging.info(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for i, element in enumerate(elements):
                        track_info = {
                            'selector': selector,
                            'index': i,
                            'tag': element.tag_name,
                            'text': element.text.strip() if element.text else '',
                            'id': element.get_attribute('id') or '',
                            'class': element.get_attribute('class') or '',
                            'data_track': element.get_attribute('data-track') or '',
                            'data_instrument': element.get_attribute('data-instrument') or '',
                            'for_attribute': element.get_attribute('for') or '',
                            'value': element.get_attribute('value') or ''
                        }
                        
                        # Only add if it seems track-related
                        if any([track_info['text'], 
                               'track' in track_info['class'].lower(),
                               'instrument' in track_info['class'].lower(),
                               track_info['data_track'],
                               track_info['data_instrument']]):
                            found_tracks.append(track_info)
                            
            except Exception as e:
                logging.debug(f"Selector {selector} failed: {e}")
                
        # Print all found tracks
        logging.info(f"\n{'='*50}")
        logging.info("FOUND TRACK ELEMENTS:")
        logging.info(f"{'='*50}")
        
        for track in found_tracks:
            logging.info(f"Selector: {track['selector']}")
            logging.info(f"  Tag: {track['tag']}")
            logging.info(f"  Text: '{track['text']}'")
            logging.info(f"  ID: '{track['id']}'")
            logging.info(f"  Class: '{track['class']}'")
            logging.info(f"  Data-track: '{track['data_track']}'")
            logging.info(f"  Data-instrument: '{track['data_instrument']}'")
            logging.info(f"  For: '{track['for_attribute']}'")
            logging.info(f"  Value: '{track['value']}'")
            logging.info("-" * 30)
            
        # Also check for any audio/download related elements
        logging.info(f"\n{'='*50}")
        logging.info("LOOKING FOR DOWNLOAD/AUDIO ELEMENTS:")
        logging.info(f"{'='*50}")
        
        download_selectors = [
            "button",
            "a[href*='download']",
            "[data-download]",
            ".download",
            ".btn",
            "input[type='button']"
        ]
        
        for selector in download_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if any(word in text.lower() for word in ['download', 'get', 'export', 'save']):
                        logging.info(f"Download element: {element.tag_name}")
                        logging.info(f"  Text: '{text}'")
                        logging.info(f"  Class: '{element.get_attribute('class') or ''}'")
                        logging.info(f"  Href: '{element.get_attribute('href') or ''}'")
                        logging.info("-" * 20)
            except:
                pass
                
        return found_tracks
    
    def run_inspection(self):
        """Main inspection flow"""
        try:
            # Login first
            if not self.login():
                logging.error("Login failed, cannot proceed with inspection")
                return
                
            # Wait a moment for login to complete
            time.sleep(2)
            
            # Inspect the specific page
            test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
            tracks = self.inspect_page(test_url)
            
            # Keep browser open for manual inspection
            logging.info(f"\nFound {len(tracks)} potential track elements")
            logging.info("Browser will stay open for 30 seconds for manual inspection...")
            time.sleep(30)
            
        except Exception as e:
            logging.error(f"Inspection failed: {e}")
        finally:
            self.driver.quit()

if __name__ == "__main__":
    inspector = PageInspector()
    inspector.run_inspection()