#!/usr/bin/env python3
"""
Complete track extraction - more thorough examination
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

def complete_track_extraction():
    """More thorough extraction of ALL tracks"""
    chrome_options = Options()
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        logging.info(f"Navigating to: {test_url}")
        
        driver.get(test_url)
        time.sleep(5)
        
        logging.info(f"Page title: {driver.title}")
        
        # Look for ALL track elements - be more comprehensive
        track_elements = driver.find_elements(By.CSS_SELECTOR, ".track")
        
        logging.info(f"\n{'='*60}")
        logging.info(f"FOUND {len(track_elements)} TRACK ELEMENTS:")
        logging.info(f"{'='*60}")
        
        all_tracks = []
        
        for i, track in enumerate(track_elements):
            # Get all the data we can
            data_index = track.get_attribute('data-index')
            full_text = track.text.strip()
            
            # Try to get track name from different possible locations
            track_name = None
            
            # Method 1: .track__caption
            try:
                caption_elem = track.find_element(By.CSS_SELECTOR, ".track__caption")
                track_name = caption_elem.text.strip()
            except:
                pass
            
            # Method 2: First line of text
            if not track_name:
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                if lines:
                    track_name = lines[0]
            
            # Method 3: Check for any text that looks like an instrument
            if not track_name:
                # Look for common instrument words
                for line in full_text.split('\n'):
                    line = line.strip()
                    if any(word in line.lower() for word in ['vocal', 'guitar', 'bass', 'drum', 'piano', 'synth', 'percussion']) and len(line) > 3:
                        track_name = line
                        break
            
            if track_name:
                # Clean up track name - remove control characters and percentages
                clean_name = track_name
                if not any(char in clean_name for char in ['%', 'L\nC\nR']) and len(clean_name) > 2:
                    all_tracks.append({
                        'index': data_index,
                        'name': clean_name,
                        'element_index': i,
                        'full_text': repr(full_text),
                        'html_snippet': track.get_attribute('outerHTML')[:300]
                    })
                    
                    logging.info(f"Track {i} (data-index={data_index}): '{clean_name}'")
                    logging.info(f"  Full text: {repr(full_text)}")
                    logging.info(f"  HTML snippet: {track.get_attribute('outerHTML')[:200]}...")
                    logging.info("-" * 50)
        
        # Also check if there are any hidden or initially invisible tracks
        logging.info(f"\n{'='*60}")
        logging.info("CHECKING FOR ADDITIONAL TRACK PATTERNS:")
        logging.info(f"{'='*60}")
        
        # Check for different possible selectors
        additional_selectors = [
            "[data-index]",
            ".track-item",
            ".instrument",
            "[class*='track']",
            ".mixer .track",
            ".track-control"
        ]
        
        for selector in additional_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                logging.info(f"Selector '{selector}': {len(elements)} elements")
                
                for el in elements[:3]:  # Show first few
                    text = el.text.strip()
                    if text and any(word in text.lower() for word in ['vocal', 'guitar', 'bass', 'drum', 'piano', 'synth']):
                        logging.info(f"  Found: '{text[:50]}...'")
            except Exception as e:
                logging.debug(f"Selector {selector} failed: {e}")
        
        # Check page source for any missed patterns
        page_source = driver.page_source.lower()
        track_patterns = ['lead vocal', 'lead electric guitar', 'rhythm guitar', 'acoustic guitar']
        
        logging.info(f"\n{'='*60}")
        logging.info("SEARCHING PAGE SOURCE FOR SPECIFIC PATTERNS:")
        logging.info(f"{'='*60}")
        
        for pattern in track_patterns:
            if pattern in page_source:
                logging.info(f"Found '{pattern}' in page source!")
                # Try to find the context
                start_pos = page_source.find(pattern)
                context = page_source[max(0, start_pos-100):start_pos+100]
                logging.info(f"Context: {context}")
        
        # Print final summary
        logging.info(f"\n{'='*60}")
        logging.info("FINAL EXTRACTED TRACK NAMES:")
        logging.info(f"{'='*60}")
        
        unique_tracks = []
        seen_names = set()
        
        for track in all_tracks:
            if track['name'] not in seen_names:
                unique_tracks.append(track['name'])
                seen_names.add(track['name'])
                
        for i, track_name in enumerate(unique_tracks, 1):
            logging.info(f"{i}. {track_name}")
            
        logging.info(f"\nTotal unique tracks found: {len(unique_tracks)}")
        
        # Keep browser open for manual verification
        logging.info("\nBrowser staying open for 30 seconds - please manually verify all tracks are visible...")
        time.sleep(30)
        
        return unique_tracks
        
    except Exception as e:
        logging.error(f"Error during extraction: {e}")
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    tracks = complete_track_extraction()
    print(f"\nComplete track list: {tracks}")