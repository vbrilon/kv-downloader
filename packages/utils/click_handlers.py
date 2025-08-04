"""
Common click handling utilities with JavaScript fallback for Selenium WebDriver.

This module provides standardized click handling patterns to reduce code duplication
across the track management and download management modules.
"""

import logging
from selenium.webdriver.remote.webelement import WebElement
from ..configuration.config import CLICK_HANDLER_DELAY
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import ElementClickInterceptedException


def safe_click(driver: WebDriver, element: WebElement, element_description: str = "element") -> bool:
    """
    Safely click an element with JavaScript fallback if regular click is intercepted.
    
    Args:
        driver: Selenium WebDriver instance
        element: WebElement to click
        element_description: Description of element for logging (e.g., "download button", "solo button")
    
    Returns:
        bool: True if click succeeded, False otherwise
        
    Raises:
        Exception: Re-raises non-click-interception exceptions
    """
    try:
        # Try regular click first
        element.click()
        logging.debug(f"✅ {element_description} clicked successfully")
        return True
        
    except Exception as e:
        if "element click intercepted" in str(e):
            # Use JavaScript click as fallback
            logging.info(f"Click intercepted on {element_description}, using JavaScript click")
            try:
                driver.execute_script("arguments[0].click();", element)
                logging.debug(f"✅ {element_description} clicked via JavaScript")
                return True
            except Exception as js_error:
                logging.error(f"JavaScript click also failed on {element_description}: {js_error}")
                return False
        else:
            # Re-raise non-interception exceptions
            raise e


def safe_click_with_scroll(driver: WebDriver, element: WebElement, element_description: str = "element") -> bool:
    """
    Safely click an element with scroll-into-view and JavaScript fallback.
    
    This is useful for elements that might be outside the viewport or have 
    overlapping elements that could cause click interception.
    
    Args:
        driver: Selenium WebDriver instance
        element: WebElement to click
        element_description: Description of element for logging
    
    Returns:
        bool: True if click succeeded, False otherwise
        
    Raises:
        Exception: Re-raises non-click-interception exceptions
    """
    try:
        # Scroll element into view first
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        logging.debug(f"Scrolled {element_description} into view")
        
        # Small delay to allow scrolling to complete
        import time
        time.sleep(CLICK_HANDLER_DELAY)
        
        # Use safe_click for the actual clicking logic
        return safe_click(driver, element, element_description)
        
    except Exception as e:
        logging.error(f"Failed to scroll and click {element_description}: {e}")
        raise e