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

### 🔧 FINAL CLEANUP PASS ENHANCEMENT (2025-07-08)
**Problem**: Some downloaded files weren't cleaned up due to 30-second time window restriction during sequential downloads  
**Root Cause**: The cleanup system only cleaned files downloaded within 30 seconds, but sequential downloads can take several minutes  
**Files Affected**: Early tracks became "old" by the time later tracks completed, leaving long karaoke-version filenames  
**Solution**: Added comprehensive final cleanup pass that runs after all downloads complete  
**Files Modified**:
- `packages/file_operations/file_manager.py`: Added `final_cleanup_pass()` method with pattern matching and track name extraction
- `karaoke_automator.py:231-234`: Integrated final cleanup into main automation flow  
**Impact**: Ensures 100% of downloaded files get properly renamed regardless of download timing  
**Test Results**: Successfully cleaned 2 uncleaned files in Bruce Springsteen directory during testing

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

**Note**: Both production and debug modes now show identical progress UI. The only difference is browser visibility and log file detail level.

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

### ✅ Final Cleanup Pass System (Latest Enhancement)
- **Post-Download Cleanup**: Comprehensive final cleanup pass after all downloads complete
- **Race Condition Prevention**: Runs after all downloads finish to avoid timing conflicts
- **Smart Pattern Matching**: Identifies uncleaned files using Custom_Backing_Track patterns
- **Automatic File Extraction**: Extracts track names from long karaoke-version filenames
- **Complete Coverage**: Catches any files missed by time-based cleanup during download

## Current Status: PRODUCTION READY + SESSION PERSISTENCE + FINAL CLEANUP COMPLETE ✅

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
# Edit songs.yaml with your desired songs (check indentation: exactly 2 spaces!)
python karaoke_automator.py              # Production mode
python karaoke_automator.py --debug      # Debug mode with visible browser
```

## Recent Updates & Bug Fixes

### 🎯 Click Track Recognition Fixed (2025-06-17)
**Issue**: Click tracks with spaced names like "Intro count      Click" were showing as failed despite successful downloads
**Root Cause**: File matching logic incorrectly filtered out "intro" and "count" as skip words, failing to match downloaded files
**Fix Applied**: 
- Enhanced `_does_file_match_track()` method in `packages/download_management/download_manager.py`
- Removed "intro" and "count" from skip words list  
- Added proper whitespace normalization with `' '.join(track_lower.split())`
- Improved click track special case handling
**Result**: Click tracks now properly recognized and marked successful ✅

### 🧹 Browser Cleanup Errors Fixed (2025-06-17)  
**Issue**: Connection refused errors flooding the screen after automation completion
**Root Cause**: Multiple cleanup attempts trying to quit the same browser driver (3 separate locations)
**Fix Applied**:
- Centralized cleanup through `chrome_manager.quit()` only
- Removed duplicate `driver.quit()` from `run_automation()` finally block  
- Added connection error suppression for already-closed browsers
- Updated signal handler to prevent duplicate cleanup attempts
**Result**: Clean automation completion without error message spam ✅

### 📝 YAML Configuration Errors (2025-06-17)
**Issue**: "ERROR: string indices must be integers, not 'str'" during configuration loading
**Root Cause**: YAML indentation sensitivity - 3 spaces instead of 2 caused parsing failure
**Fix Applied**: 
- Fixed `songs.yaml` indentation (line 12: 3 spaces → 2 spaces)
- Enhanced README with comprehensive YAML formatting requirements
- Added troubleshooting section mapping errors to solutions
**Result**: Proper configuration parsing and user guidance ✅

### 🔧 Phase 2 Refactoring Completed (2025-06-17)
**Achievement**: Successfully refactored 5 major methods (539 total lines) into 52 focused helper methods
- **karaoke_automator.py**: `run_automation()` (124 lines → 12 methods)
- **authentication/**: `fill_login_form()` (86→5), `logout()` (71→7)  
- **download_management/**: `start_completion_monitoring()` (116→15)
- **track_management/**: `solo_track()` (142→13)
**Benefits**: Methods under 30 lines, improved maintainability, 100% functionality preserved

### 🧪 Enhanced Testing Coverage (2025-06-17)
**Achievement**: Added comprehensive unit tests for newly extracted Phase 2 helper methods
- **Created**: `tests/unit/test_automation_workflow.py` with 30 unit tests
- **Coverage**: All 12 helper methods from `karaoke_automator.py` refactoring
- **Test Types**: Success paths, failure scenarios, edge cases, exception handling
- **Quality**: Proper mocking, isolated testing, comprehensive assertions
- **Result**: 100% test pass rate while maintaining regression test compatibility ✅
**Analysis**: Identified 43 total helper methods across all packages requiring future test coverage
**Impact**: Improved code maintainability and confidence in refactored methods

### 📁 Directory Naming Bug - Apostrophe Handling Fixed (2025-06-17)
**Issue**: Songs with apostrophes created poorly formatted directory names with orphaned letters
**Example**: "Don't Stop Me Now" became "Queen_Don T Stop Me Now" (space before 'T')
**Root Cause**: Two separate issues in different modules:
1. **Direct apostrophes**: `sanitize_filesystem_name()` didn't include apostrophes in invalid_chars
2. **URL patterns**: URLs like "don-t-stop-me-now" created "Don T Stop" instead of "Dont Stop"
**Fix Applied**:
- **packages/download_management/download_manager.py:362**: Added apostrophe to `invalid_chars = '<>:"/\\|?*\'`
- **packages/configuration/config_manager.py:114**: Added apostrophe to `invalid_chars` + regex to handle `-[letter]-` patterns
- **Enhanced logic**: `re.sub(r'-([a-z])-', r'\1-', path_part)` converts "don-t-stop" → "dont-stop"
**Result**: "Queen_Dont Stop Me Now" (clean directory names) ✅
**Status**: ✅ **FIXED** - All regression tests pass, functionality preserved

### 🖥️ Stdout Log Leakage Fixed (2025-06-17)
**Issue**: Log data was printing to stdout during download process in non-debug mode, interfering with clean status UI
**Root Cause**: `ProgressTracker` class used `print()` statements that bypassed the logging system configuration
**Examples**: Progress displays, download summaries, and final reports appeared on stdout regardless of debug mode
**Fix Applied**:
- **packages/progress/progress_tracker.py**: Added `show_display` parameter to control visual output
- **Modified methods**: `_update_display()`, `_display_track_progress()`, `_final_display()` now respect display mode
- **karaoke_automator.py**: Previously passed `show_progress=args.debug` to only show progress in debug mode
- **Final reports**: Conditional display vs logging based on debug mode
**Result**: Clean stdout in non-debug mode, detailed progress display preserved in debug mode ✅
**Status**: ✅ **FIXED** - Non-debug mode now shows only essential logging messages

### 🎨 UI Unification Enhancement (2025-07-11)
**Issue**: Production mode had no progress UI while debug mode had beautiful visual progress tracking
**Root Cause**: `show_progress` parameter was tied to debug mode, creating inconsistent user experience
**Architecture Decision**: Separate UI behavior from debug mode - users should get consistent visual feedback regardless of browser visibility
**Solution Applied**:
- **karaoke_automator.py:366**: Changed `show_progress=args.debug` to `show_progress=True` (UI enabled for both modes)
- **packages/utils/logging_setup.py:78**: Unified console logging to `WARNING+` for both modes (matches existing debug behavior)
**Result**: Identical beautiful progress UI in both debug and production modes ✅
**Architectural Benefits**:
- **Consistent UX**: Users get same visual feedback regardless of browser visibility
- **Clean Console**: No logging conflicts with progress UI screen clearing
- **Information Preservation**: All INFO messages preserved in log files
- **Maintainability**: Single code path for UI behavior reduces complexity
**Status**: ✅ **ENHANCED** - UI behavior now unified across all modes

---

## important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context or otherwise consider it in your response unless it is highly relevant to your task. Most of the time, it is not relevant.
