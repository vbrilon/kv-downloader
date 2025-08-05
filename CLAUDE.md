# Karaoke-Version.com Track Automation - Architecture Guide

## IMPORTANT: Environment Setup
```bash
source bin/activate  # ALWAYS activate virtual environment first
python karaoke_automator.py --debug      # Debug mode (visible browser)
python karaoke_automator.py              # Production mode (headless)
```

## Songs Configuration (songs.yaml)
```yaml
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song.html"
    name: "Song_Directory_Name"  # Optional: auto-extracts from URL if omitted
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

### Track Management System (packages/track_management/)
- **Track Discovery**: Up to 15 tracks per song (data-index 0-14)
- **Complexity Detection**: Adaptive timeouts based on track count (≤8 simple, 9+ complex)
- **Solo Isolation**: Mutually exclusive track isolation with 2-phase validation:
  1. Solo button activation with retry logic
  2. Audio mix state validation (solo button active check)
- **Adaptive Timeouts**: 15s for simple arrangements, 21s for complex arrangements

### Download Management System (packages/download_management/)
- **Modular Download Flow**: `download_current_mix()` orchestrates 4 focused methods:
  - `_navigate_and_find_download_button()`: Page navigation and button finding
  - `_validate_pre_download_requirements()`: Pre-download validation with retry
  - `_execute_download_action()`: Download execution and progress tracking
  - `_monitor_download_completion()`: Download monitoring and completion handling
- **Performance Optimization**: 30s initial wait before active monitoring (server generation time)
- **Cross-Browser Mode Compatibility**: Handles timing differences between headless and visible modes
- **File Processing Pipeline**: Download detection → File cleanup/renaming → Validation with updated paths

### Session Management & Authentication (packages/authentication/)
- **Chrome Profile Reuse**: Persistent authentication via `chrome_profile/`
- **Session Storage**: `.cache/session_data.pkl` with 24-hour expiry
- **Performance**: 85% faster subsequent runs (2-3s vs 4-14s)

### Testing & Regression Prevention
- **Unit Test Coverage**: 117+ comprehensive tests across critical architectural components
- **Regression Testing**: `python tests/run_tests.py --regression-only` for system validation
- **Critical Tests**: Download detection, completion monitoring, dependency injection

### File Operations System (packages/file_operations/)
- **Performance-Optimized Caching**: 60-80% reduction in file system calls
  - 2-second TTL cache for file metadata, optimized directory scanning
  - Pre-compiled pattern matching for audio files and karaoke detection
- **Cross-Mode Download Detection**: Handles both headless and visible browser modes
- **File Cleanup**: Removes `_Custom_Backing_Track` suffixes, simplifies to clean track names
- **Content Validation**: Audio file validation with proper path tracking after renaming

## Current Performance Configuration (⚠️ May cause regression)
- **SOLO_ACTIVATION_DELAY**: 12.0s (base), 15.0s (simple), 21.0s (complex)
- **DOWNLOAD_CHECK_INTERVAL**: 5s (optimized from 2s)
- **DOWNLOAD_MAX_WAIT**: 90s (reduced from 300s)
- **DOWNLOAD_MONITORING_INITIAL_WAIT**: 30s (new optimization)

## Architecture Notes for Future Sessions
- **Performance Regression**: Current optimizations causing 2x slowdown - investigate adaptive timeouts and initial wait
- **Instrumentation Needed**: Add comprehensive timing decorators to identify real bottlenecks
- **Test Coverage**: 117+ unit tests prevent regressions during optimization work
