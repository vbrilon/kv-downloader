"""Login management for Karaoke-Version.com authentication"""

import time
import logging
import json
import pickle
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

try:
    from packages.configuration import USERNAME, PASSWORD
except ImportError:
    # Fallback for when config is not available during testing
    USERNAME = None
    PASSWORD = None


class LoginManager:
    """Handles all login-related functionality for Karaoke-Version.com"""
    
    def __init__(self, driver, wait, session_file="session_data.pkl"):
        """
        Initialize login manager
        
        Args:
            driver: Selenium WebDriver instance
            wait: WebDriverWait instance
            session_file: Path to file for storing session data (cookies, etc.)
        """
        self.driver = driver
        self.wait = wait
        self.session_file = Path(session_file)
        
        # Create session storage directory if it doesn't exist
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
    
    def is_logged_in(self):
        """Check if user is currently logged in"""
        try:
            # Primary check: Look for "My Account" in header
            my_account_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'My Account')]")
            if my_account_elements:
                logging.info("✅ User is logged in: Found 'My Account' in header")
                return True
            
            # Secondary check: No login links present
            login_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Log in')]")
            if not login_links:
                logging.info("✅ User appears logged in: No login links found")
                return True
            
            logging.info("❌ User is not logged in")
            return False
            
        except Exception as e:
            logging.error(f"Error checking login status: {e}")
            return False
    
    def logout(self):
        """Logout from the current session"""
        try:
            # Look for logout/account links
            logout_selectors = [
                "//a[contains(text(), 'Log out')]",
                "//a[contains(text(), 'Logout')]", 
                "//a[contains(text(), 'Sign out')]",
                "//a[contains(text(), 'My Account')]"
            ]
            
            for selector in logout_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        if "my account" in element.text.lower():
                            # Click My Account to access logout
                            element.click()
                            time.sleep(2)
                            # Now look for logout within account area
                            logout_element = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Log out')]")
                            logout_element.click()
                        else:
                            # Direct logout link
                            element.click()
                        
                        time.sleep(3)
                        logging.info("Logout completed")
                        return True
                except:
                    continue
            
            # Alternative: Clear cookies to force logout
            logging.info("Direct logout not found, clearing session cookies")
            self.driver.delete_all_cookies()
            self.driver.refresh()
            time.sleep(3)
            return True
            
        except Exception as e:
            logging.error(f"Error during logout: {e}")
            # Fallback: clear cookies
            try:
                self.driver.delete_all_cookies()
                self.driver.refresh()
                time.sleep(3)
                return True
            except:
                return False
    
    def click_login_link(self):
        """Find and click the login link"""
        try:
            login_selectors = [
                "//a[contains(text(), 'Log in')]",  # Working selector
                "//a[contains(text(), 'Log In')]",
                "//a[contains(text(), 'Login')]",
                "//a[contains(text(), 'Sign In')]"
            ]
            
            for selector in login_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        logging.info(f"Clicking login link: '{element.text}'")
                        element.click()
                        time.sleep(3)
                        return True
                except:
                    continue
            
            logging.warning("No login link found")
            return False
            
        except Exception as e:
            logging.error(f"Error clicking login link: {e}")
            return False
    
    def fill_login_form(self, username, password):
        """Fill and submit the login form"""
        try:
            # Find username field
            username_selectors = [
                (By.NAME, "frm_login"),  # Working selector for Karaoke-Version.com
                (By.NAME, "email"),
                (By.NAME, "username"),
                (By.ID, "email"),
                (By.CSS_SELECTOR, "input[type='email']")
            ]
            
            username_field = None
            for selector_type, selector_value in username_selectors:
                try:
                    username_field = self.wait.until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    if username_field and username_field.is_displayed():
                        logging.info(f"Found username field: {selector_type} = '{selector_value}'")
                        break
                except:
                    continue
            
            if not username_field:
                logging.error("Could not find username field")
                return False
            
            # Find password field
            password_selectors = [
                (By.NAME, "frm_password"),  # Working selector for Karaoke-Version.com
                (By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]
            
            password_field = None
            for selector_type, selector_value in password_selectors:
                try:
                    password_field = self.driver.find_element(selector_type, selector_value)
                    if password_field and password_field.is_displayed():
                        logging.info(f"Found password field: {selector_type} = '{selector_value}'")
                        break
                except:
                    continue
            
            if not password_field:
                logging.error("Could not find password field")
                return False
            
            # Fill credentials
            logging.info("Filling in credentials...")
            username_field.clear()
            username_field.send_keys(username)
            password_field.clear()
            password_field.send_keys(password)
            
            # Find and click submit button
            submit_selectors = [
                (By.NAME, "sbm"),  # Working selector for Karaoke-Version.com
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']")
            ]
            
            submit_button = None
            for selector_type, selector_value in submit_selectors:
                try:
                    submit_button = self.driver.find_element(selector_type, selector_value)
                    if submit_button and submit_button.is_displayed():
                        logging.info(f"Found submit button: {selector_type} = '{selector_value}'")
                        break
                except:
                    continue
            
            if not submit_button:
                logging.error("Could not find submit button")
                return False
            
            # Submit form
            submit_button.click()
            logging.info("Login form submitted")
            time.sleep(5)  # Wait for login to process
            
            return True
            
        except Exception as e:
            logging.error(f"Error filling login form: {e}")
            return False
    
    def login(self, username=None, password=None, force_relogin=False):
        """Complete login process with optimized login checking
        
        Args:
            username (str): Username (uses config if not provided)
            password (str): Password (uses config if not provided)  
            force_relogin (bool): Force re-login even if already logged in
        """
        # Use config credentials if not provided
        if not username:
            username = USERNAME
        if not password:
            password = PASSWORD
        
        if not username or not password:
            logging.error("Username or password not provided")
            return False
        
        logging.info("Starting optimized login process...")
        
        # Navigate to homepage to check current login status
        self.driver.get("https://www.karaoke-version.com")
        time.sleep(3)
        
        # Check if already logged in (unless forced)
        if not force_relogin and self.is_logged_in():
            logging.info("✅ Already logged in - skipping login process")
            logging.info("💡 Use force_relogin=True to force re-authentication")
            return True
        
        if force_relogin:
            logging.info("🔄 Force re-login requested")
            # If already logged in, need to logout first
            if self.is_logged_in():
                logging.info("Already logged in - logging out first for force re-login")
                if not self.logout():
                    logging.warning("Logout failed, continuing with login attempt")
        
        # Click login link
        if not self.click_login_link():
            logging.error("Could not access login page")
            return False
        
        # Fill and submit login form
        if not self.fill_login_form(username, password):
            logging.error("Could not fill login form")
            return False
        
        # Verify login success
        if self.is_logged_in():
            logging.info("✅ Login successful!")
            # Save session data for future use
            self.save_session()
            return True
        else:
            logging.error("❌ Login failed - verification unsuccessful")
            return False
    
    def save_session(self):
        """Save current browser session data (cookies, localStorage, etc.) to file"""
        try:
            session_data = {
                'cookies': self.driver.get_cookies(),
                'url': self.driver.current_url,
                'timestamp': time.time(),
                'user_agent': self.driver.execute_script("return navigator.userAgent"),
                'window_size': self.driver.get_window_size()
            }
            
            # Try to get localStorage data (actual key-value pairs only)
            try:
                local_storage_script = """
                var storage = {};
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    storage[key] = localStorage.getItem(key);
                }
                return storage;
                """
                local_storage = self.driver.execute_script(local_storage_script)
                session_data['localStorage'] = local_storage
            except Exception as e:
                logging.debug(f"Could not save localStorage: {e}")
                session_data['localStorage'] = {}
            
            # Try to get sessionStorage data (actual key-value pairs only)
            try:
                session_storage_script = """
                var storage = {};
                for (var i = 0; i < sessionStorage.length; i++) {
                    var key = sessionStorage.key(i);
                    storage[key] = sessionStorage.getItem(key);
                }
                return storage;
                """
                session_storage = self.driver.execute_script(session_storage_script)
                session_data['sessionStorage'] = session_storage
            except Exception as e:
                logging.debug(f"Could not save sessionStorage: {e}")
                session_data['sessionStorage'] = {}
            
            # Save to file
            with open(self.session_file, 'wb') as f:
                pickle.dump(session_data, f)
            
            logging.info(f"💾 Session data saved to {self.session_file}")
            return True
            
        except Exception as e:
            logging.warning(f"⚠️ Could not save session data: {e}")
            return False
    
    def load_session(self):
        """Load and restore browser session data from file"""
        try:
            if not self.session_file.exists():
                logging.debug("No session file found")
                return False
            
            # Load session data
            with open(self.session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            # Check if session is not too old (24 hours max)
            session_age = time.time() - session_data.get('timestamp', 0)
            max_age = 24 * 60 * 60  # 24 hours in seconds
            
            if session_age > max_age:
                logging.info(f"🕐 Saved session is {session_age/3600:.1f} hours old, too old to use")
                self.clear_session()
                return False
            
            logging.info(f"🔄 Loading session from {session_age/60:.1f} minutes ago")
            
            # Navigate to the saved URL first
            saved_url = session_data.get('url', 'https://www.karaoke-version.com')
            self.driver.get(saved_url)
            time.sleep(2)
            
            # Restore cookies
            cookies = session_data.get('cookies', [])
            for cookie in cookies:
                try:
                    # Keep all cookie attributes, but handle expiry specially
                    cookie_copy = cookie.copy()
                    
                    # Handle expiry - convert to int if present
                    if 'expiry' in cookie_copy:
                        try:
                            cookie_copy['expiry'] = int(cookie_copy['expiry'])
                        except:
                            del cookie_copy['expiry']
                    
                    self.driver.add_cookie(cookie_copy)
                    logging.debug(f"Restored cookie: {cookie.get('name', 'unknown')}")
                except Exception as e:
                    logging.debug(f"Could not restore cookie {cookie.get('name', 'unknown')}: {e}")
                    # Try with minimal attributes as fallback
                    try:
                        minimal_cookie = {
                            'name': cookie.get('name'),
                            'value': cookie.get('value'),
                            'domain': cookie.get('domain'),
                            'path': cookie.get('path', '/'),
                            'secure': cookie.get('secure', False)
                        }
                        self.driver.add_cookie(minimal_cookie)
                        logging.debug(f"Restored cookie with minimal attributes: {cookie.get('name', 'unknown')}")
                    except Exception as e2:
                        logging.debug(f"Failed to restore cookie even with minimal attributes: {e2}")
            
            # Restore localStorage
            local_storage = session_data.get('localStorage', {})
            if local_storage and isinstance(local_storage, dict):
                for key, value in local_storage.items():
                    try:
                        # Use JSON.stringify to safely encode the value
                        self.driver.execute_script(
                            "window.localStorage.setItem(arguments[0], arguments[1]);", 
                            key, str(value)
                        )
                        logging.debug(f"Restored localStorage: {key}")
                    except Exception as e:
                        logging.debug(f"Could not restore localStorage item {key}: {e}")
            
            # Restore sessionStorage
            session_storage = session_data.get('sessionStorage', {})
            if session_storage and isinstance(session_storage, dict):
                for key, value in session_storage.items():
                    try:
                        # Use arguments to safely pass values to avoid injection issues
                        self.driver.execute_script(
                            "window.sessionStorage.setItem(arguments[0], arguments[1]);", 
                            key, str(value)
                        )
                        logging.debug(f"Restored sessionStorage: {key}")
                    except Exception as e:
                        logging.debug(f"Could not restore sessionStorage item {key}: {e}")
            
            # Refresh page to apply restored session
            self.driver.refresh()
            time.sleep(3)
            
            # Try accessing a protected area to trigger session validation
            try:
                # Navigate to account page which should validate session
                self.driver.get("https://www.karaoke-version.com/my/index.html")
                time.sleep(3)
                
                # Check if we were redirected to login page
                current_url = self.driver.current_url
                if "login" in current_url.lower() or "signin" in current_url.lower():
                    logging.debug("Redirected to login page, session invalid")
                    return False
                    
            except Exception as e:
                logging.debug(f"Error accessing account page: {e}")
            
            # Go back to home page and verify login status
            self.driver.get("https://www.karaoke-version.com")
            time.sleep(3)
            
            # Verify the session restoration worked by checking login status
            if self.is_logged_in():
                logging.info("✅ Session data restored and login verified")
                return True
            else:
                logging.warning("⚠️ Session data restored but login verification failed")
                return False
            
        except Exception as e:
            logging.warning(f"⚠️ Could not load session data: {e}")
            return False
    
    def clear_session(self):
        """Clear saved session data"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                logging.info("🗑️ Cleared saved session data")
            return True
        except Exception as e:
            logging.warning(f"⚠️ Could not clear session data: {e}")
            return False
    
    def is_session_valid(self):
        """Check if there's a valid saved session without loading it"""
        try:
            if not self.session_file.exists():
                return False
            
            with open(self.session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            # Check age
            session_age = time.time() - session_data.get('timestamp', 0)
            max_age = 24 * 60 * 60  # 24 hours
            
            return session_age <= max_age
            
        except Exception:
            return False
    
    def login_with_session_persistence(self, username=None, password=None, force_relogin=False):
        """Enhanced login with session persistence - checks Chrome's native session first"""
        username = username or USERNAME
        password = password or PASSWORD
        
        if not username or not password:
            logging.error("Username and password are required for login")
            return False
        
        # If not forcing relogin, check Chrome's native session first
        if not force_relogin:
            logging.info("🔍 Checking Chrome's native session...")
            
            # Navigate to homepage and check if already logged in via Chrome's persistent cookies
            self.driver.get("https://www.karaoke-version.com")
            time.sleep(3)
            
            if self.is_logged_in():
                logging.info("🎉 Already logged in via Chrome's persistent session!")
                logging.info("⚡ Login skipped - using Chrome's native session persistence")
                # Still save session data for our tracking
                self.save_session()
                return True
            else:
                logging.info("💡 Chrome's native session not logged in")
        else:
            logging.info("🔄 Force relogin requested")
        
        # Fall back to regular login process
        logging.info("🔐 Proceeding with fresh login...")
        return self.login(username, password, force_relogin=False)  # Don't double force