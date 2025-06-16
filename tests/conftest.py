"""
Shared test fixtures for the Karaoke Version automation project.

This module provides centralized fixtures to reduce duplication across
test files and standardize common test setup patterns.
"""

import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import yaml
import time

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# Browser and WebDriver Fixtures
# =============================================================================

@pytest.fixture
def mock_webdriver():
    """
    Standard WebDriver mock with common attributes and methods.
    
    Provides a fully configured Mock driver that includes all the standard
    attributes and methods used across the test suite.
    """
    driver = Mock()
    
    # Basic attributes
    driver.current_url = "https://www.karaoke-version.com/"
    driver.window_handles = ["handle1", "handle2"]
    driver.current_window_handle = "handle1"
    driver.page_source = "<html><body>Test Page</body></html>"
    driver.title = "Test Page"
    
    # Cookie methods
    driver.get_cookies.return_value = [
        {"name": "session_id", "value": "abc123", "domain": ".karaoke-version.com"},
        {"name": "auth_token", "value": "xyz789", "domain": ".karaoke-version.com"}
    ]
    driver.add_cookie.return_value = None
    driver.delete_all_cookies.return_value = None
    
    # Navigation methods
    driver.get.return_value = None
    driver.back.return_value = None
    driver.forward.return_value = None
    driver.refresh.return_value = None
    
    # Element finding (returns mock elements)
    mock_element = Mock()
    mock_element.text = "Mock Element"
    mock_element.is_displayed.return_value = True
    mock_element.click.return_value = None
    mock_element.send_keys.return_value = None
    mock_element.get_attribute.return_value = "mock_value"
    
    driver.find_element.return_value = mock_element
    driver.find_elements.return_value = [mock_element, mock_element]
    
    # JavaScript execution
    driver.execute_script.return_value = {"localStorage": {}, "sessionStorage": {}}
    
    # Window management
    driver.switch_to.window.return_value = None
    driver.close.return_value = None
    driver.quit.return_value = None
    
    return driver


@pytest.fixture
def mock_webdriver_wait():
    """
    Standard WebDriverWait mock with common methods.
    
    Provides a configured Mock wait object that includes the until method
    and other common wait functionality.
    """
    wait = Mock()
    
    # Mock element for wait.until() return
    mock_element = Mock()
    mock_element.text = "Waited Element"
    mock_element.click.return_value = None
    
    wait.until.return_value = mock_element
    wait.until_not.return_value = True
    
    return wait


@pytest.fixture
def webdriver_setup(mock_webdriver, mock_webdriver_wait):
    """
    Combined WebDriver and Wait fixture setup.
    
    Returns a dictionary with both driver and wait mocks, ready for use
    in tests that need both components.
    """
    return {
        'driver': mock_webdriver,
        'wait': mock_webdriver_wait
    }


# =============================================================================
# Configuration and YAML Fixtures
# =============================================================================

@pytest.fixture
def sample_yaml_config():
    """
    Standard YAML configuration content for testing.
    
    Provides a realistic songs.yaml structure that can be used across
    multiple test files without duplication.
    """
    return {
        'songs': [
            {
                'url': 'https://www.karaoke-version.com/custombackingtrack/artist/song1.html',
                'name': 'Test_Song_One',
                'description': 'First test song',
                'key': 2
            },
            {
                'url': 'https://www.karaoke-version.com/custombackingtrack/artist/song2.html',
                'name': 'Test_Song_Two',
                'description': 'Second test song',
                'key': -1
            },
            {
                'url': 'https://www.karaoke-version.com/custombackingtrack/artist/song3.html',
                'description': 'Song without explicit name (should auto-extract)'
            }
        ]
    }


@pytest.fixture
def yaml_config_string(sample_yaml_config):
    """
    YAML configuration as string format.
    
    Converts the sample YAML config to string format for tests that
    need to mock file reading operations.
    """
    return yaml.dump(sample_yaml_config, default_flow_style=False)


@pytest.fixture
def mock_yaml_file(yaml_config_string):
    """
    Mock YAML file reading operations.
    
    Provides a context manager that mocks file operations for YAML
    configuration reading, returning the standard test configuration.
    """
    @patch('builtins.open', mock_open(read_data=yaml_config_string))
    @patch('yaml.safe_load')
    def _mock_yaml_operations(mock_yaml_load):
        mock_yaml_load.return_value = yaml.safe_load(yaml_config_string)
        return mock_yaml_load
    
    return _mock_yaml_operations


# =============================================================================
# Track Data Fixtures
# =============================================================================

@pytest.fixture
def sample_track_list():
    """
    Standard track list for testing track management functionality.
    
    Provides a realistic track structure that matches what would be
    discovered from a real Karaoke Version song page.
    """
    return [
        {'name': 'Intro count Click', 'index': 0},
        {'name': 'Electronic Drum Kit', 'index': 1},
        {'name': 'Percussion', 'index': 2},
        {'name': 'Synth Bass', 'index': 3},
        {'name': 'Lead Electric Guitar', 'index': 4},
        {'name': 'Piano', 'index': 5},
        {'name': 'Synth Pad', 'index': 6},
        {'name': 'Synth Keys 1', 'index': 7},
        {'name': 'Synth Keys 2', 'index': 8},
        {'name': 'Backing Vocals', 'index': 9},
        {'name': 'Lead Vocal', 'index': 10}
    ]


@pytest.fixture
def minimal_track_list():
    """
    Minimal track list for simple testing scenarios.
    
    Provides a smaller track list for tests that don't need the full
    complexity but still need realistic track data.
    """
    return [
        {'name': 'Electronic Drum Kit', 'index': 1},
        {'name': 'Lead Electric Guitar', 'index': 4},
        {'name': 'Lead Vocal', 'index': 10}
    ]


# =============================================================================
# File and Path Management Fixtures
# =============================================================================

@pytest.fixture
def temp_file():
    """
    Managed temporary file fixture.
    
    Creates a temporary file for testing and ensures it's cleaned up
    after the test completes, even if the test fails.
    """
    temp_fd, temp_path = tempfile.mkstemp()
    try:
        yield temp_path
    finally:
        try:
            Path(temp_path).unlink()
        except FileNotFoundError:
            pass  # File was already deleted


@pytest.fixture
def temp_directory():
    """
    Managed temporary directory fixture.
    
    Creates a temporary directory for testing and ensures it's cleaned up
    after the test completes.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def project_path():
    """
    Project root path fixture.
    
    Provides the project root path for tests that need to work with
    project-relative paths or imports.
    """
    return Path(__file__).parent.parent


# =============================================================================
# Session Data Fixtures
# =============================================================================

@pytest.fixture
def sample_session_data():
    """
    Standard session data structure for testing session persistence.
    
    Provides a realistic session data structure that matches what would
    be saved during actual login operations.
    """
    return {
        'cookies': [
            {
                'name': 'session_id',
                'value': 'abc123def456',
                'domain': '.karaoke-version.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            },
            {
                'name': 'auth_token',
                'value': 'xyz789uvw012',
                'domain': '.karaoke-version.com',
                'path': '/',
                'secure': True,
                'httpOnly': False
            }
        ],
        'localStorage': {
            'user_preferences': '{"theme": "dark", "volume": 0.8}',
            'last_visited': 'https://www.karaoke-version.com/account'
        },
        'sessionStorage': {
            'current_session': 'active',
            'csrf_token': 'token123'
        },
        'url': 'https://www.karaoke-version.com/account',
        'timestamp': time.time() - 3600,  # 1 hour ago
        'user_agent': 'Mozilla/5.0 (Test Browser)',
        'window_size': {'width': 1920, 'height': 1080}
    }


@pytest.fixture
def expired_session_data(sample_session_data):
    """
    Expired session data for testing session expiry logic.
    
    Takes the standard session data and modifies the timestamp to
    simulate an expired session (older than 24 hours).
    """
    expired_data = sample_session_data.copy()
    expired_data['timestamp'] = time.time() - (25 * 3600)  # 25 hours ago
    return expired_data


# =============================================================================
# Component Manager Fixtures
# =============================================================================

@pytest.fixture
def mock_chrome_manager():
    """
    Mock ChromeManager for testing browser management functionality.
    
    Provides a fully configured ChromeManager mock that includes all
    the standard methods and attributes used in tests.
    """
    chrome_manager = Mock()
    
    # Setup methods
    chrome_manager.setup_chrome_options.return_value = Mock()
    chrome_manager.setup_chrome_service.return_value = Mock()
    chrome_manager.setup_chrome_driver.return_value = Mock()
    
    # Path and configuration
    chrome_manager.download_path = "/tmp/downloads"
    chrome_manager.user_data_dir = "/tmp/chrome_test"
    chrome_manager.headless = True
    
    # Driver access
    chrome_manager.driver = None  # Will be set by tests as needed
    
    return chrome_manager


@pytest.fixture
def mock_login_manager(mock_webdriver, mock_webdriver_wait):
    """
    Mock LoginManager for testing authentication functionality.
    
    Provides a configured LoginManager mock with standard methods
    and return values for testing login workflows.
    """
    login_manager = Mock()
    
    # Driver references
    login_manager.driver = mock_webdriver
    login_manager.wait = mock_webdriver_wait
    
    # Authentication methods
    login_manager.login.return_value = True
    login_manager.is_logged_in.return_value = True
    login_manager.logout.return_value = True
    
    # Session persistence
    login_manager.save_session.return_value = True
    login_manager.load_session.return_value = True
    
    return login_manager


# =============================================================================
# Time and Timing Fixtures
# =============================================================================

@pytest.fixture
def mock_time():
    """
    Mock time functions for consistent test timing.
    
    Provides patched time functions that return predictable values,
    useful for testing time-dependent functionality.
    """
    with patch('time.time') as mock_time_func:
        with patch('time.sleep') as mock_sleep_func:
            # Set consistent time
            mock_time_func.return_value = 1640995200.0  # 2022-01-01 00:00:00 UTC
            mock_sleep_func.return_value = None
            
            yield {
                'time': mock_time_func,
                'sleep': mock_sleep_func
            }


# =============================================================================
# Composite Fixtures for Common Scenarios
# =============================================================================

@pytest.fixture
def full_test_setup(webdriver_setup, sample_yaml_config, sample_track_list, temp_directory):
    """
    Complete test setup for integration-style tests.
    
    Combines multiple fixtures into a single comprehensive setup that
    includes browser mocks, configuration, track data, and file management.
    """
    return {
        'driver': webdriver_setup['driver'],
        'wait': webdriver_setup['wait'],
        'config': sample_yaml_config,
        'tracks': sample_track_list,
        'temp_dir': temp_directory
    }


@pytest.fixture
def minimal_test_setup(mock_webdriver, minimal_track_list):
    """
    Minimal test setup for simple unit tests.
    
    Provides basic mocks and data for tests that don't need the full
    complexity of the complete test setup.
    """
    return {
        'driver': mock_webdriver,
        'tracks': minimal_track_list
    }