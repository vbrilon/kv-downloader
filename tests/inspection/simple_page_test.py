#!/usr/bin/env python3
"""
Simple test script to inspect the Chappell Roan page structure
without logging in first.
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def inspect_page_simple():
    """Simple page inspection without login"""
    chrome_options = Options()
    # Don't run headless so we can see what's happening
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        logging.info(f"Navigating to: {test_url}")
        
        driver.get(test_url)
        time.sleep(5)  # Let the page load completely
        
        logging.info(f"Page title: {driver.title}")
        logging.info(f"Current URL: {driver.current_url}")
        
        # Check if we need to login or if content is visible
        page_source = driver.page_source
        
        if "login" in page_source.lower() or "sign in" in page_source.lower():
            logging.info("Page appears to require login")
        
        # Look for any text that mentions tracks or instruments
        track_keywords = ['vocal', 'guitar', 'bass', 'drum', 'piano', 'track', 'instrument', 'backing']
        
        logging.info("\nSearching for track-related content...")
        for keyword in track_keywords:
            if keyword.lower() in page_source.lower():
                logging.info(f"Found keyword '{keyword}' on page")
        
        # Look for specific elements that might be tracks
        selectors_to_check = [
            "button",
            "input[type='checkbox']",
            "label",
            ".track",
            ".instrument",
            "[data-track]",
            "[class*='track']",
            "[class*='instrument']"
        ]
        
        for selector in selectors_to_check:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logging.info(f"\nFound {len(elements)} elements with selector: {selector}")
                    for i, element in enumerate(elements[:5]):  # Limit to first 5
                        text = element.text.strip()
                        if text and any(keyword in text.lower() for keyword in track_keywords):
                            logging.info(f"  {i}: '{text}' (class: {element.get_attribute('class')})")
            except Exception as e:
                logging.debug(f"Error with selector {selector}: {e}")
        
        # Print some of the page content for manual inspection
        logging.info(f"\nFirst 500 characters of page:")
        logging.info(page_source[:500])
        
        # Keep browser open for manual inspection
        logging.info("\nBrowser will stay open for 30 seconds for manual inspection...")
        time.sleep(30)
        
    except Exception as e:
        logging.error(f"Error during inspection: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    inspect_page_simple()