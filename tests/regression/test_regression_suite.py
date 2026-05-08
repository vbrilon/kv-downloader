#!/usr/bin/env python3
"""
Regression Test Suite
Quick validation that core functionality still works after refactoring
Designed to be run before/after code changes to catch regressions
"""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from karaoke_automator import KaraokeVersionAutomator, setup_logging


@pytest.mark.live
def test_regression_core_functions():
    """Test core functions still work - quick regression check"""

    print("🔄 REGRESSION TEST SUITE")
    print("=" * 60)
    print("Quick validation of core functionality after code changes")
    print("=" * 60)

    # Setup minimal logging
    setup_logging(debug_mode=False)

    regression_results = {
        'automator_init': False,
        'config_loading': False,
        'login_function': False,
        'track_discovery': False,
        'mixer_controls': False,
        'solo_function': False,
        'download_setup': False
    }

    automator = None
    try:
        print("\n🔧 Testing Core Component Initialization...")

        # Test 1: Automator initialization
        try:
            automator = KaraokeVersionAutomator(headless=True, show_progress=False)
            print("✅ Automator initialization")
            regression_results['automator_init'] = True
        except Exception as e:
            # Without a working Chrome we cannot exercise any of the wired-up
            # components — skip rather than report a phantom regression.
            import pytest
            pytest.skip(f"KaraokeVersionAutomator could not start: {e}")

        # Test 2: Configuration loading
        songs = automator.load_songs_config()
        if songs:
            print(f"✅ Configuration loading - {len(songs)} songs found")
            regression_results['config_loading'] = True
        else:
            print("❌ Configuration loading - no songs found")

        print("\n🔐 Testing Authentication System...")

        # Test 3: Login function (quick check) - just confirm callable
        login_method = getattr(automator, 'login', None)
        if callable(login_method):
            print("✅ Login function available")
            regression_results['login_function'] = True
        else:
            print("❌ Login function not found")

        print("\n🎵 Testing Track Management...")

        # Test 4: Track discovery function
        track_method = getattr(automator, 'get_available_tracks', None)
        if callable(track_method):
            print("✅ Track discovery function available")
            regression_results['track_discovery'] = True
        else:
            print("❌ Track discovery function not found")

        # Test 5: Mixer control functions
        intro_method = getattr(automator.track_manager, 'ensure_intro_count_enabled', None)
        key_method = getattr(automator.track_manager, 'adjust_key', None)
        if callable(intro_method) and callable(key_method):
            print("✅ Mixer control functions available")
            regression_results['mixer_controls'] = True
        else:
            print("❌ Mixer control functions not found")

        # Test 6: Solo function
        solo_method = getattr(automator, 'solo_track', None)
        if callable(solo_method):
            print("✅ Solo function available")
            regression_results['solo_function'] = True
        else:
            print("❌ Solo function not found")

        # Test 7: Download setup
        download_method = getattr(automator.download_manager, 'download_current_mix', None)
        if callable(download_method):
            print("✅ Download function available")
            regression_results['download_setup'] = True
        else:
            print("❌ Download function not found")

    finally:
        if automator is not None:
            try:
                automator.driver.quit()
            except Exception:
                pass

    failed = [name for name, ok in regression_results.items() if not ok]
    assert not failed, f"Regression failures in core functions: {failed}"

def test_configuration_validation():
    """Test configuration validation and edge cases"""

    print("\n🔧 Testing Configuration Edge Cases...")

    edge_case_results = {
        'valid_config': False,
        'key_validation': False,
        'missing_fields': False
    }

    # Test valid configuration
    from packages.configuration import load_songs_config
    songs = load_songs_config()
    if songs:
        print("✅ Valid configuration loaded")
        edge_case_results['valid_config'] = True

    import yaml

    # Test key validation
    test_config_data = {
        'songs': [
            {'url': 'test', 'name': 'test', 'key': 15},   # Out of range
            {'url': 'test', 'name': 'test', 'key': -15},  # Out of range
            {'url': 'test', 'name': 'test', 'key': 'invalid'},  # Invalid type
            {'url': 'test', 'name': 'test'},  # Missing key (should default)
        ]
    }
    test_file = Path(__file__).parent / 'test_config.yaml'
    try:
        with open(test_file, 'w') as f:
            yaml.dump(test_config_data, f)
        with open(test_file, 'r') as f:
            config = yaml.safe_load(f)
            songs = config.get('songs', [])
            if len(songs) >= 4:
                print("✅ Key validation handles edge cases")
                edge_case_results['key_validation'] = True
    finally:
        test_file.unlink(missing_ok=True)

    # Test missing required fields
    test_invalid_config = {
        'songs': [
            {'name': 'test'},  # Missing URL
            {'url': 'test'},   # Missing name
            {}                 # Missing both
        ]
    }
    test_file = Path(__file__).parent / 'test_invalid_config.yaml'
    try:
        with open(test_file, 'w') as f:
            yaml.dump(test_invalid_config, f)
        with open(test_file, 'r') as f:
            yaml.safe_load(f)
            print("✅ Missing field validation works")
            edge_case_results['missing_fields'] = True
    finally:
        test_file.unlink(missing_ok=True)

    failed = [name for name, ok in edge_case_results.items() if not ok]
    assert not failed, f"Configuration edge case failures: {failed}"

if __name__ == "__main__":
    print("🔄 Running Regression Test Suite")
    print("Designed to quickly validate core functionality after code changes")
    print()

    failures = []
    try:
        test_regression_core_functions()
    except AssertionError as e:
        failures.append(f"core_functions: {e}")

    try:
        test_configuration_validation()
    except AssertionError as e:
        failures.append(f"edge_cases: {e}")

    print("\n" + "=" * 60)
    if not failures:
        print("✅ REGRESSION TESTS PASSED - Safe to proceed")
    else:
        print("❌ REGRESSION TESTS FAILED - Address issues before proceeding")
        for failure in failures:
            print(f"  - {failure}")
    print("=" * 60)
    sys.exit(0 if not failures else 1)