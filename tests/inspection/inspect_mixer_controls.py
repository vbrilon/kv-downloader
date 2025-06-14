#!/usr/bin/env python3
"""
Inspect mixer controls and download process on Karaoke-Version.com
This tool will help discover the selectors needed for track selection and downloading.
"""

import time
import sys
from pathlib import Path
from selenium.webdriver.common.by import By

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def inspect_mixer_controls():
    """Inspect mixer controls and download elements"""
    print("🔍 Starting mixer controls inspection...")
    
    try:
        # Initialize automator and login
        print("🔐 Initializing automator and logging in...")
        automator = KaraokeVersionAutomator()
        
        if not automator.login():
            print("❌ Login failed - cannot inspect protected content")
            return
            
        print("✅ Login successful!")
            
        # Navigate to test song
        test_song_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        print(f"🎵 Navigating to test song: {test_song_url}")
        automator.driver.get(test_song_url)
        time.sleep(5)
        
        print("\n" + "="*80)
        print("MIXER CONTROLS INSPECTION")
        print("="*80)
        
        # Look for mixer/player controls
        inspect_mixer_area(automator.driver)
        
        print("\n" + "="*80)
        print("DOWNLOAD CONTROLS INSPECTION")
        print("="*80)
        
        # Look for download buttons
        inspect_download_controls(automator.driver)
        
        print("\n" + "="*80)
        print("TRACK CONTROL ELEMENTS INSPECTION")
        print("="*80)
        
        # Inspect individual track controls
        inspect_track_controls(automator.driver)
        
        print("\n" + "="*80)
        print("PAGE SOURCE ANALYSIS")
        print("="*80)
        
        # Search for relevant keywords in page source
        analyze_page_source(automator.driver)
        
        # Keep browser open for manual inspection
        print("\n🔍 Browser will stay open for 30 seconds for manual inspection...")
        print("Use this time to manually explore the page controls.")
        time.sleep(30)
        
    except Exception as e:
        print(f"❌ Error during inspection: {e}")
    finally:
        try:
            automator.driver.quit()
        except:
            pass
        print("✅ Inspection completed")


def inspect_mixer_area(driver):
    """Look for mixer/player area elements"""
    mixer_selectors = [
        ".mixer",
        ".player",
        ".track-mixer",
        ".audio-mixer",
        ".controls",
        ".player-controls",
        "#mixer",
        "#player",
        "[class*='mix']",
        "[class*='player']",
        "[id*='mix']",
        "[id*='player']"
    ]
    
    print("🎚️ Searching for mixer/player areas...")
    
    for selector in mixer_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"✅ Found {len(elements)} elements with selector: '{selector}'")
                for i, elem in enumerate(elements):
                    try:
                        print(f"   Element {i+1}: tag='{elem.tag_name}', class='{elem.get_attribute('class')}', id='{elem.get_attribute('id')}'")
                        if elem.text and len(elem.text) < 100:
                            print(f"   Text: '{elem.text.strip()}'")
                    except:
                        continue
        except Exception as e:
            continue

def inspect_download_controls(driver):
    """Look for download-related controls"""
    download_selectors = [
        "//button[contains(text(), 'Download')]",
        "//a[contains(text(), 'Download')]",
        "//input[contains(@value, 'Download')]",
        ".download-btn",
        ".download-button",
        "#download",
        "[class*='download']",
        "[id*='download']",
        "//button[contains(text(), 'Create')]",
        "//a[contains(text(), 'Create')]"
    ]
    
    print("⬇️ Searching for download controls...")
    
    for selector in download_selectors:
        try:
            if selector.startswith("//"):
                elements = driver.find_elements(By.XPATH, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
            if elements:
                print(f"✅ Found {len(elements)} elements with selector: '{selector}'")
                for i, elem in enumerate(elements):
                    try:
                        tag = elem.tag_name
                        classes = elem.get_attribute('class') or ''
                        elem_id = elem.get_attribute('id') or ''
                        text = elem.text.strip() if elem.text else ''
                        print(f"   Element {i+1}: <{tag}> class='{classes}' id='{elem_id}' text='{text}'")
                    except:
                        continue
        except:
            continue

def inspect_track_controls(driver):
    """Look for individual track control elements"""
    print("🎛️ Inspecting individual track controls...")
    
    # Get all track elements
    track_elements = driver.find_elements(By.CSS_SELECTOR, ".track")
    print(f"Found {len(track_elements)} track elements")
    
    if track_elements:
        print("\n🔍 Inspecting first few tracks for control elements...")
        for i, track in enumerate(track_elements[:3]):  # Only inspect first 3 tracks
            try:
                track_name = track.find_element(By.CSS_SELECTOR, ".track__caption").text
                data_index = track.get_attribute("data-index")
                print(f"\n--- Track {i+1}: '{track_name}' (index: {data_index}) ---")
                
                # Look for interactive elements within the track
                interactive_selectors = [
                    "button",
                    "input",
                    "a",
                    "[onclick]",
                    "[class*='toggle']",
                    "[class*='button']",
                    "[class*='control']",
                    "[data-track]",
                    "[data-index]"
                ]
                
                for selector in interactive_selectors:
                    try:
                        sub_elements = track.find_elements(By.CSS_SELECTOR, selector)
                        if sub_elements:
                            print(f"   Found {len(sub_elements)} '{selector}' elements:")
                            for j, sub_elem in enumerate(sub_elements):
                                try:
                                    tag = sub_elem.tag_name
                                    classes = sub_elem.get_attribute('class') or ''
                                    elem_id = sub_elem.get_attribute('id') or ''
                                    onclick = sub_elem.get_attribute('onclick') or ''
                                    print(f"     {j+1}. <{tag}> class='{classes}' id='{elem_id}' onclick='{onclick[:50]}...'")
                                except:
                                    continue
                    except:
                        continue
                        
            except Exception as e:
                print(f"   Error inspecting track {i+1}: {e}")

def analyze_page_source(driver):
    """Search for relevant keywords in page source"""
    print("📄 Analyzing page source for relevant keywords...")
    
    page_source = driver.page_source.lower()
    
    keywords = [
        "download",
        "create",
        "mix",
        "track",
        "toggle",
        "mute",
        "solo",
        "enable",
        "disable",
        "select",
        "checkbox",
        "radio"
    ]
    
    print("🔍 Keyword frequency analysis:")
    for keyword in keywords:
        count = page_source.count(keyword)
        if count > 0:
            print(f"   '{keyword}': {count} occurrences")
    
    # Look for JavaScript functions that might be relevant
    print("\n🔍 Searching for relevant JavaScript function names...")
    js_patterns = [
        "function.*download",
        "function.*mix",
        "function.*track",
        "function.*toggle",
        "onclick.*track",
        "onclick.*mix"
    ]
    
    import re
    for pattern in js_patterns:
        matches = re.findall(pattern, page_source, re.IGNORECASE)
        if matches:
            print(f"   Pattern '{pattern}': {len(matches)} matches")
            for match in matches[:3]:  # Show first 3 matches
                print(f"     {match[:100]}...")

if __name__ == "__main__":
    inspect_mixer_controls()