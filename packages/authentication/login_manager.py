"""Login management for Karaoke-Version.com authentication"""

import time
import logging
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
    
    def __init__(self, driver, wait):
        """
        Initialize login manager
        
        Args:
            driver: Selenium WebDriver instance
            wait: WebDriverWait instance
        """
        self.driver = driver
        self.wait = wait
    
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
            return True
        else:
            logging.error("❌ Login failed - verification unsuccessful")
            return False