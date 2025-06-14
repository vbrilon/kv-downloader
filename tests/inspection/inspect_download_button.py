#!/usr/bin/env python3
"""
Inspect download button after track is soloed
This will help us find the actual download button selectors
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def inspect_download_button():
    """Inspect download button after soloing a track"""
    print("⬇️ INSPECTING DOWNLOAD BUTTON AFTER TRACK SOLO")
    print("="*60)
    
    song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
    
    try:
        # Initialize and login
        print("1️⃣ Initializing and logging in...")
        automator = KaraokeVersionAutomator()
        
        if not automator.login():
            print("❌ Login failed")
            return
        
        print("✅ Login successful!")
        
        # Get tracks and solo bass
        print("2️⃣ Getting tracks and soloing bass...")
        tracks = automator.get_available_tracks(song_url)
        bass_tracks = [t for t in tracks if 'bass' in t['name'].lower()]
        
        if bass_tracks:
            bass_track = bass_tracks[0]
            print(f"Soloing: {bass_track['name']}")
            automator.solo_track(bass_track, song_url)
            time.sleep(3)  # Wait for UI to update
        
        print("3️⃣ Searching for download buttons...")
        
        # Look for download-related buttons using automator's driver
        found_buttons = _discover_download_buttons(automator.driver)
        
        print(f"\n4️⃣ Summary: Found {len(found_buttons)} potential download buttons")
        
        if found_buttons:
            print("\nMost likely download buttons:")
            priority_buttons = []
            
            for btn in found_buttons:
                score = 0
                text_lower = btn['text'].lower()
                
                # Score buttons based on relevance
                if 'download' in text_lower:
                    score += 10
                if 'create' in text_lower:
                    score += 8
                if 'generate' in text_lower:
                    score += 6
                if 'export' in text_lower:
                    score += 5
                if 'get' in text_lower:
                    score += 3
                
                if btn['visible'] and btn['enabled']:
                    score += 5
                
                if btn['text']:  # Has visible text
                    score += 2
                
                priority_buttons.append((score, btn))
            
            # Sort by score
            priority_buttons.sort(key=lambda x: x[0], reverse=True)
            
            print("\nTop candidates (by relevance score):")
            for i, (score, btn) in enumerate(priority_buttons[:5]):
                print(f"  {i+1}. Score: {score} - '{btn['text']}' ({btn['tag']})")
                print(f"     Pattern: {btn['pattern']}")
                print(f"     Class: {btn['class'][:50]}")
                print()
        
        # Search page source for download-related content
        print("5️⃣ Analyzing page source...")
        _analyze_page_source(automator.driver)
        
        # Manual inspection
        print("\n6️⃣ Manual inspection time...")
        print("Browser staying open for 60 seconds.")
        print("Please manually look for:")
        print("- Download button location")
        print("- Create/Generate buttons")
        print("- Any buttons that appear after soloing")
        print("- Button text and styling")
        time.sleep(60)
        
    except Exception as e:
        print(f"❌ Error during inspection: {e}")
    finally:
        try:
            automator.driver.quit()
        except:
            pass

def _discover_download_buttons(driver):
    """Helper function to discover download buttons using the provided driver"""
    from selenium.webdriver.common.by import By
    
    download_patterns = [
        # Direct download text (case insensitive)
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download')]",
        "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download')]",
        "//input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download')]",
        
        # Simple case sensitive
        "//button[contains(text(), 'Download')]",
        "//a[contains(text(), 'Download')]",
        "//button[contains(text(), 'DOWNLOAD')]",
        
        # Create/Generate (common for custom tracks)
        "//button[contains(text(), 'Create')]",
        "//a[contains(text(), 'Create')]",
        "//button[contains(text(), 'Generate')]",
        "//button[contains(text(), 'CREATE')]",
        
        # Export related
        "//button[contains(text(), 'Export')]",
        "//a[contains(text(), 'Export')]",
        
        # Get/Obtain
        "//button[contains(text(), 'Get')]",
        "//a[contains(text(), 'Get')]",
        
        # All buttons and links (broad search)
        "//button",
        "//a[@href]",
        "//input[@type='submit']",
        "//input[@type='button']",
        
        # CSS selectors
        "button[class*='download']",
        "a[class*='download']",
        ".download-btn",
        ".download-button",
        ".btn-download",
        
        ".create-btn",
        ".create-button", 
        ".btn-create",
        
        ".export-btn",
        ".export-button",
        
        # ID selectors
        "#download",
        "#create",
        "#export",
        "[id*='download']",
        "[id*='create']",
        "[id*='export']"
    ]
    
    found_buttons = []
    
    for pattern in download_patterns:
        try:
            if pattern.startswith("//"):
                elements = driver.find_elements(By.XPATH, pattern)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, pattern)
            
            if elements:
                print(f"\n✅ Found {len(elements)} elements with pattern: '{pattern}'")
                
                for i, elem in enumerate(elements):
                    try:
                        tag = elem.tag_name
                        text = elem.text.strip()
                        classes = elem.get_attribute('class') or ''
                        elem_id = elem.get_attribute('id') or ''
                        href = elem.get_attribute('href') or ''
                        onclick = elem.get_attribute('onclick') or ''
                        visible = elem.is_displayed()
                        enabled = elem.is_enabled()
                        
                        button_info = {
                            'pattern': pattern,
                            'tag': tag,
                            'text': text,
                            'class': classes,
                            'id': elem_id,
                            'href': href,
                            'onclick': onclick,
                            'visible': visible,
                            'enabled': enabled,
                            'element': elem
                        }
                        
                        found_buttons.append(button_info)
                        
                        print(f"  {i+1}. <{tag}> text='{text}' class='{classes[:30]}'")
                        print(f"     visible={visible} enabled={enabled}")
                        if href:
                            print(f"     href='{href[:50]}'")
                        if onclick:
                            print(f"     onclick='{onclick[:50]}...'")
                        print()
                        
                    except Exception as e:
                        print(f"     Error inspecting element: {e}")
                        
        except Exception as e:
            continue
    
    return found_buttons

def _analyze_page_source(driver):
    """Helper function to analyze page source for download keywords"""
    page_source = driver.page_source.lower()
    
    download_keywords = ['download', 'create', 'generate', 'export', 'get mp3', 'get file']
    for keyword in download_keywords:
        count = page_source.count(keyword)
        if count > 0:
            print(f"  '{keyword}': {count} occurrences")

if __name__ == "__main__":
    inspect_download_button()