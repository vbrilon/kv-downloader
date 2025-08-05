"""Login management for Karaoke-Version.com authentication"""

import time
import logging
import pickle
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    ElementClickInterceptedException,
    WebDriverException,
    StaleElementReferenceException
)

try:
    from packages.configuration import USERNAME, PASSWORD
except ImportError:
    # Fallback for when config is not available during testing
    USERNAME = None
    PASSWORD = None

from packages.utils import selenium_safe, validation_safe, profile_timing, profile_selenium
from packages.configuration.config import SESSION_MAX_AGE_SECONDS


class LoginManager:
    """Handles all login-related functionality for Karaoke-Version.com"""
    
    def __init__(self, driver, wait, session_file=".cache/session_data.pkl"):
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
    
    @validation_safe(return_value=False, operation_name="login status check")
    def is_logged_in(self):
        """Check if user is currently logged in"""
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
    
    @selenium_safe(return_value=False, operation_name="logout")
    def logout(self):
        """Logout from the current session"""
        if self._attempt_direct_logout():
            return True
        
        return self._fallback_cookie_logout()
    
    def _attempt_direct_logout(self):
        """Attempt to logout using direct logout links"""
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
                        return self._logout_via_account_menu(element)
                    else:
                        return self._direct_logout_click(element)
            except (Exception, AttributeError, ElementClickInterceptedException) as e:
                logging.debug(f"Logout selector failed: {e}")
                continue
        
        return False
    
    def _logout_via_account_menu(self, account_element):
        """Logout by clicking My Account then logout link"""
        account_element.click()
        
        try:
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Log out')]"))
            )
        except TimeoutException:
            pass
        
        logout_element = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Log out')]")
        logout_element.click()
        
        return self._verify_logout_success()
    
    def _direct_logout_click(self, logout_element):
        """Logout by clicking direct logout link"""
        logout_element.click()
        return self._verify_logout_success()
    
    def _verify_logout_success(self):
        """Verify that logout was successful"""
        try:
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Log in')]"))
            )
        except TimeoutException:
            pass
        
        logging.info("Logout completed")
        return True
    
    def _fallback_cookie_logout(self):
        """Fallback logout method using cookie clearing"""
        logging.info("Direct logout not found, clearing session cookies")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        
        try:
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            pass
        
        return True
    
    def _emergency_cookie_fallback(self):
        """Emergency fallback for logout failures"""
        try:
            self.driver.delete_all_cookies()
            self.driver.refresh()
            
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                pass
            
            return True
        except (Exception, WebDriverException) as e:
            logging.debug(f"Cookie fallback failed: {e}")
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
                        # Wait for login form to appear
                        try:
                            self.wait.until(
                                EC.presence_of_element_located((By.NAME, "frm_login"))
                            )
                        except TimeoutException:
                            pass
                        return True
                except (Exception, NoSuchElementException, ElementNotInteractableException) as e:
                    logging.debug(f"Login selector failed: {e}")
                    continue
            
            logging.warning("No login link found")
            return False
            
        except Exception as e:
            logging.error(f"Error clicking login link: {e}")
            return False
    
    def fill_login_form(self, username, password):
        """Fill and submit the login form"""
        try:
            username_field = self._find_username_field()
            if not username_field:
                return False
            
            password_field = self._find_password_field()
            if not password_field:
                return False
            
            self._fill_credentials(username_field, username, password_field, password)
            
            submit_button = self._find_submit_button()
            if not submit_button:
                return False
            
            return self._submit_form(submit_button)
            
        except Exception as e:
            logging.error(f"Error filling login form: {e}")
            return False
    
    def _find_username_field(self):
        """Find and return the username field element"""
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
            except (TimeoutException, NoSuchElementException, ElementNotInteractableException) as e:
                logging.debug(f"Username selector failed: {e}")
                continue
        
        if not username_field:
            logging.error("Could not find username field")
        
        return username_field
    
    def _find_password_field(self):
        """Find and return the password field element"""
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
            except (NoSuchElementException, ElementNotInteractableException) as e:
                logging.debug(f"Password selector failed: {e}")
                continue
        
        if not password_field:
            logging.error("Could not find password field")
        
        return password_field
    
    def _fill_credentials(self, username_field, username, password_field, password):
        """Fill username and password fields with credentials"""
        logging.info("Filling in credentials...")
        username_field.clear()
        username_field.send_keys(username)
        password_field.clear()
        password_field.send_keys(password)
    
    def _find_submit_button(self):
        """Find and return the submit button element"""
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
            except (NoSuchElementException, ElementNotInteractableException) as e:
                logging.debug(f"Submit selector failed: {e}")
                continue
        
        if not submit_button:
            logging.error("Could not find submit button")
        
        return submit_button
    
    def _submit_form(self, submit_button):
        """Submit the login form and wait for processing"""
        submit_button.click()
        logging.info("Login form submitted")
        
        try:
            self.wait.until(
                lambda driver: "login" not in driver.current_url.lower() or
                               driver.find_elements(By.XPATH, "//*[contains(text(), 'My Account')]") or
                               driver.find_elements(By.XPATH, "//a[contains(text(), 'Log in')]")
            )
        except TimeoutException:
            logging.debug("Login processing timeout, continuing")
        
        return True
    
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
        # Wait for homepage to load
        try:
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            pass
        
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
            session_data = self._load_and_validate_session_data()
            if not session_data:
                return False
            
            self._restore_browser_state(session_data)
            return self._verify_session_restoration()
            
        except Exception as e:
            logging.warning(f"⚠️ Could not load session data: {e}")
            return False
    
    def _load_and_validate_session_data(self):
        """Load session data from file and validate expiry"""
        if not self.session_file.exists():
            logging.debug("No session file found")
            return None
        
        # Load session data
        with open(self.session_file, 'rb') as f:
            session_data = pickle.load(f)
        
        # Check if session is not too old (24 hours max)
        session_age = time.time() - session_data.get('timestamp', 0)
        max_age = SESSION_MAX_AGE_SECONDS  # 24 hours in seconds
        
        if session_age > max_age:
            logging.info(f"🕐 Saved session is {session_age/3600:.1f} hours old, too old to use")
            self.clear_session()
            return None
        
        logging.info(f"🔄 Loading session from {session_age/60:.1f} minutes ago")
        return session_data
    
    def _restore_browser_state(self, session_data):
        """Restore browser cookies, localStorage, and sessionStorage"""
        # Navigate to the saved URL first
        saved_url = session_data.get('url', 'https://www.karaoke-version.com')
        self.driver.get(saved_url)
        # Wait for page to load before restoring session data
        try:
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            pass
        
        self._restore_cookies(session_data.get('cookies', []))
        self._restore_local_storage(session_data.get('localStorage', {}))
        self._restore_session_storage(session_data.get('sessionStorage', {}))
        
        # Refresh page to apply restored session
        self.driver.refresh()
        # Wait for page to reload with restored session
        try:
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            pass
    
    def _restore_cookies(self, cookies):
        """Restore browser cookies with fallback handling"""
        for cookie in cookies:
            try:
                # Keep all cookie attributes, but handle expiry specially
                cookie_copy = cookie.copy()
                
                # Handle expiry - convert to int if present
                if 'expiry' in cookie_copy:
                    try:
                        cookie_copy['expiry'] = int(cookie_copy['expiry'])
                    except (ValueError, TypeError) as e:
                        logging.debug(f"Could not convert expiry to int: {e}")
                        del cookie_copy['expiry']
                
                self.driver.add_cookie(cookie_copy)
                logging.debug(f"Restored cookie: {cookie.get('name', 'unknown')}")
            except Exception as e:
                logging.debug(f"Could not restore cookie {cookie.get('name', 'unknown')}: {e}")
                self._restore_cookie_fallback(cookie)
    
    def _restore_cookie_fallback(self, cookie):
        """Fallback cookie restoration with minimal attributes"""
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
        except Exception as e:
            logging.debug(f"Failed to restore cookie even with minimal attributes: {e}")
    
    def _restore_local_storage(self, local_storage):
        """Restore browser localStorage data"""
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
    
    def _restore_session_storage(self, session_storage):
        """Restore browser sessionStorage data"""
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
    
    def _verify_session_restoration(self):
        """Verify that session restoration was successful"""
        # Try accessing a protected area to trigger session validation
        try:
            # Navigate to account page which should validate session
            self.driver.get("https://www.karaoke-version.com/my/index.html")
            # Wait for account page to load or redirect to login
            try:
                self.wait.until(
                    lambda driver: driver.current_url != "https://www.karaoke-version.com/my/index.html" or
                                   driver.find_elements(By.TAG_NAME, "body")
                )
            except TimeoutException:
                pass
            
            # Check if we were redirected to login page
            current_url = self.driver.current_url
            if "login" in current_url.lower() or "signin" in current_url.lower():
                logging.debug("Redirected to login page, session invalid")
                return False
                
        except Exception as e:
            logging.debug(f"Error accessing account page: {e}")
        
        # Go back to home page and verify login status
        self.driver.get("https://www.karaoke-version.com")
        # Wait for homepage to load for login verification
        try:
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            pass
        
        # Verify the session restoration worked by checking login status
        if self.is_logged_in():
            logging.info("✅ Session data restored and login verified")
            return True
        else:
            logging.warning("⚠️ Session data restored but login verification failed")
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
            max_age = SESSION_MAX_AGE_SECONDS  # 24 hours
            
            return session_age <= max_age
            
        except Exception:
            return False
    
    @profile_timing("login_with_session_persistence", "authentication", "method")
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
            # Wait for homepage to load for Chrome session check
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                pass
            
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
        return self.login(username, password, force_relogin=force_relogin)