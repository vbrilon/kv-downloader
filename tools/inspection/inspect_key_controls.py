#!/usr/bin/env python3
"""
Key Controls Inspector - Focused search for key adjustment elements
"""

import time
import logging
from pathlib import Path
from karaoke_automator import KaraokeVersionAutomator, setup_logging

def inspect_key_controls():
    """Focused inspection of key/pitch adjustment controls"""
    
    # Setup debug logging
    setup_logging(debug_mode=True)
    
    # Initialize automator in debug mode (visible browser)
    automator = KaraokeVersionAutomator(headless=False, show_progress=False)
    
    try:
        # Login
        print("🔐 Logging in...")
        if not automator.login():
            print("❌ Login failed")
            return False
        
        # Get test song from config
        songs = automator.load_songs_config()
        if not songs:
            print("❌ No songs found in config")
            return False
        
        test_song = songs[0]
        test_song_url = test_song['url']
        print(f"🎵 Loading: {test_song['description'] or test_song['name']}")
        
        # Navigate to song page
        automator.driver.get(test_song_url)
        time.sleep(5)
        
        print("\n🔍 FOCUSED KEY CONTROLS SEARCH:")
        print("="*50)
        
        # Look around the pitch/key area
        try:
            # Find the key label area first
            key_label = automator.driver.find_element("css selector", ".pitch__label")
            if key_label:
                print(f"✅ Found key label: {key_label.text}")
                
                # Get the parent container
                key_container = key_label.find_element("xpath", "..")
                print(f"📦 Key container tag: {key_container.tag_name}")
                print(f"📦 Key container class: {key_container.get_attribute('class')}")
                
                # Look for all children of the key container
                children = key_container.find_elements("xpath", "./*")
                print(f"👶 Found {len(children)} child elements in key container:")
                
                for i, child in enumerate(children):
                    tag = child.tag_name
                    child_class = child.get_attribute('class') or 'N/A'
                    child_text = child.text.strip() or 'N/A'
                    child_id = child.get_attribute('id') or 'N/A'
                    
                    print(f"   [{i+1}] <{tag}> id='{child_id}' class='{child_class}' text='{child_text}'")
                    
                    # If it's a button or clickable element, show more details
                    if tag in ['button', 'a', 'span'] or 'btn' in child_class.lower():
                        onclick = child.get_attribute('onclick') or 'N/A'
                        href = child.get_attribute('href') or 'N/A'
                        print(f"       onclick='{onclick}' href='{href}'")
                        
                        # Look for sub-children that might be arrows
                        sub_children = child.find_elements("xpath", "./*")
                        if sub_children:
                            print(f"       Sub-elements: {len(sub_children)}")
                            for j, sub in enumerate(sub_children):
                                sub_tag = sub.tag_name
                                sub_class = sub.get_attribute('class') or 'N/A'
                                sub_text = sub.text.strip() or 'N/A'
                                print(f"         [{j+1}] <{sub_tag}> class='{sub_class}' text='{sub_text}'")
                
        except Exception as e:
            print(f"❌ Error finding key label: {e}")
        
        # Look for arrow-like elements near the pitch area
        print("\n🏹 SEARCHING FOR ARROW ELEMENTS:")
        arrow_selectors = [
            "//span[contains(@class, 'fa-')]",  # Font Awesome icons
            "//i[contains(@class, 'fa-')]",
            "//span[contains(@class, 'arrow')]",
            "//span[contains(@class, 'up')]",
            "//span[contains(@class, 'down')]",
            "//button[contains(@class, 'pitch')]",
            "//a[contains(@class, 'pitch')]",
            "//*[contains(@onclick, 'pitch')]",
            "//*[contains(@onclick, 'key')]"
        ]
        
        for selector in arrow_selectors:
            try:
                elements = automator.driver.find_elements("xpath", selector)
                if elements:
                    print(f"✅ Found {len(elements)} elements with xpath: {selector}")
                    for i, element in enumerate(elements[:3]):  # Show first 3
                        try:
                            tag = element.tag_name
                            element_class = element.get_attribute('class') or 'N/A'
                            element_text = element.text.strip() or 'N/A'
                            onclick = element.get_attribute('onclick') or 'N/A'
                            
                            print(f"   [{i+1}] <{tag}> class='{element_class}' text='{element_text}'")
                            if onclick != 'N/A':
                                print(f"       onclick='{onclick}'")
                                
                        except Exception as e:
                            print(f"   [{i+1}] Error: {e}")
            except Exception as e:
                print(f"❌ Xpath error: {selector} - {e}")
        
        # Check the page source for pitch-related JavaScript
        print("\n🔬 JAVASCRIPT FUNCTION SEARCH:")
        page_source = automator.driver.page_source
        
        # Look for JavaScript functions related to pitch/key
        js_patterns = [
            "pitch", "key", "transpose", "tune", "semitone"
        ]
        
        for pattern in js_patterns:
            if pattern in page_source.lower():
                print(f"✅ Found '{pattern}' in page source")
                # Extract a small snippet around the pattern
                lower_source = page_source.lower()
                start_idx = lower_source.find(pattern)
                if start_idx != -1:
                    snippet_start = max(0, start_idx - 50)
                    snippet_end = min(len(page_source), start_idx + 100)
                    snippet = page_source[snippet_start:snippet_end]
                    print(f"   Context: ...{snippet}...")
        
        # Manual instructions
        print("\n" + "="*60)
        print("🔍 MANUAL INSPECTION NEEDED:")
        print("="*60)
        print("1. Look at the browser window")
        print("2. Find the 'Key' section in the mixer")
        print("3. Look for up/down arrows or +/- buttons near the key value")
        print("4. Right-click on those buttons and 'Inspect Element'")
        print("5. Copy the exact selector/class/onclick from dev tools")
        print("\n⏸️ Browser left open for manual inspection...")
        
        # Keep browser open for 60 seconds
        print("🕐 Auto-closing in 60 seconds...")
        time.sleep(60)
        
        return True
        
    except Exception as e:
        print(f"❌ Inspection failed: {e}")
        return False
    
    finally:
        automator.driver.quit()

if __name__ == "__main__":
    print("🎵 Focused Key Controls Inspection")
    print("="*40)
    inspect_key_controls()