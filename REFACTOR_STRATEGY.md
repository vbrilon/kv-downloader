# Karaoke Automator Refactoring Strategy

## Current State Analysis
- **Total Lines**: ~2,000 lines in a single file
- **Largest Class**: `KaraokeVersionTracker` (1,214 lines) - **MAJOR REFACTOR TARGET**
- **Main Issues**: Mixed responsibilities, code duplication, dead code, poor separation of concerns

## Proposed Module Structure

### 1. **Core Infrastructure Modules**

#### `browser/` package
- **`driver_manager.py`** (~150 lines)
  - Chrome WebDriver setup and configuration
  - Browser options and preferences management
  - Driver lifecycle (start, stop, restart)
  - Download path configuration
  ```python
  class ChromeDriverManager:
      def setup_driver(headless=True, download_path=None)
      def configure_chrome_options()
      def set_download_behavior()
  ```

- **`selectors.py`** (~50 lines)
  - Centralized CSS selectors and XPath expressions
  - Constants for all site elements
  ```python
  class KaraokeSelectors:
      LOGIN_LINK = "//a[contains(text(), 'Log in')]"
      USERNAME_FIELD = "name='frm_login'"
      TRACK_ELEMENT = ".track"
      # ... all selectors
  ```

#### `authentication/` package
- **`auth_manager.py`** (~200 lines)
  - Move `KaraokeVersionLogin` class here
  - Login status detection
  - Session management
  - Force re-login capability

#### `progress/` package  
- **`progress_tracker.py`** (~175 lines)
  - Move `ProgressTracker` class here
  - Real-time progress visualization
  - Thread-safe status management

### 2. **Core Business Logic Modules**

#### `track_management/` package
- **`track_discovery.py`** (~200 lines)
  - Extract track discovery logic from `KaraokeVersionTracker`
  - Song access verification
  - Track enumeration and parsing
  ```python
  class TrackDiscovery:
      def get_available_tracks(song_url)
      def verify_song_access(song_url)
      def parse_track_info(track_elements)
  ```

- **`mixer_controls.py`** (~200 lines)
  - Solo/mute functionality
  - Key adjustment controls  
  - Intro count management
  ```python
  class MixerControls:
      def solo_track(track_info, song_url)
      def adjust_key(song_url, target_key)
      def ensure_intro_count_enabled(song_url)
  ```

#### `download_management/` package
- **`download_orchestrator.py`** (~250 lines)
  - Download initiation and coordination
  - Download sequencing logic
  - Integration with progress tracking
  ```python
  class DownloadOrchestrator:
      def download_current_mix(song_url, track_name, key_adjustment=0)
      def initiate_download(song_url)
      def wait_for_download_start()
  ```

- **`download_monitor.py`** (~200 lines)
  - Background download completion monitoring
  - File detection and tracking
  - .crdownload handling
  ```python
  class DownloadMonitor:
      def schedule_completion_monitoring()
      def monitor_download_progress()
      def detect_completed_downloads()
  ```

#### `file_operations/` package
- **`file_manager.py`** (~200 lines)
  - Directory creation and management
  - File moving and organization
  - Cleanup and deduplication
  ```python
  class FileManager:
      def setup_song_folder(song_folder_name)
      def extract_song_folder_name(song_url)
      def cleanup_existing_files()
  ```

- **`filename_cleaner.py`** (~150 lines)
  - Consolidate all filename sanitization logic
  - Pattern removal (Custom_Backing_Track, etc.)
  - Track name and key adjustment formatting
  ```python
  class FilenameCleaner:
      def clean_filename_after_download(file_path, track_name, key_adjustment)
      def sanitize_filename(filename)
      def remove_song_name_redundancy()
  ```

### 3. **Main Coordination Module**

#### `automation/` package
- **`main_automator.py`** (~200 lines)
  - Simplified main coordinator
  - Dependency injection
  - High-level workflow orchestration
  ```python
  class KaraokeVersionAutomator:
      def __init__(self, headless=True, show_progress=True)
      def run_automation()
      def process_song(song_config)
  ```

### 4. **Utilities and Configuration**

#### `utils/` package
- **`logging_setup.py`** (~50 lines)
  - Move `setup_logging()` function
  - Logging configuration management

- **`exceptions.py`** (~50 lines)
  - Custom exception classes
  - Common error handling patterns

#### Keep existing:
- **`config.py`** - Configuration constants
- **`config_manager.py`** - Configuration business logic

## Refactoring Implementation Plan

### Phase 1: Extract Infrastructure (Low Risk)
1. **Create `browser/` package**
   - Extract driver setup logic
   - Create centralized selectors
   - Update imports in main file

2. **Create `progress/` package** 
   - Move `ProgressTracker` class
   - Update imports and dependencies

3. **Create `authentication/` package**
   - Move `KaraokeVersionLogin` class
   - Test login functionality

### Phase 2: Break Down Core Logic (Medium Risk)
4. **Create `file_operations/` package**
   - Extract and consolidate file management
   - Consolidate filename cleaning logic
   - Remove code duplication

5. **Create `track_management/` package**
   - Extract track discovery from `KaraokeVersionTracker`
   - Extract mixer controls
   - Split into focused classes

### Phase 3: Download Management (High Risk) 
6. **Create `download_management/` package**
   - Extract download orchestration
   - Extract background monitoring
   - Maintain progress integration

### Phase 4: Final Coordination (Low Risk)
7. **Simplify main coordinator**
   - Update `KaraokeVersionAutomator` to use new modules
   - Remove now-empty `KaraokeVersionTracker`
   - Clean up imports and dependencies

### Phase 5: Testing and Cleanup
8. **Update test suite**
   - Update imports in all test files
   - Add unit tests for new modules
   - Run comprehensive regression testing

9. **Documentation update**
   - Update CLAUDE.md with new architecture
   - Create module documentation
   - Update usage examples

## Expected Results

### **Before Refactoring:**
```
karaoke_automator.py    (~2,000 lines)
config.py               (~50 lines)
config_manager.py       (~200 lines)
```

### **After Refactoring:**
```
browser/
├── driver_manager.py      (~150 lines)
└── selectors.py           (~50 lines)

authentication/
└── auth_manager.py        (~200 lines)

track_management/
├── track_discovery.py     (~200 lines)
└── mixer_controls.py      (~200 lines)

download_management/
├── download_orchestrator.py  (~250 lines)
└── download_monitor.py       (~200 lines)

file_operations/
├── file_manager.py        (~200 lines)
└── filename_cleaner.py    (~150 lines)

progress/
└── progress_tracker.py    (~175 lines)

automation/
└── main_automator.py      (~200 lines)

utils/
├── logging_setup.py       (~50 lines)
└── exceptions.py          (~50 lines)

config.py                  (~50 lines)
config_manager.py          (~200 lines)
```

## Benefits

### **Maintainability**
- Each module has a single, clear responsibility
- Easier to locate and fix bugs
- Simpler to add new features

### **Testability** 
- Each module can be unit tested independently
- Easier to mock dependencies
- More focused test cases

### **Reusability**
- Components can be reused in different contexts
- Cleaner dependency management
- Better separation of concerns

### **Code Quality**
- Elimination of dead code
- Reduced code duplication
- Consistent error handling patterns

## Risk Mitigation

### **Regression Prevention**
- Run full regression test suite after each phase
- Maintain backward compatibility during transition
- Use feature flags for gradual rollout

### **Testing Strategy**
- Unit tests for each new module
- Integration tests for module interactions
- End-to-end validation after each phase

### **Rollback Plan**
- Keep original file as backup during refactoring
- Git branching strategy for each phase
- Ability to revert to working state at any point

## Timeline Estimate
- **Phase 1-2**: 1-2 sessions (Infrastructure + Core Logic)
- **Phase 3**: 1 session (Download Management - most complex)
- **Phase 4-5**: 1 session (Final Coordination + Testing)
- **Total**: 3-4 development sessions

This refactoring will transform a monolithic 2K line file into a well-organized, maintainable codebase with clear separation of concerns and improved testability.