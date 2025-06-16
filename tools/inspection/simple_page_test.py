#!/usr/bin/env python3
"""
Simple test script to inspect page structure
Uses the main automation class for consistent browser setup
"""

import time
import logging
import sys
from pathlib import Path
from selenium.webdriver.common.by import By

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def inspect_page_simple():
    """Simple page inspection without login"""
    automator = KaraokeVersionAutomator()
    
    try:
        test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        logging.info(f"Navigating to: {test_url}")
        
        automator.driver.get(test_url)
        time.sleep(5)  # Let the page load completely
        
        logging.info(f"Page title: {automator.driver.title}")
        logging.info(f"Current URL: {automator.driver.current_url}")
        
        # Look for track elements
        track_elements = automator.driver.find_elements(By.CSS_SELECTOR, ".track")
        logging.info(f"Found {len(track_elements)} track elements")
        
        if track_elements:
            for i, track in enumerate(track_elements[:5]):  # Just show first 5
                try:
                    track_name = track.find_element(By.CSS_SELECTOR, ".track__caption").text
                    data_index = track.get_attribute("data-index")
                    logging.info(f"Track {i+1}: '{track_name}' (index: {data_index})")
                except Exception as e:
                    logging.info(f"Track {i+1}: Could not extract name - {e}")
        
        # Check if we can see any obvious protection/login requirements
        page_text = automator.driver.page_source.lower()
        protection_keywords = ["login", "sign in", "subscribe", "premium", "member"]
        
        found_protection = []
        for keyword in protection_keywords:
            if keyword in page_text:
                found_protection.append(keyword)
        
        if found_protection:
            logging.warning(f"Page may have access restrictions. Found keywords: {found_protection}")
        else:
            logging.info("No obvious access restrictions detected")
        
        # Look for any audio elements
        audio_elements = automator.driver.find_elements(By.TAG_NAME, "audio")
        logging.info(f"Found {len(audio_elements)} audio elements")
        
        # Look for mixer-related elements
        mixer_keywords = ["mixer", "track", "volume", "mute", "solo"]
        for keyword in mixer_keywords:
            elements = automator.driver.find_elements(By.XPATH, f"//*[contains(@class, '{keyword}') or contains(@id, '{keyword}')]")
            if elements:
                logging.info(f"Found {len(elements)} elements with '{keyword}' in class or id")
        
        # Keep browser open for a while
        logging.info("Browser will stay open for 30 seconds for manual inspection...")
        time.sleep(30)
        
    except Exception as e:
        logging.error(f"Error during inspection: {e}")
    finally:
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    inspect_page_simple()