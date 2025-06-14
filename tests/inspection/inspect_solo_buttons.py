#!/usr/bin/env python3
"""
Inspect solo buttons on the mixer page
This will help us discover the selectors needed for track isolation via solo functionality
"""

import time
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def inspect_solo_buttons():
    """Inspect solo button controls on the mixer page"""
    print("🎛️ INSPECTING SOLO BUTTONS ON MIXER PAGE")
    print("="*60)
    
    try:
        # Use our working login system
        print("1️⃣ Initializing with working login...")
        automator = KaraokeVersionAutomator()
        
        # Login first
        if not automator.login():
            print("❌ Login failed")
            return
        
        print("✅ Login successful!")
        
        # Navigate to test song
        test_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        print(f"2️⃣ Navigating to song page: {test_url}")
        automator.driver.get(test_url)
        time.sleep(5)
        
        # Get all tracks first
        tracks = automator.get_available_tracks(test_url)
        if not tracks:
            print("❌ No tracks found")
            return
        
        print(f"✅ Found {len(tracks)} tracks")
        
        print("\n3️⃣ Inspecting each track for solo buttons...")
        
        # Look for solo buttons in each track
        for i, track_info in enumerate(tracks[:3]):  # Inspect first 3 tracks
            print(f"\n--- Track {i+1}: {track_info['name']} (index: {track_info['index']}) ---")
            
            # Get the track element
            track_elements = automator.driver.find_elements(By.CSS_SELECTOR, f".track[data-index='{track_info['index']}']")
            
            if not track_elements:
                print(f"  ❌ Could not find track element with data-index='{track_info['index']}'")
                continue
            
            track_element = track_elements[0]
            
            # Look for solo-related elements within this track
            solo_patterns = [
                # Button patterns
                "button[class*='solo']",
                "button[id*='solo']", 
                "button[data*='solo']",
                ".solo-button",
                ".btn-solo",
                
                # Input patterns
                "input[class*='solo']",
                "input[id*='solo']",
                "input[type='checkbox'][class*='solo']",
                "input[type='radio'][class*='solo']",
                
                # Generic patterns
                "*[class*='solo']",
                "*[id*='solo']",
                
                # Text-based patterns
                "//*[contains(text(), 'Solo')]",
                "//*[contains(text(), 'SOLO')]",
                "//*[contains(@title, 'solo')]",
                "//*[contains(@title, 'Solo')]"
            ]
            
            found_solo_elements = []
            
            for pattern in solo_patterns:
                try:
                    if pattern.startswith("//"):
                        # XPath pattern
                        elements = track_element.find_elements(By.XPATH, pattern)
                    else:
                        # CSS pattern
                        elements = track_element.find_elements(By.CSS_SELECTOR, pattern)
                    
                    if elements:
                        for elem in elements:
                            try:
                                tag = elem.tag_name
                                elem_class = elem.get_attribute('class') or ''
                                elem_id = elem.get_attribute('id') or ''
                                elem_text = elem.text.strip() if elem.text else ''
                                elem_title = elem.get_attribute('title') or ''
                                elem_type = elem.get_attribute('type') or ''
                                
                                element_info = {
                                    'pattern': pattern,
                                    'tag': tag,
                                    'class': elem_class,
                                    'id': elem_id,
                                    'text': elem_text,
                                    'title': elem_title,
                                    'type': elem_type,
                                    'element': elem
                                }
                                
                                found_solo_elements.append(element_info)
                                
                            except Exception as e:
                                print(f"    Error inspecting element: {e}")
                                
                except Exception as e:
                    continue
            
            if found_solo_elements:
                print(f"  ✅ Found {len(found_solo_elements)} potential solo elements:")
                for j, elem_info in enumerate(found_solo_elements):
                    print(f"    {j+1}. <{elem_info['tag']} type='{elem_info['type']}'> class='{elem_info['class'][:30]}' id='{elem_info['id']}'")
                    if elem_info['text']:
                        print(f"       text='{elem_info['text'][:30]}'")
                    if elem_info['title']:
                        print(f"       title='{elem_info['title'][:30]}'")
                    print(f"       pattern='{elem_info['pattern']}'")
                    print()
            else:
                print(f"  ❌ No solo elements found in this track")
        
        print("\n4️⃣ Looking for global solo controls...")
        
        # Look for solo controls outside of individual tracks
        global_solo_patterns = [
            "button[class*='solo']",
            "input[class*='solo']", 
            ".solo",
            "[data-track-action='solo']",
            "[data-action='solo']"
        ]
        
        for pattern in global_solo_patterns:
            try:
                elements = automator.driver.find_elements(By.CSS_SELECTOR, pattern)
                if elements:
                    print(f"  Found {len(elements)} global elements matching '{pattern}':")
                    for elem in elements[:3]:  # Show first 3
                        try:
                            print(f"    <{elem.tag_name}> class='{elem.get_attribute('class')}' text='{elem.text[:20]}'")
                        except:
                            continue
            except:
                continue
        
        print("\n5️⃣ Analyzing page HTML for 'solo' references...")
        
        # Search page source for solo-related content
        page_source = automator.driver.page_source.lower()
        
        solo_keywords = ['solo', 'mute', 'isolate', 'only']
        for keyword in solo_keywords:
            count = page_source.count(keyword)
            if count > 0:
                print(f"  '{keyword}': {count} occurrences in page source")
        
        # Look for JavaScript functions that might handle solo
        import re
        js_solo_patterns = [
            r'function.*solo.*\(',
            r'\.solo\s*\(',
            r'solo.*=.*function',
            r'onclick.*solo',
            r'data-.*solo'
        ]
        
        print(f"\n6️⃣ Searching for solo-related JavaScript...")
        for pattern in js_solo_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                print(f"  Pattern '{pattern}': {len(matches)} matches")
                for match in matches[:2]:  # Show first 2
                    print(f"    {match[:60]}...")
        
        print(f"\n🔍 Browser staying open for 60 seconds for manual inspection...")
        print("Please manually inspect the mixer controls and look for:")
        print("- Solo buttons for each track")
        print("- Mute buttons for each track") 
        print("- Any toggle controls")
        print("- Track isolation mechanisms")
        time.sleep(60)
        
    except Exception as e:
        print(f"❌ Error during inspection: {e}")
    finally:
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    inspect_solo_buttons()