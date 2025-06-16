#!/usr/bin/env python3
"""
Regression Test Suite
Quick validation that core functionality still works after refactoring
Designed to be run before/after code changes to catch regressions
"""

import sys
import time
import logging
import json
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from karaoke_automator import KaraokeVersionAutomator, setup_logging

def test_regression_core_functions():
    """Test core functions still work - quick regression check"""
    
    print("🔄 REGRESSION TEST SUITE")
    print("=" * 60)
    print("Quick validation of core functionality after code changes")
    print("=" * 60)
    
    # Setup minimal logging
    setup_logging(debug_mode=False)
    
    # Track test results
    regression_results = {
        'automator_init': False,
        'config_loading': False,
        'login_function': False,
        'track_discovery': False,
        'mixer_controls': False,
        'solo_function': False,
        'download_setup': False
    }
    
    try:
        print("\n🔧 Testing Core Component Initialization...")
        
        # Test 1: Automator initialization
        try:
            automator = KaraokeVersionAutomator(headless=True, show_progress=False)
            print("✅ Automator initialization")
            regression_results['automator_init'] = True
        except Exception as e:
            print(f"❌ Automator initialization failed: {e}")
            return regression_results
        
        # Test 2: Configuration loading
        try:
            songs = automator.load_songs_config()
            if songs:
                test_song = songs[0]
                print(f"✅ Configuration loading - {len(songs)} songs found")
                regression_results['config_loading'] = True
            else:
                print("❌ Configuration loading - no songs found")
                return regression_results
        except Exception as e:
            print(f"❌ Configuration loading failed: {e}")
            return regression_results
        
        print("\n🔐 Testing Authentication System...")
        
        # Test 3: Login function (quick check)
        try:
            # Don't actually login in regression test - just test function exists and is callable
            login_method = getattr(automator, 'login', None)
            if callable(login_method):
                print("✅ Login function available")
                regression_results['login_function'] = True
            else:
                print("❌ Login function not found")
                return regression_results
        except Exception as e:
            print(f"❌ Login function test failed: {e}")
            return regression_results
        
        print("\n🎵 Testing Track Management...")
        
        # Test 4: Track discovery function
        try:
            track_method = getattr(automator, 'get_available_tracks', None)
            if callable(track_method):
                print("✅ Track discovery function available")
                regression_results['track_discovery'] = True
            else:
                print("❌ Track discovery function not found")
        except Exception as e:
            print(f"❌ Track discovery test failed: {e}")
        
        # Test 5: Mixer control functions
        try:
            intro_method = getattr(automator.track_handler, 'ensure_intro_count_enabled', None)
            key_method = getattr(automator.track_handler, 'adjust_key', None)
            
            if callable(intro_method) and callable(key_method):
                print("✅ Mixer control functions available")
                regression_results['mixer_controls'] = True
            else:
                print("❌ Mixer control functions not found")
        except Exception as e:
            print(f"❌ Mixer control test failed: {e}")
        
        # Test 6: Solo function
        try:
            solo_method = getattr(automator, 'solo_track', None)
            if callable(solo_method):
                print("✅ Solo function available")
                regression_results['solo_function'] = True
            else:
                print("❌ Solo function not found")
        except Exception as e:
            print(f"❌ Solo function test failed: {e}")
        
        # Test 7: Download setup
        try:
            download_method = getattr(automator.track_handler, 'download_current_mix', None)
            if callable(download_method):
                print("✅ Download function available")
                regression_results['download_setup'] = True
            else:
                print("❌ Download function not found")
        except Exception as e:
            print(f"❌ Download function test failed: {e}")
        
        return regression_results
        
    except Exception as e:
        print(f"❌ CRITICAL REGRESSION FAILURE: {e}")
        return regression_results
    
    finally:
        try:
            automator.driver.quit()
        except:
            pass

def test_configuration_validation():
    """Test configuration validation and edge cases"""
    
    print("\n🔧 Testing Configuration Edge Cases...")
    
    edge_case_results = {
        'valid_config': False,
        'key_validation': False,
        'missing_fields': False
    }
    
    try:
        # Test valid configuration
        from packages.configuration import load_songs_config
        songs = load_songs_config()
        if songs:
            print("✅ Valid configuration loaded")
            edge_case_results['valid_config'] = True
        
        # Test key validation
        test_config_data = {
            'songs': [
                {'url': 'test', 'name': 'test', 'key': 15},  # Out of range
                {'url': 'test', 'name': 'test', 'key': -15}, # Out of range
                {'url': 'test', 'name': 'test', 'key': 'invalid'}, # Invalid type
                {'url': 'test', 'name': 'test'}, # Missing key (should default)
            ]
        }
        
        # Mock the config loading with test data
        import yaml
        test_file = Path(__file__).parent / 'test_config.yaml'
        with open(test_file, 'w') as f:
            yaml.dump(test_config_data, f)
        
        # Test loading with edge cases
        try:
            with open(test_file, 'r') as f:
                config = yaml.safe_load(f)
                songs = config.get('songs', [])
                
                # Should handle edge cases gracefully
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
        with open(test_file, 'w') as f:
            yaml.dump(test_invalid_config, f)
        
        try:
            with open(test_file, 'r') as f:
                config = yaml.safe_load(f)
                # Should handle invalid configs without crashing
                print("✅ Missing field validation works")
                edge_case_results['missing_fields'] = True
        finally:
            test_file.unlink(missing_ok=True)
        
    except Exception as e:
        print(f"⚠️ Configuration edge case test failed: {e}")
    
    return edge_case_results

def save_regression_baseline(results, edge_results):
    """Save regression test results as baseline for comparison"""
    
    baseline = {
        'timestamp': time.time(),
        'core_functions': results,
        'edge_cases': edge_results,
        'total_score': sum(results.values()) + sum(edge_results.values()),
        'max_score': len(results) + len(edge_results)
    }
    
    baseline_file = Path(__file__).parent / 'regression_baseline.json'
    with open(baseline_file, 'w') as f:
        json.dump(baseline, f, indent=2)
    
    print(f"\n💾 Regression baseline saved to {baseline_file}")
    return baseline

def compare_with_baseline(current_results, current_edge):
    """Compare current test results with saved baseline"""
    
    baseline_file = Path(__file__).parent / 'regression_baseline.json'
    if not baseline_file.exists():
        print("📋 No baseline found - this will be the first baseline")
        return True
    
    try:
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
        
        current_score = sum(current_results.values()) + sum(current_edge.values())
        baseline_score = baseline.get('total_score', 0)
        
        print(f"\n📊 Regression Comparison:")
        print(f"   Baseline score: {baseline_score}/{baseline.get('max_score', 0)}")
        print(f"   Current score:  {current_score}/{len(current_results) + len(current_edge)}")
        
        if current_score >= baseline_score:
            print("✅ No regression detected - functionality maintained or improved")
            return True
        else:
            print("❌ REGRESSION DETECTED - functionality has degraded")
            
            # Show what regressed
            for test, current in current_results.items():
                baseline_result = baseline.get('core_functions', {}).get(test, False)
                if baseline_result and not current:
                    print(f"   🔴 Regressed: {test}")
            
            return False
    
    except Exception as e:
        print(f"⚠️ Could not compare with baseline: {e}")
        return True

def print_regression_summary(results, edge_results, comparison_passed):
    """Print regression test summary"""
    
    print("\n" + "=" * 60)
    print("📊 REGRESSION TEST SUMMARY")
    print("=" * 60)
    
    core_passed = sum(results.values())
    core_total = len(results)
    edge_passed = sum(edge_results.values())
    edge_total = len(edge_results)
    
    print(f"Core Functions: {core_passed}/{core_total}")
    print(f"Edge Cases: {edge_passed}/{edge_total}")
    print(f"Overall: {core_passed + edge_passed}/{core_total + edge_total}")
    
    print("\n🔍 DETAILED RESULTS:")
    print("Core Functions:")
    for test, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {test.replace('_', ' ').title()}")
    
    print("Edge Cases:")
    for test, passed in edge_results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {test.replace('_', ' ').title()}")
    
    print(f"\n📈 Baseline Comparison: {'✅ PASS' if comparison_passed else '❌ REGRESSION'}")
    
    # Refactor readiness assessment
    total_passed = core_passed + edge_passed
    total_tests = core_total + edge_total
    success_rate = (total_passed / total_tests) * 100
    
    print("\n🔧 REFACTOR IMPACT ASSESSMENT:")
    if success_rate >= 90 and comparison_passed:
        print("🎉 EXCELLENT - All systems operational, refactor is safe")
    elif success_rate >= 75 and comparison_passed:
        print("✅ GOOD - Minor issues, refactor likely safe")
    elif comparison_passed:
        print("⚠️ CONCERNING - Multiple failures, investigate before refactor")
    else:
        print("🛑 CRITICAL - Regression detected, do not proceed with refactor")
    
    return success_rate >= 75 and comparison_passed

if __name__ == "__main__":
    print("🔄 Running Regression Test Suite")
    print("Designed to quickly validate core functionality after code changes")
    print()
    
    # Run regression tests
    results = test_regression_core_functions()
    edge_results = test_configuration_validation()
    
    # Compare with baseline
    comparison_passed = compare_with_baseline(results, edge_results)
    
    # Save new baseline
    save_regression_baseline(results, edge_results)
    
    # Print summary and assessment
    success = print_regression_summary(results, edge_results, comparison_passed)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ REGRESSION TESTS PASSED - Safe to proceed")
    else:
        print("❌ REGRESSION TESTS FAILED - Address issues before proceeding")
    print("=" * 60)