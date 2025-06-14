#!/usr/bin/env python3
"""
Inspect the actual login form structure to find correct selectors
"""

import time
import sys
from pathlib import Path
from selenium.webdriver.common.by import By

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def inspect_login_form():
    """Navigate to login page and inspect the actual form structure"""
    print("🔍 INSPECTING LOGIN FORM STRUCTURE")
    print("="*60)
    
    try:
        # Initialize automator (don't login, just get to login page)
        print("1️⃣ Initializing automator...")
        automator = KaraokeVersionAutomator()
        
        # Navigate to homepage
        print("2️⃣ Navigating to homepage...")
        automator.driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # Click login link
        print("3️⃣ Clicking login link...")
        login_link = automator.driver.find_element(By.XPATH, "//a[contains(text(), 'Log in')]")
        login_link.click()
        time.sleep(3)
        
        print(f"Login page URL: {automator.driver.current_url}")
        
        # Inspect all input fields
        print("\n4️⃣ Inspecting all input fields on login page...")
        _inspect_form_elements(automator.driver)
        
        # Manual inspection time
        print("5️⃣ Manual inspection time...")
        print("Browser will stay open for 60 seconds.")
        print("Please manually inspect the login form and note:")
        print("- Email/username field selector")
        print("- Password field selector") 
        print("- Submit button selector")
        print("- Any special form handling needed")
        
        time.sleep(60)
        
    except Exception as e:
        print(f"❌ Error during inspection: {e}")
    finally:
        try:
            automator.driver.quit()
        except:
            pass

def _inspect_form_elements(driver):
    """Helper function to inspect form elements"""
    # Inspect all input fields
    input_fields = driver.find_elements(By.TAG_NAME, "input")
    
    print(f"Found {len(input_fields)} input fields:")
    for i, field in enumerate(input_fields):
        try:
            field_type = field.get_attribute('type') or 'text'
            field_name = field.get_attribute('name') or 'no-name'
            field_id = field.get_attribute('id') or 'no-id'
            field_class = field.get_attribute('class') or 'no-class'
            field_placeholder = field.get_attribute('placeholder') or 'no-placeholder'
            
            print(f"  Field {i+1}:")
            print(f"    Type: {field_type}")
            print(f"    Name: {field_name}")
            print(f"    ID: {field_id}")
            print(f"    Class: {field_class}")
            print(f"    Placeholder: {field_placeholder}")
            print(f"    Visible: {field.is_displayed()}")
            print()
        except Exception as e:
            print(f"  Field {i+1}: Error inspecting - {e}")
    
    # Inspect all buttons
    print("Inspecting all buttons...")
    buttons = driver.find_elements(By.TAG_NAME, "button")
    
    print(f"Found {len(buttons)} buttons:")
    for i, button in enumerate(buttons):
        try:
            button_type = button.get_attribute('type') or 'button'
            button_text = button.text.strip()
            button_class = button.get_attribute('class') or 'no-class'
            button_id = button.get_attribute('id') or 'no-id'
            
            print(f"  Button {i+1}:")
            print(f"    Type: {button_type}")
            print(f"    Text: '{button_text}'")
            print(f"    Class: {button_class}")
            print(f"    ID: {button_id}")
            print(f"    Visible: {button.is_displayed()}")
            print()
        except Exception as e:
            print(f"  Button {i+1}: Error inspecting - {e}")
    
    # Look for forms
    print("Inspecting forms...")
    forms = driver.find_elements(By.TAG_NAME, "form")
    
    print(f"Found {len(forms)} forms:")
    for i, form in enumerate(forms):
        try:
            form_action = form.get_attribute('action') or 'no-action'
            form_method = form.get_attribute('method') or 'no-method'
            form_class = form.get_attribute('class') or 'no-class'
            form_id = form.get_attribute('id') or 'no-id'
            
            print(f"  Form {i+1}:")
            print(f"    Action: {form_action}")
            print(f"    Method: {form_method}")
            print(f"    Class: {form_class}")
            print(f"    ID: {form_id}")
            
            # Find inputs within this form
            form_inputs = form.find_elements(By.TAG_NAME, "input")
            print(f"    Contains {len(form_inputs)} input fields")
            print()
        except Exception as e:
            print(f"  Form {i+1}: Error inspecting - {e}")

if __name__ == "__main__":
    inspect_login_form()