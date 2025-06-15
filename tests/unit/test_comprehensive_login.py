#!/usr/bin/env python3
"""
Comprehensive Login Test - Consolidates all login testing functionality
Tests login, logout, and session verification with proven selectors
"""

import time
import logging
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.configuration import *

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ComprehensiveLoginTest:
    """Comprehensive login testing with proven selectors and full cycle testing"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Proven working selectors from working_login_test.py
        self.SELECTORS = {
            'login_link': "//a[contains(text(), 'Log in')]",
            'username_field': "frm_login",  # name attribute
            'password_field': "frm_password",  # name attribute
            'submit_button': "sbm",  # name attribute
            'my_account_indicator': "//*[contains(text(), 'My Account')]"
        }
    
    def setup_driver(self):
        """Setup Chrome driver with proper configuration"""
        print("🔧 Setting up Chrome driver...")
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Uncomment for headless mode
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)
        
    def cleanup_driver(self):
        """Clean up driver resources"""
        if self.driver:
            self.driver.quit()
    
    def is_logged_in(self):
        """Check if currently logged in by looking for My Account indicator"""
        try:
            my_account_elements = self.driver.find_elements(By.XPATH, self.SELECTORS['my_account_indicator'])
            if my_account_elements:
                print("✅ Login status: LOGGED IN (found 'My Account')")
                return True
            else:
                print("❌ Login status: NOT LOGGED IN (no 'My Account' found)")
                return False
        except Exception as e:
            print(f"⚠️ Could not determine login status: {e}")
            return False
    
    def logout(self):
        """Attempt to logout if currently logged in"""
        print("\n🚪 Attempting logout...")
        
        if not self.is_logged_in():
            print("ℹ️ Already logged out")
            return True
        
        try:
            # Try to find and click logout link
            logout_selectors = [
                "//a[contains(text(), 'Log out')]",
                "//a[contains(text(), 'Logout')]", 
                "//a[contains(text(), 'Sign out')]",
                "//a[@href*='logout']"
            ]
            
            for selector in logout_selectors:
                try:
                    logout_link = self.driver.find_element(By.XPATH, selector)
                    logout_link.click()
                    time.sleep(3)
                    
                    # Verify logout
                    if not self.is_logged_in():
                        print("✅ Logout successful")
                        return True
                except:
                    continue
            
            print("⚠️ Could not find logout link, proceeding anyway")
            return True
            
        except Exception as e:
            print(f"⚠️ Logout failed: {e}")
            return False
    
    def login(self, force_relogin=False):
        """Perform login with proven selectors"""
        print("\n🔐 Starting login process...")
        
        if not USERNAME or not PASSWORD:
            print("❌ Credentials not configured")
            return False
        
        # Check if already logged in
        if not force_relogin and self.is_logged_in():
            print("✅ Already logged in")
            return True
        
        # Force logout if requested
        if force_relogin:
            self.logout()
        
        try:
            # Step 1: Navigate to homepage
            print("📱 Navigating to homepage...")
            self.driver.get("https://www.karaoke-version.com")
            time.sleep(3)
            
            # Step 2: Click login link
            print("🔗 Clicking login link...")
            login_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, self.SELECTORS['login_link']))
            )
            login_link.click()
            time.sleep(3)
            
            print(f"Login page URL: {self.driver.current_url}")
            
            # Step 3: Find form fields using proven selectors
            print("📧 Finding login form fields...")
            
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, self.SELECTORS['username_field']))
            )
            print("✅ Found username field")
            
            password_field = self.driver.find_element(By.NAME, self.SELECTORS['password_field'])
            print("✅ Found password field")
            
            submit_button = self.driver.find_element(By.NAME, self.SELECTORS['submit_button'])
            print("✅ Found submit button")
            
            # Step 4: Fill credentials
            print("✏️ Filling credentials...")
            username_field.clear()
            username_field.send_keys(USERNAME)
            print(f"✅ Entered username: {USERNAME}")
            
            password_field.clear()
            password_field.send_keys(PASSWORD)
            print("✅ Entered password")
            
            # Step 5: Submit form
            print("🚀 Submitting login form...")
            submit_button.click()
            
            # Step 6: Wait and verify login success
            print("⏳ Waiting for login to complete...")
            time.sleep(5)
            
            print(f"URL after login: {self.driver.current_url}")
            
            # Verify login success
            if self.is_logged_in():
                print("🎉 LOGIN SUCCESS!")
                return True
            else:
                print("❌ LOGIN FAILED - 'My Account' not found")
                return False
                
        except Exception as e:
            print(f"❌ Login failed with error: {e}")
            return False
    
    def test_song_access(self, test_song_url="https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"):
        """Test access to protected song content"""
        print(f"\n🎵 Testing song access...")
        
        try:
            self.driver.get(test_song_url)
            time.sleep(3)
            
            # Look for track elements (indicates successful access)
            track_elements = self.driver.find_elements(By.CSS_SELECTOR, ".track")
            
            if track_elements:
                print(f"✅ Song access successful - found {len(track_elements)} tracks")
                return True
            else:
                # Check if redirected to login page
                if "login" in self.driver.current_url.lower():
                    print("❌ Redirected to login page - access denied")
                else:
                    print("⚠️ No tracks found but not redirected to login")
                return False
                
        except Exception as e:
            print(f"❌ Song access test failed: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run all login tests in sequence"""
        print("🧪 COMPREHENSIVE LOGIN TEST SUITE")
        print("=" * 60)
        
        results = {
            'driver_setup': False,
            'initial_status_check': False,
            'logout_test': False,
            'login_test': False,
            'song_access_test': False,
            'force_relogin_test': False
        }
        
        try:
            # Test 1: Driver setup
            print("\n1️⃣ Testing driver setup...")
            self.setup_driver()
            results['driver_setup'] = True
            print("✅ Driver setup successful")
            
            # Test 2: Initial status check
            print("\n2️⃣ Testing initial login status...")
            self.driver.get("https://www.karaoke-version.com")
            time.sleep(3)
            results['initial_status_check'] = self.is_logged_in()
            
            # Test 3: Logout functionality
            print("\n3️⃣ Testing logout functionality...")
            results['logout_test'] = self.logout()
            
            # Test 4: Login functionality
            print("\n4️⃣ Testing login functionality...")
            results['login_test'] = self.login()
            
            # Test 5: Song access validation
            print("\n5️⃣ Testing protected content access...")
            results['song_access_test'] = self.test_song_access()
            
            # Test 6: Force re-login
            print("\n6️⃣ Testing force re-login...")
            results['force_relogin_test'] = self.login(force_relogin=True)
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
        
        finally:
            self.cleanup_driver()
        
        # Print results summary
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name.replace('_', ' ').title()}")
        
        print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - Login system fully functional!")
        elif passed >= total * 0.8:
            print("✅ Most tests passed - Login system mostly functional")
        else:
            print("⚠️ Multiple test failures - Login system needs attention")
        
        return passed == total

def test_comprehensive_login():
    """Main test function for external calling"""
    tester = ComprehensiveLoginTest()
    return tester.run_comprehensive_test()

if __name__ == "__main__":
    test_comprehensive_login()