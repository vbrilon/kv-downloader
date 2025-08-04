# Karaoke-Version.com Track Automation

## IMPORTANT: Virtual Environment Requirement
**ALWAYS activate the virtual environment before any Python operations:**
```bash
source bin/activate  # On macOS/Linux
```

## Overview
Automated system for downloading isolated backing tracks from Karaoke-Version.com using Python and Selenium. Downloads all available tracks for specified songs into organized directories.

## Usage Instructions

1. **Setup Environment**:
   ```bash
   source bin/activate  # Activate virtual environment
   pip install -r requirements.txt  # Install dependencies
   ```

2. **Configure Credentials**: Update `.env` file:
   ```
   KV_USERNAME=your_username_here
   KV_PASSWORD=your_password_here
   ```

3. **Configure Songs**: Edit `songs.yaml` with your desired songs

4. **Run Tests**:
   ```bash
   # Run organized test suite
   python tests/run_tests.py
   
   # Run specific test categories
   python tests/run_tests.py --unit-only
   python tests/run_tests.py --integration-only
   python tests/run_tests.py --regression-only
   ```

5. **Run Automation**:
   ```bash
   # Production mode (headless, organized logging)
   python karaoke_automator.py

   # Debug mode (visible browser, detailed file logging)
   python karaoke_automator.py --debug
   ```

## Songs Configuration (songs.yaml)
```yaml
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song.html"
    name: "Song_Directory_Name"  # Optional: auto-extracts from URL if omitted
    description: "Optional description"
    key: -1  # Optional: Pitch adjustment in semitones (-12 to +12)
    # Supports multiple formats: 2, "+3", "-2", "5"
```

## Project Status: PRODUCTION READY ✅

### Core Features Complete
- ✅ **Authentication & Session Management** - 24-hour session persistence with smart validation
- ✅ **Track Discovery & Isolation** - Automatic track detection and solo button functionality  
- ✅ **Mixer Controls** - Intro count and key adjustment automation
- ✅ **Download System** - Complete workflow with progress tracking and file organization
- ✅ **Final Cleanup Pass** - Post-download cleanup system to ensure all files are properly renamed
- ✅ **Modular Architecture** - Clean package-based design with no code duplication
- ✅ **Statistics & Reporting** - Comprehensive session tracking and final reports
- ✅ **Error Handling** - Robust error recovery with specific exception types
- ✅ **Test Suite** - Comprehensive testing with 100% regression pass rate

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

## Technical Implementation Details

### Key Site Selectors (Verified Working)
- **Login**: `name="frm_login"`, `name="frm_password"`, `name="sbm"`
- **Tracks**: `.track[data-index]`, `.track__caption`, `button.track__solo`
- **Download**: `a.download`, JavaScript fallback for interception
- **Mixer**: `#precount`, `button.btn--pitch.pitch__button`, `.pitch__caption`

### Track Discovery
- Up to 15 tracks per song (data-index 0-14)
- Common tracks: Intro count Click, Drum Kit, Bass, Guitar, Piano, Vocals
- Solo buttons provide mutually exclusive track isolation

## Current Capabilities
1. ✅ **Authentication with Session Persistence** - 24-hour login caching
2. ✅ **Track Discovery & Isolation** - Automatic detection and solo functionality
3. ✅ **Mixer Controls** - Intro count checkbox and key adjustment (-12 to +12 semitones)
4. ✅ **Download Process** - Complete workflow with progress tracking
5. ✅ **File Organization** - Clean naming and song-specific folders
6. ✅ **Error Handling** - Comprehensive exception management

### Key Features
- **Session Management**: Saves login state, 85% faster subsequent runs
- **Track Isolation**: Solo buttons for individual instrument downloads
- **Key Adjustment**: Support for pitch changes via songs.yaml configuration
- **Progress Tracking**: Real-time UI with completion statistics
- **Final Cleanup**: Post-download file renaming system

## Session Management

### Commands
```bash
# Normal usage (uses saved session if available)
python karaoke_automator.py

# Force fresh login (bypass saved session)
python karaoke_automator.py --force-login

# Clear saved session data and exit
python karaoke_automator.py --clear-session
```

### Performance Benefits
- **First login**: ~4-14 seconds
- **Subsequent logins**: ~2-3 seconds (85% faster)
- **Session Storage**: `.cache/session_data.pkl` with 24-hour expiry
- **Automatic fallback**: Handles expired sessions gracefully

## Key Technical Patterns

### Performance Optimization
- **Smart WebDriverWait**: Responsive waits instead of fixed delays
- **Session Persistence**: Chrome profile reuse and cached authentication
- **Threading**: Non-daemon threads for download monitoring

### Error Handling
```python
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    WebDriverException,
    TimeoutException
)
```

### Final Cleanup System
- Post-download cleanup pass ensures 100% file renaming
- Pattern matching for uncleaned files
- Handles timing conflicts during sequential downloads

## Usage Examples

### Basic Usage
```bash
# Always activate virtual environment first
source bin/activate

# Run the automation (uses saved session if available)
python karaoke_automator.py
```

### Debug Mode
```bash
# Run with visible browser and detailed logging
python karaoke_automator.py --debug

# View detailed debug logs
tail -f logs/debug.log
```

### Test Execution
```bash
# Run all tests
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py --unit-only
python tests/run_tests.py --integration-only
python tests/run_tests.py --regression-only
```

## Quick Start for New Sessions
**Verify Current State**:
```bash
source bin/activate
python tests/run_tests.py --regression-only  # Should show 100% pass
python -c "from karaoke_automator import KaraokeVersionAutomator; print('✅ Ready')"
```

**Run Automation**:
```bash
# Edit songs.yaml with your desired songs (check indentation: exactly 2 spaces!)
python karaoke_automator.py              # Production mode
python karaoke_automator.py --debug      # Debug mode with visible browser
```


---

## important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context or otherwise consider it in your response unless it is highly relevant to your task. Most of the time, it is not relevant.
