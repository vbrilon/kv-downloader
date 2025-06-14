# Test Directory

This directory contains all test files for the Karaoke-Version.com automation project.

## Unit Tests (for CI/CD)
- **test_config.py** - Tests configuration loading and YAML parsing
- **test_main.py** - Tests automation class methods and functionality

Run with: `python -m pytest tests/test_*.py -v`

## Site Inspection Tools (for development)
- **test_login.py** - Verify login functionality and status detection
- **test_page_inspection.py** - Comprehensive page inspection with login
- **simple_page_test.py** - Basic page structure analysis without login
- **extract_tracks.py** - Extract track names from song pages
- **complete_track_extraction.py** - Complete track discovery (found all 11 tracks)
- **test_full_login_cycle.py** - Test complete logout → login cycle

## Usage
```bash
# Run unit tests
python -m pytest tests/test_*.py -v

# Run specific inspection tool
python tests/test_login.py
python tests/extract_tracks.py
```