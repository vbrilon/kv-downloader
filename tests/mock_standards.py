"""
Mock Usage Standards for Karaoke Automation Tests

This module defines standardized patterns for mock usage across all test files
to ensure consistency and maintainability.

STANDARDS:
1. Use Mock() for simple object mocking
2. Use MagicMock() only when magic methods (__len__, __getitem__, etc.) are needed
3. Use @patch decorator for function/method patching
4. Use patch() as context manager for temporary patching
5. Consistent import order and naming
6. Clear mock setup patterns

"""

from unittest.mock import Mock, patch, MagicMock, mock_open, call


# Standard Mock Setup Patterns
class MockPatterns:
    """Standard mock setup patterns for common scenarios"""
    
    @staticmethod
    def create_driver_mock():
        """Create a standard WebDriver mock with common attributes"""
        mock_driver = Mock()
        mock_driver.current_url = "https://example.com"
        mock_driver.window_handles = ["handle1"]
        mock_driver.current_window_handle = "handle1"
        mock_driver.get_cookies.return_value = []
        mock_driver.execute_script.return_value = {}
        mock_driver.find_elements.return_value = []
        mock_driver.find_element.return_value = Mock()
        return mock_driver
    
    @staticmethod
    def create_wait_mock():
        """Create a standard WebDriverWait mock"""
        mock_wait = Mock()
        mock_wait.until.return_value = Mock()
        return mock_wait
    
    @staticmethod
    def create_file_mock(content=""):
        """Create a standard file mock with content"""
        return mock_open(read_data=content)
    
    @staticmethod
    def create_config_mock():
        """Create a standard configuration mock"""
        mock_config = Mock()
        mock_config.songs = []
        mock_config.download_folder = "/tmp/downloads"
        return mock_config


# Standard Import Pattern
"""
Recommended import pattern for all test files:

from unittest.mock import Mock, patch, call
from tests.mock_standards import MockPatterns

# Use MagicMock and mock_open only when specifically needed:
# from unittest.mock import MagicMock, mock_open
"""


# Mock Usage Guidelines
"""
WHEN TO USE EACH MOCK TYPE:

1. Mock() - Default choice for most scenarios
   - Mocking classes, objects, methods
   - When you only need basic attribute/method mocking
   
2. MagicMock() - Only when magic methods are needed
   - When mocking objects that use __len__, __getitem__, __iter__, etc.
   - When mocking containers or objects with operator overloading
   
3. @patch decorator - For patching functions/methods at class/method level
   - Patching imports, built-in functions
   - When patch applies to entire test method
   
4. patch() context manager - For temporary patching within test
   - When patch only applies to specific section of test
   - For multiple patches in sequence

EXAMPLES:

# Good - Mock for simple object
mock_driver = Mock()
mock_driver.find_element.return_value = Mock()

# Good - MagicMock when container behavior needed
mock_collection = MagicMock()
len(mock_collection)  # Works with MagicMock

# Good - @patch decorator for method-level patching
@patch('time.sleep')
def test_something(self, mock_sleep):
    # test code

# Good - Context manager for temporary patching
def test_something(self):
    with patch('builtins.open', mock_open()) as mock_file:
        # test code

"""


# Naming Conventions
"""
MOCK NAMING STANDARDS:

1. Prefix all mocks with 'mock_'
2. Use descriptive names based on what's being mocked
3. Use consistent naming across similar tests

Examples:
- mock_driver (WebDriver instance)
- mock_wait (WebDriverWait instance)  
- mock_file (file object)
- mock_config (configuration object)
- mock_response (HTTP response)
- mock_element (WebElement)

Avoid:
- m, m1, m2 (non-descriptive)
- mock_obj (too generic)
- driver_mock (wrong prefix order)
"""


# Setup Patterns
"""
STANDARD SETUP PATTERNS:

1. Use setUp() method for common mocks across test methods
2. Create specific mocks in individual test methods when needed
3. Use MockPatterns class for standardized mock creation
4. Set up mock return values immediately after creation

Example:
class TestSomething(unittest.TestCase):
    def setUp(self):
        self.mock_driver = MockPatterns.create_driver_mock()
        self.mock_wait = MockPatterns.create_wait_mock()
    
    def test_something(self):
        # Specific mock setup for this test
        self.mock_driver.find_element.return_value = Mock()
        # test code
"""