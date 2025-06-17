# Karaoke-Version.com Track Automation

## IMPORTANT: Virtual Environment Requirement
**ALWAYS activate the virtual environment before any Python operations:**
```bash
source bin/activate  # On macOS/Linux
```

## Overview
Automated system for downloading isolated backing tracks from Karaoke-Version.com using Python and Selenium. Downloads all available tracks for specified songs into organized directories.

## Karaoke-Version.com Site Structure (DISCOVERED)

### CSS Selectors (VERIFIED)
- **Track Container**: `.track` elements with `data-index` attributes (0-14)
- **Track Names**: `.track__caption` contains the instrument/track name
- **Track Count**: Up to 15 tracks per song

### Complete Track List Example
1. **Intro count Click** (data-index=0) - Metronome/click track
2. **Electronic Drum Kit** (data-index=1)
3. **Percussion** (data-index=2)
4. **Synth Bass** (data-index=3)
5. **Lead Electric Guitar** (data-index=4)
6. **Piano** (data-index=5)
7. **Synth Pad** (data-index=6)
8. **Synth Keys 1** (data-index=7)
9. **Synth Keys 2** (data-index=8)
10. **Backing Vocals** (data-index=9)
11. **Lead Vocal** (data-index=10) - Usually muted by default (0% volume)

### Technical Implementation
```python
# Track discovery code
track_elements = driver.find_elements(By.CSS_SELECTOR, ".track")
for track in track_elements:
    track_name = track.find_element(By.CSS_SELECTOR, ".track__caption").text
    data_index = track.get_attribute('data-index')
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

## Project Status: PRODUCTION READY ✅

### ✅ All Core Features Fully Implemented & Tested
- **Site Structure Analysis** - Real selectors discovered and verified with live site
- **Track Discovery** - Can identify all available tracks automatically (up to 15 per song)
- **Authentication System** - **WORKING** login with live credentials and "My Account" verification
- **Security Model** - All operations require login verification first
- **Track Selection** - Solo button functionality for isolating individual tracks
- **Download Process** - Comprehensive automation framework with progress tracking
- **Testing Suite** - Comprehensive test suite with unit, integration, and regression tests
- **Modular Architecture** - Clean package-based separation of concerns

### ✅ Technical Implementation - Production Ready
- **Environment Setup**: Virtual environment, dependencies, configuration files
- **YAML Configuration**: User-friendly song URL management in `songs.yaml`
- **Error Handling**: Comprehensive error handling and logging throughout
- **VERIFIED Selectors**: All selectors tested against live Karaoke-Version.com site
- **Working Login**: `frm_login`, `frm_password`, `sbm` selectors confirmed working
- **Modular Design**: Clean package architecture with no code duplication

### 🎉 Live Verification Results
**Tested with real credentials on live site:**
- ✅ **Login Success**: Finds "My Account" in header after authentication
- ✅ **Form Fields**: Successfully fills `frm_login` and `frm_password` fields
- ✅ **Submit Process**: Uses `name="sbm"` submit button 
- ✅ **Track Access**: Can access all available tracks on protected song pages
- ✅ **Performance**: Completes login in ~14 seconds
- ✅ **Session Management**: Properly detects and maintains login state

### 📁 Project Files
- **`karaoke_automator.py`** - Main automation script with modular architecture
- **`packages/`** - Modular package structure:
  - `authentication/` - Login management
  - `browser/` - Chrome setup and management
  - `configuration/` - YAML configuration handling
  - `download_management/` - Download orchestration
  - `file_operations/` - File management and cleanup
  - `progress/` - Progress tracking and statistics
  - `track_management/` - Track discovery and isolation
  - `utils/` - Logging and utilities
- **`songs.yaml`** - YAML-based song configuration
- **`tests/`** - Comprehensive test suite organized by category

## DISCOVERED SELECTORS (ALL WORKING ✅)
**These selectors are verified working with live site:**

### Login Selectors
- **Login Link**: `//a[contains(text(), 'Log in')]` (lowercase 'i')
- **Username Field**: `name="frm_login"` 
- **Password Field**: `name="frm_password"`
- **Submit Button**: `name="sbm"`
- **Success Indicator**: Look for "My Account" text in header

### Track Control Selectors
- **Track Elements**: `.track[data-index='0-14']` (up to 15 tracks per song)
- **Track Names**: `.track__caption` (instrument names)
- **Solo Buttons**: `button.track__solo` (track isolation)
- **Solo Behavior**: Mutually exclusive (one active solo mutes all others)

### Download Selectors
- **Download Button**: `a.download` (primary working selector)
- **Download Action**: `onclick="mixer.getMix();return false;"`
- **Click Handling**: JavaScript fallback for interception issues

### Mixer Control Selectors
- **Intro Count Checkbox**: `#precount` (ID selector)
- **Key Adjustment Buttons**: `button.btn--pitch.pitch__button`
  - Up button: `onclick='mixer.changePitch(8275, + 1);'`
  - Down button: `onclick='mixer.changePitch(8275, - 1);'`
- **Key Display**: `.pitch__caption` (shows current key like "D")

## Current Capabilities (100% PRODUCTION READY ✅)
1. ✅ **Authentication** - Fully working login with session persistence and optimized re-authentication
2. ✅ **Track Discovery** - Identifies all available tracks automatically
3. ✅ **Content Access** - Can access protected song pages after login
4. ✅ **Session Management** - Maintains and verifies login state throughout with persistent storage
5. ✅ **Track Isolation** - Solo button functionality for track selection
6. ✅ **Mixer Controls** - Intro count checkbox and key adjustment automation
7. ✅ **Download Process** - Complete download workflow with JavaScript fallback
8. ✅ **File Organization** - Song-specific folders with clean filenames
9. ✅ **Progress Tracking** - Real-time visual progress with comprehensive statistics
10. ✅ **Performance Options** - Headless mode and optimized login detection
11. ✅ **Session Persistence** - Saves login state across runs (24-hour expiry)
12. ✅ **Error Handling** - Click interception, network issues, edge cases

## SOLO BUTTON FUNCTIONALITY ✅
**Successfully implemented and tested track isolation:**
- **Solo Selector**: `button.track__solo` (confirmed working)
- **Mutual Exclusivity**: Solo buttons automatically mute all other tracks
- **Track Switching**: Can switch between any of the available tracks instantly
- **State Management**: Detects active solo buttons and can clear all
- **Performance**: Immediate response, no audio delays

### Solo Button Usage
```python
# Initialize automator and login
automator = KaraokeVersionAutomator()
automator.login()

# Get tracks for a song
tracks = automator.get_available_tracks(song_url)

# Solo a specific track (automatically mutes all others)
automator.solo_track(tracks[4], song_url)  # Solo "Lead Electric Guitar"

# Switch to vocal track
vocal_track = [t for t in tracks if 'vocal' in t['name'].lower()][0]
automator.solo_track(vocal_track, song_url)

# Clear all solos (unmute all tracks) 
automator.clear_all_solos(song_url)
```

## ✅ MIXER CONTROLS ENHANCEMENT - COMPLETE! 🎉

### Successfully Implemented Features
1. **🎼 Intro Count Checkbox** ✅ - Automatically ensures "Intro count" checkbox is selected for every track
2. **🎵 Key Adjustment Support** ✅ - Configurable pitch adjustment via songs.yaml key field
   - ✅ Read key value from song configuration (-12 to +12 semitones)
   - ✅ Automatically adjust mixer key display using up/down arrows
   - ✅ Support positive and negative key changes
   - ✅ Validation and error handling for out-of-range values

### Final songs.yaml Format
```yaml
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song.html"
    name: "Song_Directory_Name"  # Optional: auto-extracts from URL if omitted
    description: "Optional description"
    key: 2  # Optional: Pitch adjustment in semitones (-12 to +12)
    
  # Enhanced key format support:
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song2.html"
    key: "+3"   # String with explicit positive sign
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song3.html"
    key: "-2"   # String with negative sign
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song4.html"
    key: "5"    # String without sign (treated as positive)
```

**Key Format Support**: Accepts integers (`2`, `-3`), strings with explicit signs (`"+2"`, `"-3"`), and strings without signs (`"2"`, `"5"`).

## ✅ SESSION PERSISTENCE - COMPLETE! 🎉

### Successfully Implemented Features
1. **💾 Automatic Session Saving** ✅ - Saves cookies, localStorage, and session data after successful login
2. **⚡ Session Restoration** ✅ - Automatically restores saved session on subsequent runs
3. **🕐 Session Expiry Management** ✅ - 24-hour automatic expiry with fallback to fresh login
4. **🔄 Force Login Option** ✅ - Command-line flag to bypass saved session when needed
5. **🗑️ Session Management** ✅ - Clear session data command and automatic cleanup

### Session Management Commands
```bash
# Normal usage (uses saved session if available)
python karaoke_automator.py

# Force fresh login (bypass saved session)
python karaoke_automator.py --force-login

# Clear saved session data and exit
python karaoke_automator.py --clear-session
```

### Performance Benefits
- **First login**: ~4-14 seconds (normal login process)
- **Subsequent logins**: ~2-3 seconds (session restoration)
- **Time savings**: Up to 85% faster startup after initial login
- **Automatic fallback**: Seamlessly handles expired or invalid sessions

### Technical Implementation
- **Session Storage**: `.cache/session_data.pkl` file with pickled browser state (moved from project root 2025-06-16)
- **Data Saved**: Cookies, localStorage, sessionStorage, window state, timestamps
- **Security**: 24-hour expiry, automatic cleanup of old sessions
- **Compatibility**: Works with both headless and debug modes
- **Architecture**: Dual session persistence (Chrome profile primary + pickle fallback)

### 🔧 RECENT SESSION BUG FIX (2025-06-15)
**Bug**: `--force-login --debug` wasn't properly logging out users before fresh login  
**Root Cause**: In `packages/authentication/login_manager.py:519`, the `force_relogin` parameter wasn't being passed through to the underlying `login()` method  
**Fix**: Changed `return self.login(username, password, force_relogin=False)` to `return self.login(username, password, force_relogin=force_relogin)`  
**Impact**: `--force-login` now correctly logs out existing sessions before performing fresh authentication  
**File**: `packages/authentication/login_manager.py:519`

## Architecture Overview

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

### Key Architectural Benefits
- **Modular Design**: Clean separation of concerns with single responsibility
- **Testable Components**: Each package can be tested independently
- **Error Isolation**: Failures in one component don't cascade to others
- **Maintainable Code**: Changes localized to specific functionality areas
- **Reusable Components**: Packages can be used independently or combined

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

### Session Management
```bash
# Force fresh login (bypass saved session)
python karaoke_automator.py --force-login

# Clear saved session data
python karaoke_automator.py --clear-session

# Debug mode with fresh login
python karaoke_automator.py --debug --force-login
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

## Architecture Overview

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

### Key Architectural Benefits
- **Modular Design**: Clean separation of concerns with single responsibility
- **Testable Components**: Each package can be tested independently
- **Error Isolation**: Failures in one component don't cascade to others
- **Maintainable Code**: Changes localized to specific functionality areas
- **Reusable Components**: Packages can be used independently or combined

### Performance Patterns
**Smart WebDriverWait Implementation**: All blocking delays replaced with intelligent wait conditions
```python
# Responsive waits instead of fixed delays
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, ".track"))
)
WebDriverWait(driver, 10).until(
    lambda driver: "login" not in driver.current_url.lower() or
                   driver.find_elements(By.XPATH, "//*[contains(text(), 'My Account')]")
)
```

### Threading Architecture
- **Completion Monitoring**: Non-daemon threads with proper synchronization
- **Progress Tracking**: Real-time updates with 500ms intervals
- **Resource Cleanup**: Proper thread joining before browser shutdown

## Current Status: 🎉 PRODUCTION READY ✅

### Core Features Complete
- ✅ **Authentication & Session Management** - 24-hour session persistence with smart validation
- ✅ **Track Discovery & Isolation** - Automatic track detection and solo button functionality  
- ✅ **Mixer Controls** - Intro count and key adjustment automation
- ✅ **Download System** - Complete workflow with progress tracking and file organization
- ✅ **Modular Architecture** - Clean package-based design with dependency injection
- ✅ **Statistics & Reporting** - Comprehensive session tracking and final reports
- ✅ **Error Handling** - Robust error recovery with specific exception types
- ✅ **Test Suite** - Comprehensive testing with 100% regression pass rate

### Key Debugging Patterns

#### Exception Handling Best Practices
```python
# Use specific exceptions for better debugging
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    WebDriverException,
    TimeoutException
)

try:
    element.click()
except ElementClickInterceptedException:
    # Handle click interception specifically
    logging.debug("Click intercepted, trying alternative method")
except NoSuchElementException:
    # Handle missing elements
    logging.warning("Element not found")
```

#### Safe Method Refactoring Patterns
**Best practices for large method extraction:**
1. **Use feature branches** for isolation
2. **Extract incrementally** (20-50 lines at a time)
3. **Test after each extraction**
4. **Maintain function signatures** to avoid breaking calls
5. **Name methods descriptively** (`_setup_download_context()` vs generic names)

## Current Project Status

### System State: 🎉 Production Ready
- ✅ **Core Functionality**: All automation features working reliably
- ✅ **Performance Optimized**: Smart waits instead of blocking delays (4-6x improvement)
- ✅ **Test Coverage**: 100% regression test pass rate
- ✅ **Code Quality**: Clean modular architecture with proper exception handling
- ✅ **Documentation**: Comprehensive usage guides and debugging patterns
- ✅ **Threading**: Proper synchronization prevents race conditions

### Quick Start for New Sessions
**Verify Current State**:
```bash
source bin/activate
python tests/run_tests.py --regression-only  # Should show 100% pass
python -c "from karaoke_automator import KaraokeVersionAutomator; print('✅ Ready')"
```

**Run Automation**:
```bash
# Edit songs.yaml with your desired songs
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
