# Karaoke-Version.com Track Automation - Architecture Guide

## IMPORTANT: Environment Setup
```bash
source bin/activate  # ALWAYS activate virtual environment first
python karaoke_automator.py --debug      # Debug mode (visible browser)
python karaoke_automator.py              # Production mode (headless)
python karaoke_automator.py --profile    # Performance profiling mode (with timing logs)
```

## Performance Profiling & Analysis Commands
```bash
# A/B regression testing
python karaoke_automator.py --ab-test pre_optimization current --max-tracks 2

# Isolate specific bottlenecks  
python karaoke_automator.py --ab-test current solo_only --max-tracks 2
python karaoke_automator.py --ab-test current download_only --max-tracks 2

# List available baseline configurations
python karaoke_automator.py --list-baselines

# Performance regression analysis workflow
python analyze_performance_regression.py
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

## Current Performance Configuration (✅ OPTIMIZED - Regression Resolved)
- **SOLO_ACTIVATION_DELAY**: 5.0s (restored from pre-regression value)
- **SOLO_ACTIVATION_DELAY_SIMPLE**: 7.0s (optimized from 15.0s - 53% reduction)
- **SOLO_ACTIVATION_DELAY_COMPLEX**: 10.0s (optimized from 21.0s - 52% reduction)
- **DOWNLOAD_MONITORING_INITIAL_WAIT**: 15s (optimized from 30s - 50% reduction)
- **DOWNLOAD_CHECK_INTERVAL**: 5s (maintained)
- **DOWNLOAD_MAX_WAIT**: 90s (maintained)

## Architecture Notes for Future Sessions
- **Performance Regression**: ✅ **RESOLVED** - 2x performance regression successfully eliminated through comprehensive optimization
- **Profiling Infrastructure**: Multi-tier timing system with method-level instrumentation across critical path components
- **Deterministic Solo Detection**: Replaced blind 10s waits with DOM-based solo button state detection (0.5-2s typical response)
- **Performance Improvement**: **75-85% faster per track** - from ~78s to ~12-18s per track processing time
- **A/B Testing System**: Baseline comparison capability for isolating regression sources and validating optimizations
- **Recent Optimizations**: 
  - Phase 1 solo button activation: 10s → 8s timeout with 200ms polling (increased responsiveness)
  - Phase 2 audio server sync: 10s blind wait → 0.3-2s DOM detection (major optimization)
  - Variable scope bug fix: Exception handling in download operations properly initialized
- **Test Coverage**: 117+ unit tests prevent regressions during optimization work
- **Documentation**: Complete profiling system documented in `docs/PERF.md`
- **Optimization Methodology**: 
  - Comprehensive profiling identified exact bottlenecks (21s audio server sync delays)
  - Targeted configuration optimizations (reduced timeouts by 50-53%)
  - Deterministic DOM detection replaced unreliable UI state scanning
  - Intelligent fallback strategies with minimal safety buffers
- **Test Coverage**: 117+ unit tests prevent regressions during optimization work
- **Memory Tracking**: Performance profiler now includes memory usage analysis with psutil integration
