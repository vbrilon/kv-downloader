# Shared Test Fixtures Guide

This guide explains how to use the centralized test fixtures defined in `conftest.py` to reduce duplication and standardize test setup across the test suite.

## Overview

The shared fixtures eliminate common duplication patterns identified across 15+ test files, including:
- WebDriver and browser setup (found in 15+ files)
- YAML configuration mocking (found in 8+ files)  
- Track list data (found in 10+ files)
- Temporary file management (found in 6+ files)
- Component manager mocking (found in 8+ files)

## Available Fixtures

### Browser and WebDriver Fixtures

#### `mock_webdriver`
Standard WebDriver mock with common attributes and methods pre-configured.

```python
def test_browser_interaction(mock_webdriver):
    # Use pre-configured driver mock
    assert mock_webdriver.current_url == "https://www.karaoke-version.com/"
    
    # All standard methods are available
    mock_webdriver.get("https://example.com")
    element = mock_webdriver.find_element("id", "test")
    cookies = mock_webdriver.get_cookies()
```

#### `mock_webdriver_wait`
Standard WebDriverWait mock with until/until_not methods.

```python
def test_wait_functionality(mock_webdriver_wait):
    element = mock_webdriver_wait.until(lambda d: d.find_element("id", "test"))
    assert element is not None
```

#### `webdriver_setup`
Combined fixture providing both driver and wait mocks.

```python
def test_combined_setup(webdriver_setup):
    driver = webdriver_setup['driver']
    wait = webdriver_setup['wait']
    
    # Use both components together
    driver.get("https://example.com")
    element = wait.until(lambda d: True)
```

### Configuration and YAML Fixtures

#### `sample_yaml_config`
Standard YAML configuration structure with 3 test songs.

```python
def test_config_parsing(sample_yaml_config):
    assert 'songs' in sample_yaml_config
    assert len(sample_yaml_config['songs']) == 3
    assert sample_yaml_config['songs'][0]['name'] == 'Test_Song_One'
```

#### `yaml_config_string`
YAML configuration as string format for file mocking.

```python
def test_file_reading(yaml_config_string):
    assert 'Test_Song_One' in yaml_config_string
    assert 'url:' in yaml_config_string
```

#### `mock_yaml_file`
Context manager for mocking YAML file operations.

```python
def test_yaml_loading(mock_yaml_file, sample_yaml_config):
    with mock_yaml_file() as mock_yaml_load:
        # Your code that loads YAML files
        # The mock will return sample_yaml_config
        result = yaml.safe_load("fake_file.yaml")
        assert result == sample_yaml_config
```

### Track Data Fixtures

#### `sample_track_list`
Complete track list with 11 tracks (matches real Karaoke Version structure).

```python
def test_track_processing(sample_track_list):
    assert len(sample_track_list) == 11
    assert sample_track_list[0]['name'] == 'Intro count Click'
    assert sample_track_list[4]['name'] == 'Lead Electric Guitar'
```

#### `minimal_track_list`
Simplified track list with 3 tracks for basic testing.

```python
def test_simple_track_logic(minimal_track_list):
    assert len(minimal_track_list) == 3
    # Perfect for tests that don't need full complexity
    for track in minimal_track_list:
        assert 'name' in track
        assert 'index' in track
```

### File Management Fixtures

#### `temp_file`
Managed temporary file that's automatically cleaned up.

```python
def test_file_operations(temp_file):
    # Use temp_file path directly
    Path(temp_file).write_text("test content")
    content = Path(temp_file).read_text()
    assert content == "test content"
    # File is automatically cleaned up after test
```

#### `temp_directory`
Managed temporary directory for complex file testing.

```python
def test_directory_operations(temp_directory):
    # Create files in temporary directory
    test_file = temp_directory / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()
    # Directory and contents automatically cleaned up
```

### Session Data Fixtures

#### `sample_session_data`
Realistic session data structure for testing persistence.

```python
def test_session_handling(sample_session_data):
    assert 'cookies' in sample_session_data
    assert len(sample_session_data['cookies']) == 2
    assert 'localStorage' in sample_session_data
```

#### `expired_session_data`
Session data with timestamp >24 hours old for expiry testing.

```python
def test_session_expiry(expired_session_data):
    import time
    age_hours = (time.time() - expired_session_data['timestamp']) / 3600
    assert age_hours > 24  # Should be expired
```

### Component Manager Fixtures

#### `mock_chrome_manager`
Pre-configured ChromeManager mock with standard methods.

```python
def test_chrome_management(mock_chrome_manager):
    assert mock_chrome_manager.headless is True
    assert mock_chrome_manager.download_path == "/tmp/downloads"
    
    # All standard methods are mocked
    options = mock_chrome_manager.setup_chrome_options()
    assert options is not None
```

#### `mock_login_manager`
Pre-configured LoginManager mock with authentication methods.

```python
def test_authentication(mock_login_manager):
    result = mock_login_manager.login("user", "pass")
    assert result is True
    
    assert mock_login_manager.is_logged_in() is True
```

### Composite Fixtures

#### `full_test_setup`
Comprehensive setup including all major components.

```python
def test_integration_scenario(full_test_setup):
    driver = full_test_setup['driver']
    config = full_test_setup['config']
    tracks = full_test_setup['tracks']
    temp_dir = full_test_setup['temp_dir']
    
    # Everything you need for complex integration tests
    assert driver.current_url is not None
    assert 'songs' in config
    assert len(tracks) == 11
    assert temp_dir.exists()
```

#### `minimal_test_setup`
Basic setup for simple unit tests.

```python
def test_simple_scenario(minimal_test_setup):
    driver = minimal_test_setup['driver']
    tracks = minimal_test_setup['tracks']
    
    # Just the essentials for unit testing
    assert len(tracks) == 3
```

## Migration Patterns

### From Duplicate Setup Code

**Before (Duplicated across files):**
```python
def setUp(self):
    self.mock_driver = Mock()
    self.mock_driver.current_url = "https://example.com"
    self.mock_driver.get_cookies.return_value = []
    # ... 20+ lines of similar setup
```

**After (Using fixtures):**
```python
def test_something(self, mock_webdriver):
    # Driver is pre-configured and ready to use
    assert mock_webdriver.current_url is not None
```

### From Manual Track Data

**Before:**
```python
def setUp(self):
    self.sample_tracks = [
        {'name': 'Electronic Drum Kit', 'index': 1},
        {'name': 'Lead Electric Guitar', 'index': 4},
        # ... repeated in multiple files
    ]
```

**After:**
```python
def test_tracks(self, minimal_track_list):
    # Standardized track data ready to use
    assert len(minimal_track_list) == 3
```

### From Manual YAML Setup

**Before:**
```python
def test_config(self):
    yaml_content = {
        'songs': [
            {'url': 'https://...', 'name': 'Test_Song'}
            # ... repeated setup
        ]
    }
    with patch('yaml.safe_load', return_value=yaml_content):
        # test code
```

**After:**
```python
def test_config(self, mock_yaml_file, sample_yaml_config):
    with mock_yaml_file():
        # YAML operations automatically return sample_yaml_config
        pass
```

## Testing the Fixtures

Run the demo test to verify fixtures work correctly:

```bash
# Run the demo test file
python -m pytest tests/unit/test_shared_fixtures_demo.py -v

# Run specific fixture tests
python -m pytest tests/unit/test_shared_fixtures_demo.py::TestSharedFixturesDemo::test_webdriver_fixture_usage -v
```

## Best Practices

### 1. Choose the Right Fixture Level
- Use `minimal_track_list` for simple unit tests
- Use `sample_track_list` for comprehensive testing
- Use `full_test_setup` for integration tests

### 2. Combine Fixtures as Needed
```python
def test_complex_scenario(self, mock_webdriver, sample_yaml_config, temp_directory):
    # Combine multiple fixtures for specific test needs
    pass
```

### 3. Extend Fixtures When Needed
```python
def test_with_custom_data(self, sample_track_list):
    # Modify fixture data for specific test requirements
    custom_tracks = sample_track_list.copy()
    custom_tracks[0]['custom_field'] = 'test_value'
    # Use custom_tracks in test
```

### 4. Use Parametrize with Fixtures
```python
@pytest.mark.parametrize("track_index", [0, 1, 2])
def test_each_track(self, minimal_track_list, track_index):
    track = minimal_track_list[track_index]
    assert 'name' in track
```

## Benefits

### Reduced Duplication
- **15+ files** with duplicate WebDriver setup → **1 shared fixture**
- **8+ files** with duplicate YAML setup → **3 YAML fixtures**
- **10+ files** with duplicate track data → **2 track fixtures**

### Improved Consistency
- Standardized test data across all files
- Consistent mock behavior and expectations
- Reduced test maintenance burden

### Better Test Reliability
- Centralized fixture maintenance
- Consistent test environment setup
- Reduced setup-related test failures

### Easier Test Writing
- Less boilerplate code in each test
- Focus on test logic rather than setup
- Clear, documented fixture interface

## Future Expansion

The fixture system can be easily extended with new fixtures for:
- Additional component manager types
- Specialized test data sets
- More complex integration scenarios
- Performance testing setups

Add new fixtures to `conftest.py` following the established patterns and documentation conventions.