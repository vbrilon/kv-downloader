# Karaoke-Version.com Track Automation

## IMPORTANT: Virtual Environment Requirement
**ALWAYS activate the virtual environment before any Python operations:**
```bash
source bin/activate  # On macOS/Linux
```

## Overview
Production-ready automated system for downloading isolated backing tracks from Karaoke-Version.com using Python and Selenium. Downloads all available tracks for specified songs into organized directories.

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

## Architecture

### Package Structure
```
packages/
├── authentication/     # Login management and session handling
├── browser/           # Chrome setup and download path management
├── configuration/     # YAML config parsing, validation, and constants
├── di/               # Dependency injection container and interfaces
├── download_management/  # Download orchestration and monitoring
├── file_operations/   # File management and cleanup
├── progress/         # Progress tracking and statistics reporting
├── track_management/ # Track discovery, isolation, mixer controls
└── utils/           # Logging, error handling, and cross-cutting utilities
```

### Configuration System (packages/configuration/)
- **config.py**: Centralized constants for timeouts, delays, retries, and thresholds
  - WebDriver timeouts (WEBDRIVER_DEFAULT_TIMEOUT, WEBDRIVER_SHORT_TIMEOUT, etc.)
  - Sleep/delay intervals (PROGRESS_UPDATE_INTERVAL, CLICK_HANDLER_DELAY, etc.)
  - Retry limits and polling intervals (TRACK_SELECTION_MAX_RETRIES, DOWNLOAD_MAX_WAIT, etc.)
  - File matching ratios and UI constants
- **config_manager.py**: Configuration parsing and validation logic

### Dependency Injection System (packages/di/)
- **DIContainer**: Lightweight dependency injection container for service management
- **Interfaces**: Abstract base classes defining contracts for major components
  - `IProgressTracker`: Progress tracking interface
  - `IFileManager`: File operations interface  
  - `IChromeManager`: Browser management interface
  - `IStatsReporter`: Statistics reporting interface
  - `IConfig`: Configuration management interface
- **Adapters**: Bridge pattern implementations connecting existing classes to interfaces
- **Factory**: Service creation and container setup utilities

### Error Handling System (packages/utils/error_handling.py)
- **@selenium_safe**: Decorator for Selenium operations with consistent error handling
- **@validation_safe**: Decorator for validation methods returning boolean results
- **@file_operation_safe**: Decorator for file system operations
- **@retry_on_failure**: Decorator with exponential backoff retry logic
- **ErrorContext**: Context manager for complex operation error handling

### Key Site Selectors (Verified Working)
- **Login**: `name="frm_login"`, `name="frm_password"`, `name="sbm"`
- **Tracks**: `.track[data-index]`, `.track__caption`, `button.track__solo`
- **Download**: `a.download`, JavaScript fallback for interception
- **Mixer**: `#precount`, `button.btn--pitch.pitch__button`, `.pitch__caption`

### Track Management System
- **Track Discovery**: Up to 15 tracks per song (data-index 0-14)
- **Solo Isolation**: Mutually exclusive track isolation with simplified 2-phase validation:
  1. Solo button activation with retry logic
  2. Simple audio mix state validation (solo button active check)

### Download Management System
- **Dependency Injection**: DownloadManager uses constructor injection for all dependencies
- **Modular Download Flow**: `download_current_mix()` orchestrates 4 focused methods:
  - `_navigate_and_find_download_button()`: Page navigation and button finding
  - `_validate_pre_download_requirements()`: Pre-download validation with retry
  - `_execute_download_action()`: Download execution and progress tracking
  - `_monitor_download_completion()`: Download monitoring and completion handling
- **File Processing Pipeline**: Coordinated sequence ensuring validation uses correct file paths:
  1. Download completion detection
  2. File cleanup/renaming with path mapping (`old_path → new_path`)
  3. Validation using updated paths after renaming
- **Error Handling**: Standardized error handling using decorators
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

### File Operations System (packages/file_operations/)
- **Performance-Optimized Architecture**: 60-80% reduction in file system calls through intelligent caching
  - 2-second TTL cache for file metadata (`stat()`, `exists()`, `is_file()`, `is_dir()`)
  - Optimized directory scanning with `_scan_directory_cached()` to reduce `iterdir()` operations
  - Pre-compiled pattern matching for audio files and karaoke detection
  - Batch file information processing instead of individual calls
- **Download Path Management**: Automatic Chrome download path configuration per song
- **File Cleanup**: Intelligent filename cleaning removing site-generated suffixes
  - Removes `_Custom_Backing_Track` patterns and parenthetical content
  - Simplifies to clean track names (e.g., `"Drum Kit.mp3"`)
- **Content Validation**: Audio file validation with proper path tracking after renaming
- **Error Recovery**: Fallback mechanisms for file system operations


