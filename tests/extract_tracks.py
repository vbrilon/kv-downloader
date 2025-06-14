#!/usr/bin/env python3
"""
Extract track names from the Chappell Roan page
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

def extract_track_names():
    """Extract specific track names from the page"""
    chrome_options = Options()
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        logging.info(f"Navigating to: {test_url}")
        
        driver.get(test_url)
        time.sleep(5)
        
        logging.info(f"Page title: {driver.title}")
        
        # Look for track elements specifically
        track_elements = driver.find_elements(By.CSS_SELECTOR, ".track")
        
        logging.info(f"\n{'='*60}")
        logging.info(f"FOUND {len(track_elements)} TRACK ELEMENTS:")
        logging.info(f"{'='*60}")
        
        track_names = []
        
        for i, track in enumerate(track_elements):
            # Get the full text
            full_text = track.text.strip()
            
            # Try to extract just the instrument name (usually first line)
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            track_name = lines[0] if lines else full_text
            
            # Clean up the track name
            if track_name and not any(char in track_name for char in ['%', 'L', 'C', 'R']) and len(track_name) > 2:
                track_names.append(track_name)
                logging.info(f"Track {i+1}: '{track_name}'")
                logging.info(f"  Full text: {repr(full_text)}")
                logging.info(f"  HTML: {track.get_attribute('outerHTML')[:200]}...")
                logging.info("-" * 40)
        
        # Also try alternative selectors that might contain track names
        alternative_selectors = [
            ".track-name",
            ".instrument-name", 
            "[data-track-name]",
            ".track .name",
            ".track h3",
            ".track h4",
            ".track span"
        ]
        
        for selector in alternative_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logging.info(f"\nAlternative selector '{selector}' found {len(elements)} elements:")
                for el in elements[:3]:  # Show first 3
                    logging.info(f"  '{el.text.strip()}'")
        
        # Print summary
        logging.info(f"\n{'='*60}")
        logging.info("EXTRACTED TRACK NAMES:")
        logging.info(f"{'='*60}")
        
        unique_tracks = list(dict.fromkeys(track_names))  # Remove duplicates while preserving order
        for i, track_name in enumerate(unique_tracks, 1):
            logging.info(f"{i}. {track_name}")
            
        logging.info(f"\nTotal unique tracks found: {len(unique_tracks)}")
        
        # Keep browser open briefly
        time.sleep(10)
        
        return unique_tracks
        
    except Exception as e:
        logging.error(f"Error during extraction: {e}")
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    tracks = extract_track_names()
    print(f"\nFinal result: {tracks}")