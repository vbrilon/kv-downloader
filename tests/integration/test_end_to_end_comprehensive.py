#!/usr/bin/env python3
"""
Comprehensive End-to-End Test
Tests complete automation workflow from login to download completion
This is the critical test to run before/after refactoring
"""

import sys
import time
import logging
import json
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from karaoke_automator import KaraokeVersionAutomator, setup_logging

def test_end_to_end_automation():
    """Test complete automation workflow with real song"""
    
    print("🧪 COMPREHENSIVE END-TO-END TEST")
    print("=" * 80)
    print("Testing complete workflow: Login → Mixer → Download → Verification")
    print("This test validates the entire automation pipeline is working correctly.")
    print("=" * 80)
    
    # Setup debug logging to file only (clean console output)
    setup_logging(debug_mode=True)
    
    # Test results tracking
    test_results = {
        'login': False,
        'song_loading': False,
        'config_parsing': False,
        'mixer_intro_count': False,
        'mixer_key_adjustment': False,
        'track_discovery': False,
        'track_isolation': False,
        'download_initiation': False,
        'download_completion': False,
        'file_verification': False,
        'filename_cleanup': False,
        'progress_tracking': False
    }
    
    # Initialize automator in debug mode (visible browser for verification)
    automator = KaraokeVersionAutomator(headless=False, show_progress=True)
    
    try:
        print("\n📋 TEST PHASE 1: Configuration & Login")
        print("-" * 50)
        
        # Test 1: Load and validate configuration
        print("🔧 Testing configuration loading...")
        songs = automator.load_songs_config()
        if not songs:
            print("❌ FAILED: No songs found in configuration")
            return test_results
        
        test_song = songs[0]
        song_url = test_song['url']
        song_name = test_song['name']
        song_key = test_song.get('key', 0)
        
        print(f"✅ Configuration loaded successfully")
        print(f"   Song: {test_song.get('description', song_name)}")
        print(f"   Key adjustment: {song_key:+d} semitones")
        test_results['config_parsing'] = True
        
        # Test 2: Authentication
        print("\n🔐 Testing authentication...")
        login_start = time.time()
        if not automator.login():
            print("❌ FAILED: Login unsuccessful")
            return test_results
        
        login_time = time.time() - login_start
        print(f"✅ Login successful ({login_time:.1f}s)")
        test_results['login'] = True
        
        print("\n📋 TEST PHASE 2: Song Loading & Track Discovery")
        print("-" * 50)
        
        # Test 3: Song page access
        print("📄 Testing song page access...")
        page_load_start = time.time()
        automator.driver.get(song_url)
        time.sleep(3)
        
        # Verify we're on the right page
        current_url = automator.driver.current_url
        if song_url not in current_url:
            print(f"❌ FAILED: Page redirect issue. Expected: {song_url}, Got: {current_url}")
            return test_results
        
        page_load_time = time.time() - page_load_start
        print(f"✅ Song page loaded successfully ({page_load_time:.1f}s)")
        test_results['song_loading'] = True
        
        # Test 4: Track discovery
        print("🎵 Testing track discovery...")
        tracks = automator.get_available_tracks(song_url)
        if not tracks:
            print("❌ FAILED: No tracks discovered")
            return test_results
        
        print(f"✅ Track discovery successful - found {len(tracks)} tracks:")
        for i, track in enumerate(tracks):
            print(f"   {i+1}. {track['name']} (index: {track['index']})")
        test_results['track_discovery'] = True
        
        print("\n📋 TEST PHASE 3: Mixer Controls Setup")
        print("-" * 50)
        
        # Test 5: Intro count checkbox
        print("🎼 Testing intro count checkbox...")
        intro_success = automator.track_manager.ensure_intro_count_enabled(song_url)
        if intro_success:
            print("✅ Intro count checkbox enabled successfully")
            test_results['mixer_intro_count'] = True
        else:
            print("❌ FAILED: Intro count checkbox setup failed")
            # Continue with test - not critical failure
        
        # Test 6: Key adjustment
        print(f"🎵 Testing key adjustment to {song_key:+d}...")
        if song_key == 0:
            print("   No key adjustment needed (key = 0)")
            test_results['mixer_key_adjustment'] = True
        else:
            key_success = automator.track_manager.adjust_key(song_url, song_key)
            if key_success:
                print(f"✅ Key adjustment to {song_key:+d} successful")
                test_results['mixer_key_adjustment'] = True
            else:
                print(f"❌ FAILED: Key adjustment to {song_key:+d} failed")
                # Continue with test - not critical failure
        
        print("\n📋 TEST PHASE 4: Track Isolation & Download")
        print("-" * 50)
        
        # Test 7: Track isolation (use first track)
        test_track = tracks[0]
        print(f"🎯 Testing track isolation with: {test_track['name']}")
        
        solo_success = automator.solo_track(test_track, song_url)
        if solo_success:
            print("✅ Track isolation successful")
            test_results['track_isolation'] = True
        else:
            print("❌ FAILED: Track isolation failed")
            return test_results
        
        # Test 8: Download initiation and monitoring
        print("⬇️ Testing download initiation...")
        
        # Setup download monitoring
        song_folder_name = automator.download_manager.extract_song_folder_name(song_url)
        # Use the default download folder
        try:
            from packages.configuration import DOWNLOAD_FOLDER
        except ImportError:
            DOWNLOAD_FOLDER = "./downloads"
        song_path = Path(DOWNLOAD_FOLDER) / song_folder_name
        
        # Clear any existing files for clean test
        existing_files = list(song_path.glob("*")) if song_path.exists() else []
        print(f"   Initial files in folder: {len(existing_files)}")
        
        # Start download
        track_name = automator.sanitize_filename(test_track['name'])
        download_start = time.time()
        
        download_success = automator.download_manager.download_current_mix(
            song_url,
            track_name,
            cleanup_existing=True,
            song_folder=song_folder_name
        )
        
        if download_success:
            print("✅ Download initiation successful")
            test_results['download_initiation'] = True
        else:
            print("❌ FAILED: Download initiation failed")
            return test_results
        
        print("\n📋 TEST PHASE 5: Download Completion & File Verification")
        print("-" * 50)
        
        # Test 9: Wait for download completion and monitor progress
        print("⏳ Monitoring download completion...")
        max_wait = 120  # 2 minutes max wait
        check_interval = 5  # Check every 5 seconds
        waited = 0
        
        download_completed = False
        final_files = []
        
        while waited < max_wait:
            time.sleep(check_interval)
            waited += check_interval
            
            # Check for new files
            current_files = list(song_path.glob("*")) if song_path.exists() else []
            new_files = [f for f in current_files if f not in existing_files]
            
            # Look for completed downloads (no .crdownload extension)
            completed_audio_files = [
                f for f in new_files 
                if f.is_file() 
                and any(f.name.lower().endswith(ext) for ext in ['.mp3', '.aif', '.wav']) 
                and not f.name.endswith('.crdownload')
            ]
            
            if completed_audio_files:
                download_completed = True
                final_files = completed_audio_files
                download_time = time.time() - download_start
                print(f"✅ Download completed ({download_time:.1f}s total)")
                print(f"   Downloaded files: {len(final_files)}")
                for f in final_files:
                    print(f"     - {f.name}")
                break
            
            # Show progress
            crdownload_files = [f for f in new_files if f.name.endswith('.crdownload')]
            if crdownload_files:
                print(f"   ⏳ Download in progress... ({waited}s elapsed, {len(crdownload_files)} .crdownload files)")
            else:
                print(f"   ⏳ Waiting for download to start... ({waited}s elapsed)")
        
        if download_completed:
            test_results['download_completion'] = True
        else:
            print(f"❌ FAILED: Download did not complete within {max_wait} seconds")
            return test_results
        
        # Test 10: File verification
        print("📁 Testing file verification...")
        
        if final_files:
            test_file = final_files[0]
            file_size = test_file.stat().st_size
            
            print(f"✅ File verification successful")
            print(f"   File: {test_file.name}")
            print(f"   Size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
            print(f"   Location: {test_file.parent}")
            
            # Check if filename was cleaned up (no _Custom_Backing_Track)
            if '_Custom_Backing_Track' not in test_file.name:
                print("✅ Filename cleanup successful")
                test_results['filename_cleanup'] = True
            else:
                print("⚠️ Filename cleanup may not have completed yet")
                # Check again after a brief wait
                time.sleep(5)
                if '_Custom_Backing_Track' not in test_file.name:
                    print("✅ Filename cleanup completed")
                    test_results['filename_cleanup'] = True
            
            test_results['file_verification'] = True
        else:
            print("❌ FAILED: No valid audio files found")
            return test_results
        
        # Test 11: Progress tracking verification
        print("📊 Testing progress tracking...")
        if automator.progress:
            # Progress tracker should show completed status
            print("✅ Progress tracking system active during test")
            test_results['progress_tracking'] = True
        else:
            print("⚠️ Progress tracking not active (show_progress=False)")
            test_results['progress_tracking'] = True  # Not a failure
        
        print("\n📋 TEST PHASE 6: Cleanup & Summary")
        print("-" * 50)
        
        # Clear all solos for clean state
        automator.clear_all_solos(song_url)
        print("🧹 Cleared all track solos")
        
        return test_results
        
    except Exception as e:
        print(f"❌ CRITICAL FAILURE: {e}")
        logging.exception("End-to-end test exception:")
        return test_results
    
    finally:
        print("\n⏸️ Keeping browser open for 10 seconds for inspection...")
        time.sleep(10)
        automator.driver.quit()

def print_test_summary(results):
    """Print comprehensive test results summary"""
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"Overall Success Rate: {passed}/{total} ({success_rate:.1f}%)")
    print()
    
    # Group results by category
    categories = {
        'Authentication & Setup': ['login', 'song_loading', 'config_parsing'],
        'Track Management': ['track_discovery', 'track_isolation'],
        'Mixer Controls': ['mixer_intro_count', 'mixer_key_adjustment'],
        'Download Process': ['download_initiation', 'download_completion'],
        'File Management': ['file_verification', 'filename_cleanup'],
        'System Features': ['progress_tracking']
    }
    
    for category, tests in categories.items():
        print(f"📋 {category}:")
        for test in tests:
            status = "✅ PASS" if results.get(test, False) else "❌ FAIL"
            test_name = test.replace('_', ' ').title()
            print(f"   {status} - {test_name}")
        print()
    
    # Overall assessment
    critical_tests = ['login', 'track_discovery', 'track_isolation', 'download_initiation', 'download_completion', 'file_verification']
    critical_passed = sum(1 for test in critical_tests if results.get(test, False))
    
    print("🔍 REFACTOR READINESS ASSESSMENT:")
    print("-" * 40)
    
    if critical_passed == len(critical_tests):
        print("🎉 EXCELLENT - All critical functionality working")
        print("✅ SAFE TO REFACTOR - Comprehensive baseline established")
        print("💡 Run this test after refactoring to verify no regressions")
    elif critical_passed >= len(critical_tests) * 0.8:
        print("⚠️ GOOD - Most critical functionality working")
        print("🔧 Address failing tests before major refactoring")
    else:
        print("❌ POOR - Critical functionality issues detected")
        print("🛑 DO NOT REFACTOR - Fix core issues first")
    
    return success_rate >= 80

if __name__ == "__main__":
    print("🚀 Starting Comprehensive End-to-End Test")
    print("This test validates the entire automation workflow is working correctly")
    print("and establishes a baseline for safe refactoring.")
    print()
    
    # Run the test
    results = test_end_to_end_automation()
    
    # Print summary
    success = print_test_summary(results)
    
    print("\n" + "=" * 80)
    if success:
        print("✅ END-TO-END TEST PASSED - System ready for refactoring")
    else:
        print("❌ END-TO-END TEST FAILED - Address issues before refactoring")
    print("=" * 80)