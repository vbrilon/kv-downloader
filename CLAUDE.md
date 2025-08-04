# Karaoke-Version.com Track Automation

## IMPORTANT: Virtual Environment Requirement
**ALWAYS activate the virtual environment before any Python operations:**
```bash
source bin/activate  # On macOS/Linux
```

## Overview
Automated system for downloading isolated backing tracks from Karaoke-Version.com using Python and Selenium. Downloads all available tracks for specified songs into organized directories.

## Quick Start
```bash
source bin/activate
python karaoke_automator.py              # Production mode
python karaoke_automator.py --debug      # Debug mode with visible browser
```

## Songs Configuration (songs.yaml)
```yaml
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song.html"
    name: "Song_Directory_Name"  # Optional: auto-extracts from URL if omitted
    description: "Optional description"
    key: -1  # Optional: Pitch adjustment in semitones (-12 to +12)
```

## Project Status: PRODUCTION READY ✅

## Architecture

### Package Structure
```
packages/
├── authentication/     # Login management and session handling
├── browser/           # Chrome setup and download path management
├── configuration/     # YAML config parsing and validation
├── download_management/  # Download orchestration and monitoring
├── file_operations/   # File management and cleanup
├── progress/         # Progress tracking and statistics reporting
├── track_management/ # Track discovery, isolation, mixer controls
├── validation/       # Unified validation logic for track selection and audio state
└── utils/           # Logging setup and cross-cutting utilities
```

### Key Site Selectors (Verified Working)
- **Login**: `name="frm_login"`, `name="frm_password"`, `name="sbm"`
- **Tracks**: `.track[data-index]`, `.track__caption`, `button.track__solo`
- **Download**: `a.download`, JavaScript fallback for interception
- **Mixer**: `#precount`, `button.btn--pitch.pitch__button`, `.pitch__caption`

### Track Management System
- **Track Discovery**: Up to 15 tracks per song (data-index 0-14)
- **Solo Isolation**: Mutually exclusive track isolation with 4-phase validation:
  1. Solo button activation with retry logic
  2. Audio server processing indicator monitoring
  3. Multi-layer validation (mixer state + server response + track fingerprinting)
  4. Persistent state verification before download

### Validation System (packages/validation/)
- **TrackValidator**: Unified validation supporting both strict (100%) and audio_mix (67%) modes
- **AudioValidator**: JavaScript-based audio state validation with mixer analysis
- **ValidationConfig**: Configurable validation behavior with predefined configs
- **Solo Button Validation**: Consolidated logic for button state checking and exclusivity
- **Track Element Validation**: Unified track discovery and name matching logic

### Download Management System
- **Modular Download Flow**: `download_current_mix()` orchestrates 4 focused methods:
  - `_navigate_and_find_download_button()`: Page navigation and button finding
  - `_validate_pre_download_requirements()`: Pre-download validation with retry
  - `_execute_download_action()`: Download execution and progress tracking
  - `_monitor_download_completion()`: Download monitoring and completion handling
- **Error Handling**: Specific error types (SONG_NOT_PURCHASED, DOWNLOAD_BUTTON_NOT_FOUND)
- **Progress Tracking**: Real-time status updates and background monitoring

### Session Management
- **Chrome Profile Reuse**: Persistent authentication via `chrome_profile/`
- **Session Storage**: `.cache/session_data.pkl` with 24-hour expiry
- **Performance**: 85% faster subsequent runs (2-3s vs 4-14s)

### Commands
```bash
python karaoke_automator.py                 # Normal usage
python karaoke_automator.py --force-login   # Force fresh login
python karaoke_automator.py --clear-session # Clear session data
python karaoke_automator.py --debug         # Debug mode
```

### Testing
```bash
python tests/run_tests.py                   # All tests
python tests/run_tests.py --regression-only # Regression tests
```


