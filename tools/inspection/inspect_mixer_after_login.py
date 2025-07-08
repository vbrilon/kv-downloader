#!/usr/bin/env python3
"""
Inspect mixer controls after successful login
Uses the main automation class for consistent login behavior
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

class MixerInspector:
    def __init__(self):
        self.automator = KaraokeVersionAutomator()
        
    def login(self):
        """Login using the main automator"""
        return self.automator.login()
    
    def inspect_mixer_on_song(self, song_url):
        """Navigate to song and inspect mixer controls"""
        logging.info(f"Navigating to song: {song_url}")
        self.automator.driver.get(song_url)
        time.sleep(5)
        
        logging.info("="*80)
        logging.info("MIXER INSPECTION AFTER LOGIN")
        logging.info("="*80)
        
        # Look for track elements
        logging.info("🎛️ Looking for track elements...")
        track_elements = self.automator.driver.find_elements(By.CSS_SELECTOR, ".track")
        
        if track_elements:
            logging.info(f"Found {len(track_elements)} track elements:")
            
            for i, track in enumerate(track_elements):
                try:
                    # Get track name
                    track_name = track.find_element(By.CSS_SELECTOR, ".track__caption").text
                    data_index = track.get_attribute("data-index")
                    
                    logging.info(f"  Track {i+1}: '{track_name}' (index: {data_index})")
                    
                    # Look for controls within the track
                    _inspect_track_controls(track, i+1)
                    
                except Exception as e:
                    logging.error(f"Error inspecting track {i+1}: {e}")
        else:
            logging.warning("No track elements found with .track selector")
        
        # Look for global controls
        logging.info("\n🎚️ Looking for global mixer controls...")
        _inspect_global_controls(self.automator.driver)
        
        # Look for download buttons
        logging.info("\n⬇️ Looking for download buttons...")
        _inspect_download_buttons(self.automator.driver)
        
        # Keep browser open for manual inspection
        logging.info("\n🔍 Keeping browser open for 45 seconds for manual inspection...")
        time.sleep(45)
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.automator.driver.quit()
        except:
            pass

def _inspect_track_controls(track_element, track_number):
    """Inspect controls within a single track element"""
    try:
        # Look for interactive elements
        buttons = track_element.find_elements(By.TAG_NAME, "button")
        inputs = track_element.find_elements(By.TAG_NAME, "input")
        clickable_elements = track_element.find_elements(By.CSS_SELECTOR, "[onclick], [data-track], .clickable")
        
        if buttons:
            logging.info(f"    Found {len(buttons)} buttons:")
            for j, btn in enumerate(buttons):
                try:
                    btn_text = btn.text.strip() or 'no-text'
                    btn_class = btn.get_attribute('class') or 'no-class'
                    onclick = btn.get_attribute('onclick') or 'no-onclick'
                    logging.info(f"      Button {j+1}: '{btn_text}' class='{btn_class}' onclick='{onclick[:30]}...'")
                except:
                    continue
        
        if inputs:
            logging.info(f"    Found {len(inputs)} input elements:")
            for j, inp in enumerate(inputs):
                try:
                    inp_type = inp.get_attribute('type') or 'text'
                    inp_class = inp.get_attribute('class') or 'no-class'
                    checked = inp.get_attribute('checked') or 'false'
                    logging.info(f"      Input {j+1}: type='{inp_type}' class='{inp_class}' checked='{checked}'")
                except:
                    continue
        
        if clickable_elements:
            logging.info(f"    Found {len(clickable_elements)} clickable elements")
            
    except Exception as e:
        logging.error(f"    Error inspecting track {track_number} controls: {e}")

def _inspect_global_controls(driver):
    """Look for global mixer controls"""
    global_selectors = [
        ".mixer-controls",
        ".global-controls", 
        ".master-controls",
        "#mixer",
        "[class*='mixer']",
        "[class*='master']"
    ]
    
    for selector in global_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logging.info(f"Found {len(elements)} elements with selector '{selector}'")
                for elem in elements:
                    try:
                        tag = elem.tag_name
                        classes = elem.get_attribute('class') or 'no-class'
                        elem_id = elem.get_attribute('id') or 'no-id'
                        logging.info(f"  <{tag}> class='{classes}' id='{elem_id}'")
                    except:
                        continue
        except:
            continue

def _inspect_download_buttons(driver):
    """Look for download buttons"""
    download_selectors = [
        "//button[contains(text(), 'Download')]",
        "//a[contains(text(), 'Download')]",
        "//button[contains(text(), 'Create')]",
        ".download-btn",
        ".create-btn"
    ]
    
    for selector in download_selectors:
        try:
            if selector.startswith("//"):
                elements = driver.find_elements(By.XPATH, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
            if elements:
                logging.info(f"Found {len(elements)} elements with selector '{selector}'")
                for elem in elements:
                    try:
                        text = elem.text.strip() or 'no-text'
                        classes = elem.get_attribute('class') or 'no-class'
                        visible = elem.is_displayed()
                        enabled = elem.is_enabled()
                        logging.info(f"  '{text}' class='{classes}' visible={visible} enabled={enabled}")
                    except:
                        continue
        except:
            continue

def run_mixer_inspection():
    """Main function to run mixer inspection"""
    inspector = MixerInspector()
    
    try:
        # Login first
        if not inspector.login():
            logging.error("Login failed - cannot proceed with inspection")
            return
        
        logging.info("✅ Login successful!")
        
        # Test songs to inspect
        test_songs = [
            "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html",
            "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
        ]
        
        for song_url in test_songs:
            logging.info(f"\n{'='*80}")
            logging.info(f"INSPECTING: {song_url}")
            logging.info(f"{'='*80}")
            
            inspector.inspect_mixer_on_song(song_url)
            
            # Short break between songs
            time.sleep(2)
        
    except Exception as e:
        logging.error(f"Error during inspection: {e}")
    finally:
        inspector.cleanup()

if __name__ == "__main__":
    run_mixer_inspection()