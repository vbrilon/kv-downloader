#!/usr/bin/env python3
"""
Inspect mixer controls and download process on Karaoke-Version.com
This tool will help discover the selectors needed for track selection and downloading.
"""

import time
import os
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent))
import config

def inspect_mixer_controls():
    """Inspect mixer controls and download elements"""
    print("🔍 Starting mixer controls inspection...")
    
    # Setup Chrome driver
    chrome_options = Options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 10)
    
    try:
        # Navigate to homepage and login
        print("📱 Navigating to homepage...")
        driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # Login
        print("🔐 Attempting login...")
        login_successful = attempt_login(driver, wait)
        
        if not login_successful:
            print("❌ Login failed - cannot inspect protected content")
            return
            
        # Navigate to test song
        test_song_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
        print(f"🎵 Navigating to test song: {test_song_url}")
        driver.get(test_song_url)
        time.sleep(5)
        
        print("\n" + "="*80)
        print("MIXER CONTROLS INSPECTION")
        print("="*80)
        
        # Look for mixer/player controls
        inspect_mixer_area(driver)
        
        print("\n" + "="*80)
        print("DOWNLOAD CONTROLS INSPECTION")
        print("="*80)
        
        # Look for download buttons
        inspect_download_controls(driver)
        
        print("\n" + "="*80)
        print("TRACK CONTROL ELEMENTS INSPECTION")
        print("="*80)
        
        # Inspect individual track controls
        inspect_track_controls(driver)
        
        print("\n" + "="*80)
        print("PAGE SOURCE ANALYSIS")
        print("="*80)
        
        # Search for relevant keywords in page source
        analyze_page_source(driver)
        
        # Keep browser open for manual inspection
        print("\n🔍 Browser will stay open for 30 seconds for manual inspection...")
        print("Use this time to manually explore the page controls.")
        time.sleep(30)
        
    except Exception as e:
        print(f"❌ Error during inspection: {e}")
    finally:
        driver.quit()
        print("✅ Inspection completed")

def attempt_login(driver, wait):
    """Attempt to login with credentials"""
    try:
        # Look for login link
        login_selectors = [
            "//a[contains(text(), 'Log In')]",
            "//a[contains(text(), 'Login')]",
            "//a[contains(text(), 'Sign In')]"
        ]
        
        for selector in login_selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                if element and element.is_displayed():
                    print(f"🔗 Clicking login link: '{element.text}'")
                    element.click()
                    time.sleep(3)
                    break
            except:
                continue
        
        # Find username field
        username_field = None
        username_selectors = [
            (By.NAME, "email"),
            (By.NAME, "username"),
            (By.ID, "email"),
            (By.CSS_SELECTOR, "input[type='email']")
        ]
        
        for selector_type, selector_value in username_selectors:
            try:
                username_field = wait.until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                if username_field and username_field.is_displayed():
                    break
            except:
                continue
                
        if not username_field:
            print("❌ Could not find username field")
            return False
        
        # Find password field
        password_field = driver.find_element(By.NAME, "password")
        
        # Fill credentials
        username_field.clear()
        username_field.send_keys(config.USERNAME)
        password_field.clear()
        password_field.send_keys(config.PASSWORD)
        
        # Submit
        submit_button = driver.find_element(By.XPATH, "//input[@type='submit'] | //button[@type='submit']")
        submit_button.click()
        
        time.sleep(5)
        
        # Check if logged in
        hello_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Hello')]")
        if hello_elements:
            print("✅ Login successful!")
            return True
        else:
            print("❌ Login may have failed")
            return False
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False

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