# Development Tools

This directory contains development and debugging tools that are separate from the main test suite.

## Inspection Tools (`/inspection/`)

These are standalone scripts for inspecting and debugging the Karaoke-Version.com website:

- `inspect_download_button.py` - Examines download button elements and attributes
- `inspect_key_controls.py` - Tests key adjustment mixer controls
- `inspect_login_form.py` - Inspects login form fields and selectors
- `inspect_mixer_after_login.py` - Checks mixer state after successful login
- `inspect_mixer_controls.py` - Tests mixer control functionality
- `inspect_solo_buttons.py` - Examines solo button elements and behavior
- `simple_page_test.py` - Basic page loading test
- `test_page_inspection.py` - General page element inspection
- `verify_login_status.py` - Checks login session status

## Usage

These tools are designed to be run individually for debugging and development purposes. They are not part of the automated test suite.

```bash
# Example usage
python tools/inspection/inspect_login_form.py
python tools/inspection/verify_login_status.py
```

## Note

These tools may require manual configuration (URLs, credentials, etc.) and are intended for development use only.