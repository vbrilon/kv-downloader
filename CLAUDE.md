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
- **Validation Score**: Requires 2/3 validation checks to pass (67% threshold)

### Critical Bug Fix (2025-08-04)
**Fixed**: `NameError: name 'track_index' is not defined` in `packages/track_management/track_manager.py`
- **Root Cause**: Parameter not passed through method call chain (`_activate_solo_button`)
- **Solution**: Updated method signature to accept and pass `track_index` parameter
- **Impact**: Resolved 100% track isolation failures

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


