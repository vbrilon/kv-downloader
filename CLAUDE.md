# Karaoke-Version.com Track Automation - Architecture Guide

## Songs Configuration (songs.yaml)
```yaml
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song.html"
    name: "Song_Directory_Name"  # Optional: smart auto-extraction from URL if omitted
    key: -1  # Optional: Pitch adjustment in semitones (-12 to +12)
```

### Smart Folder Naming
- **No conflicts**: Folders named with song only (e.g., "Paranoid", "Starlight")
- **With conflicts**: Folders include artist to prevent overwrites (e.g., "Fleetwood Mac - The Chain", "Ingrid Michaelson - The Chain")
- **Automatic detection**: System scans all configured songs and detects name conflicts across the entire configuration

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
└── utils/           # Logging, error handling, performance profiling, and cross-cutting utilities
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

### Performance Profiling System (packages/utils/performance_profiler.py)
- **Multi-Tier Architecture**: System → Component → Method → Operation level timing analysis
- **@profile_timing()**: General-purpose method timing decorator with component/tier classification
- **@profile_selenium()**: Specialized Selenium operation profiling with timeout/retry tracking
- **PerformanceProfiler**: Thread-safe timing collection with memory usage tracking
- **Automated Reporting**: Hierarchical performance breakdowns with bottleneck identification
- **Memory Tracking**: Resource consumption analysis (when psutil available)

### A/B Testing & Baseline System (packages/utils/baseline_tester.py)
- **PerformanceBaselineTester**: Context-managed configuration switching for regression analysis
- **4 Pre-Defined Baselines**:
  - `current`: Current config (suspected 2x regression source)
  - `pre_optimization`: Original baseline (before regression)
  - `solo_only`: Isolate solo activation delay impact (5s → 12s/15s/21s)
  - `download_only`: Isolate download monitoring impact (0s → 30s initial wait)
- **Dynamic Configuration**: Runtime modification with automatic restoration
- **Comprehensive Analysis**: Performance differentials, optimization recommendations
- **JSON Result Storage**: Detailed timing data saved to `logs/performance/baselines/`

### Key Site Selectors (Verified Working)
- **Login**: `name="frm_login"`, `name="frm_password"`, `name="sbm"`
- **Tracks**: `.track[data-index]`, `.track__caption`, `button.track__solo`
- **Download**: `a.download`, JavaScript fallback for interception
- **Mixer**: `#precount`, `button.btn--pitch.pitch__button`, `.pitch__caption`

### Track Management System (packages/track_management/) - INSTRUMENTED & OPTIMIZED
- **Track Discovery**: Up to 15 tracks per song (data-index 0-14)
- **Complexity Detection**: Adaptive timeouts based on track count (≤8 simple, 9+ complex)
- **Solo Isolation**: Mutually exclusive track isolation with 2-phase validation:
  1. **Phase 1 (Optimized)**: Initial button activation with 200ms polling, 8s timeout
  2. **Phase 2 (Optimized)**: Audio server sync with deterministic DOM detection, 0.5-2s typical response
- **Performance Optimizations**: 
  - Phase 1: Reduced from 10s timeout to 8s with 200ms polling for responsiveness
  - Phase 2: DOM-based detection replacing blind 10s waits, achieving 0.3-2s response times
- **Performance Instrumentation**: 5 key methods profiled with comprehensive optimization results

### Download Management System (packages/download_management/) - INSTRUMENTED
- **Modular Download Flow**: `download_current_mix()` orchestrates 4 focused methods:
  - `_navigate_and_find_download_button()`: Page navigation and button finding
  - `_validate_pre_download_requirements()`: Pre-download validation with retry
  - `_execute_download_action()`: Download execution and progress tracking
  - `_monitor_download_completion()`: Download monitoring and completion handling (INSTRUMENTED)
- **Performance Optimization**: 30s initial wait before active monitoring (server generation time)
- **Cross-Browser Mode Compatibility**: Handles timing differences between headless and visible modes
- **File Processing Pipeline**: Download detection → File cleanup/renaming → Validation with updated paths

### Session Management & Authentication (packages/authentication/) - INSTRUMENTED
- **Chrome Profile Reuse**: Persistent authentication via `chrome_profile/`
- **Session Storage**: `.cache/session_data.pkl` with 24-hour expiry
- **Performance**: 85% faster subsequent runs (2-3s vs 4-14s)
- **Performance Instrumentation**: `login_with_session_persistence()` method profiled

### Testing & Regression Prevention
- **Unit Test Coverage**: 117+ comprehensive tests across critical architectural components
- **Regression Testing**: `python tests/run_tests.py --regression-only` for system validation
- **Performance Baseline Testing**: A/B configuration comparison for regression analysis
- **Critical Tests**: Download detection, completion monitoring, dependency injection

### File Operations System (packages/file_operations/) - INSTRUMENTED
- **Performance-Optimized Caching**: 60-80% reduction in file system calls
  - 2-second TTL cache for file metadata, optimized directory scanning
  - Pre-compiled pattern matching for audio files and karaoke detection
- **Cross-Mode Download Detection**: Handles both headless and visible browser modes
- **File Cleanup**: Removes `_Custom_Backing_Track` suffixes, simplifies to clean track names
- **Content Validation**: Audio file validation with proper path tracking after renaming
- **Performance Instrumentation**: `clear_song_folder()` and `final_cleanup_pass()` methods profiled

## Current Performance Configuration
- **SOLO_ACTIVATION_DELAY**: 5.0s (base timeout)
- **SOLO_ACTIVATION_DELAY_SIMPLE**: 7.0s (8 tracks or fewer)
- **SOLO_ACTIVATION_DELAY_COMPLEX**: 10.0s (9+ tracks)
- **SOLO_ACTIVATION_DELAY_CLICK**: 12.0s (click tracks - extended for reliability)
- **SOLO_ACTIVATION_DELAY_SPECIAL**: 10.0s (bass/drums tracks)
- **DOWNLOAD_CHECK_INTERVAL**: 3s (optimized polling)
- **DOWNLOAD_MAX_WAIT**: 90s

**Current Performance**: ~20s per track with enhanced reliability for all track types

## Critical Architecture Components

### **Enhanced Solo Button Detection System**
- **Multi-Method Detection**: 4 detection approaches (CSS classes, ARIA attributes, data attributes, visual state)
- **Track-Type-Aware Timeouts**: Click tracks (12s), bass/drums (10s), standard (7s/10s based on complexity)
- **Consistent Detection**: Same enhanced logic used in both solo activation AND download verification
- **Smart Solo Management**: `ensure_only_track_active()` method for selective clearing vs full clearing

### **Track Management Optimizations**
- **Track Type Classification**: Automatic detection of click, bass, drums, vocal, standard tracks
- **Adaptive Timeout System**: Dynamic timeouts based on track type and song complexity
- **Enhanced Button State Detection**: Robust detection replacing simple CSS class checks
- **Performance-Optimized Clearing**: Selective deactivation of conflicting tracks only

### **Download Verification Enhancements**  
- **Enhanced Detection Consistency**: Download verification uses same multi-method detection as track management
- **Robust State Validation**: 4-check verification system (track element, solo button active, other solos inactive, track name match)
- **Comprehensive Error Logging**: Detailed diagnostic information for troubleshooting failures

### **Performance Profiling Infrastructure**
- **Multi-Tier Profiling**: System → Component → Method → Operation level timing analysis
- **A/B Testing Framework**: Baseline comparison capability for regression analysis
- **Memory Tracking**: Resource consumption analysis with psutil integration
- **Comprehensive Instrumentation**: Method-level timing across all critical path components

### **Key Technical Achievements**
- **DOM-Based Detection**: Near-instantaneous download readiness detection vs hardcoded waits
- **Headless Mode Reliability**: Race condition prevention through smart solo state management
- **Click Track Reliability**: Specialized handling for problematic track types
- **Performance Optimization**: ~20s per track with enhanced reliability across all track types

## Logging System Architecture (packages/utils/)

### **Multi-Tier Logging System**
- **Production Logs** (`logs/automation.log`): Operational tracking with emoji-based visual scanning
- **Debug Logs** (`logs/debug.log`): Detailed debug information when `--debug` flag used
- **Performance Logs** (`logs/performance/*.log`): Specialized timing analysis with method-level instrumentation
- **Stats JSON** (`logs/automation_stats.json`): Structured operational metrics and success rates

### **Logging Effectiveness Assessment**
- **Overall Rating**: 8.5/10 for operational insights
- **Strengths**: Rich contextual information, clear success/failure tracking, performance correlation
- **Minor Issue**: "Could not find target button" warnings are harmless noise (should be DEBUG level)
- **Operational Value**: Enables quick issue identification, performance regression detection, detailed troubleshooting

### **Error Handling Decorators**
- **@selenium_safe**: Selenium operations with consistent error handling
- **@validation_safe**: Validation methods returning boolean results
- **@file_operation_safe**: File system operations
- **@retry_on_failure**: Exponential backoff retry logic
