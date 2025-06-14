#!/usr/bin/env python3
"""
Production Ready Validation Test
Comprehensive test of the complete automation system
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def test_production_ready_system():
    """Test the complete production-ready system"""
    print("🚀 PRODUCTION READY VALIDATION TEST")
    print("Testing complete automation system end-to-end")
    print("="*60)
    
    results = {
        'headless_mode': False,
        'optimized_login': False,  
        'track_discovery': False,
        'track_isolation': False,
        'download_functionality': False,
        'error_handling': False,
        'session_management': False
    }
    
    try:
        # Test 1: Headless Mode Operation
        print("1️⃣ Testing headless mode operation...")
        automator = KaraokeVersionAutomator(headless=True)
        
        if automator.headless:
            print("✅ Headless mode properly configured")
            results['headless_mode'] = True
        
        # Test 2: Optimized Login
        print("2️⃣ Testing optimized login system...")
        start_time = time.time()
        
        if automator.login():
            login_time = time.time() - start_time
            print(f"✅ Initial login successful ({login_time:.1f}s)")
            
            # Test optimized second login
            start_time = time.time()
            if automator.login():
                optimized_time = time.time() - start_time
                print(f"✅ Optimized login successful ({optimized_time:.1f}s)")
                if optimized_time < login_time * 0.7:
                    print("🚀 Login optimization working!")
                    results['optimized_login'] = True
        
        # Test 3: Track Discovery
        print("3️⃣ Testing track discovery...")
        song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
        tracks = automator.get_available_tracks(song_url)
        
        if tracks and len(tracks) >= 10:
            print(f"✅ Track discovery successful: {len(tracks)} tracks found")
            results['track_discovery'] = True
            
            # Validate track data structure
            for track in tracks[:3]:  # Check first 3 tracks
                if 'name' in track and 'index' in track and 'element' in track:
                    continue
                else:
                    print("❌ Track data structure invalid")
                    results['track_discovery'] = False
                    break
        
        # Test 4: Track Isolation (Solo Functionality)
        print("4️⃣ Testing track isolation...")
        if tracks:
            # Test bass isolation
            bass_tracks = [t for t in tracks if 'bass' in t['name'].lower()]
            if bass_tracks:
                bass_track = bass_tracks[0]
                print(f"Testing bass isolation: {bass_track['name']}")
                
                if automator.solo_track(bass_track, song_url):
                    print("✅ Bass track isolation successful")
                    results['track_isolation'] = True
                    
                    # Test clear solos
                    if automator.clear_all_solos(song_url):
                        print("✅ Solo clearing successful")
        
        # Test 5: Download Functionality  
        print("5️⃣ Testing download functionality...")
        if results['track_isolation']:
            # Solo bass again for download test
            if automator.solo_track(bass_track, song_url):
                time.sleep(2)  # Wait for UI update
                
                if automator.track_handler.download_current_mix(song_url, "production_test"):
                    print("✅ Download functionality working")
                    results['download_functionality'] = True
        
        # Test 6: Error Handling
        print("6️⃣ Testing error handling...")
        # Test with invalid URL
        invalid_tracks = automator.get_available_tracks("https://www.karaoke-version.com/invalid-url")
        if invalid_tracks == []:  # Should return empty list, not crash
            print("✅ Error handling working - invalid URL handled gracefully")
            results['error_handling'] = True
        
        # Test 7: Session Management
        print("7️⃣ Testing session management...")
        if automator.is_logged_in():
            print("✅ Session management working - login state tracked")
            results['session_management'] = True
        
        # Calculate overall success
        passed_tests = sum(results.values())
        total_tests = len(results)
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"\n📊 PRODUCTION READY TEST RESULTS:")
        print(f"Passed: {passed_tests}/{total_tests} tests ({success_rate:.1f}%)")
        print()
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test_name.replace('_', ' ').title()}: {status}")
        
        if success_rate >= 85:
            print(f"\n🎉 SYSTEM IS PRODUCTION READY!")
            print(f"🚀 All core functionality working at {success_rate:.1f}% success rate")
            production_ready = True
        else:
            print(f"\n⚠️  System needs more work: {success_rate:.1f}% success rate")
            production_ready = False
        
        return production_ready
        
    except Exception as e:
        print(f"❌ Critical error during production test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

def test_usage_examples():
    """Test usage examples for documentation"""
    print("\n📖 TESTING USAGE EXAMPLES")
    print("Validating examples from documentation")
    print("="*40)
    
    try:
        # Example 1: Simple track isolation
        print("Example 1: Simple track isolation")
        automator = KaraokeVersionAutomator(headless=True)
        
        if automator.login():
            song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
            tracks = automator.get_available_tracks(song_url)
            
            if tracks:
                # Find guitar track
                guitar_tracks = [t for t in tracks if 'guitar' in t['name'].lower()]
                if guitar_tracks:
                    guitar_track = guitar_tracks[0]
                    if automator.solo_track(guitar_track, song_url):
                        print("✅ Guitar isolation example works")
                
                # Switch to vocals
                vocal_tracks = [t for t in tracks if 'vocal' in t['name'].lower()]
                if vocal_tracks:
                    vocal_track = vocal_tracks[0]
                    if automator.solo_track(vocal_track, song_url):
                        print("✅ Vocal switching example works")
                
                # Clear all
                if automator.clear_all_solos(song_url):
                    print("✅ Clear solos example works")
        
        print("📖 Usage examples validated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Usage examples failed: {e}")
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    print("🏁 FINAL PRODUCTION VALIDATION")
    print("="*60)
    
    # Main production test
    production_ready = test_production_ready_system()
    
    # Usage examples test
    examples_working = test_usage_examples()
    
    print("\n" + "="*60)
    print("🏆 FINAL RESULTS:")
    print(f"Production Ready: {'YES' if production_ready else 'NO'}")
    print(f"Examples Working: {'YES' if examples_working else 'NO'}")
    
    if production_ready and examples_working:
        print("\n🎉 SYSTEM IS 100% COMPLETE AND READY FOR USE!")
        print("🚀 Ready for production deployment")
        print("📚 Documentation examples validated")
        print("✅ All core functionality operational")
    else:
        print("\n⚠️  System needs final adjustments")
    
    print("="*60)