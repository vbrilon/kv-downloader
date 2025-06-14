#!/usr/bin/env python3
"""
Test final features: headless mode and optimized login
Validates both new functionality additions
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator

def test_headless_mode():
    """Test headless browser mode functionality"""
    print("🔇 TESTING HEADLESS MODE")
    print("Browser should run hidden without visible window")
    print("="*60)
    
    try:
        # Test headless mode
        print("1️⃣ Initializing automator in headless mode...")
        automator_headless = KaraokeVersionAutomator(headless=True)
        
        print("2️⃣ Testing login in headless mode...")
        if not automator_headless.login():
            print("❌ Headless login failed")
            return False
        
        print("✅ Headless login successful!")
        
        # Test basic functionality in headless
        song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
        tracks = automator_headless.get_available_tracks(song_url)
        
        if tracks:
            print(f"✅ Track discovery works in headless mode: {len(tracks)} tracks found")
        else:
            print("❌ Track discovery failed in headless mode")
            return False
        
        print("🎉 Headless mode is fully functional!")
        return True
        
    except Exception as e:
        print(f"❌ Error in headless mode test: {e}")
        return False
    finally:
        try:
            automator_headless.driver.quit()
        except:
            pass

def test_visible_mode():
    """Test visible browser mode functionality"""
    print("\n👁️ TESTING VISIBLE MODE")
    print("Browser window should be visible")
    print("="*60)
    
    try:
        # Test visible mode
        print("1️⃣ Initializing automator in visible mode...")
        automator_visible = KaraokeVersionAutomator(headless=False)
        
        print("2️⃣ Testing login in visible mode...")
        if not automator_visible.login():
            print("❌ Visible login failed")
            return False
        
        print("✅ Visible login successful!")
        print("✅ Browser window should be visible for verification")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in visible mode test: {e}")
        return False
    finally:
        try:
            automator_visible.driver.quit() 
        except:
            pass

def test_optimized_login():
    """Test optimized login that skips if already logged in"""
    print("\n⚡ TESTING OPTIMIZED LOGIN")
    print("Should skip login process if already authenticated")
    print("="*60)
    
    try:
        # Initialize automator
        print("1️⃣ Initializing automator...")
        automator = KaraokeVersionAutomator(headless=False)  # Visible for verification
        
        # First login
        print("2️⃣ First login attempt...")
        start_time = time.time()
        if not automator.login():
            print("❌ First login failed")
            return False
        first_login_time = time.time() - start_time
        print(f"✅ First login successful in {first_login_time:.1f} seconds")
        
        # Second login (should be optimized/skipped)
        print("3️⃣ Second login attempt (should be optimized)...")
        start_time = time.time()
        if not automator.login():
            print("❌ Second login failed")
            return False
        second_login_time = time.time() - start_time
        print(f"✅ Second login completed in {second_login_time:.1f} seconds")
        
        # Compare times
        if second_login_time < first_login_time * 0.5:  # Should be much faster
            print(f"🚀 Login optimization working! {second_login_time:.1f}s vs {first_login_time:.1f}s")
            optimization_working = True
        else:
            print(f"⚠️ Login optimization may not be working: {second_login_time:.1f}s vs {first_login_time:.1f}s")
            optimization_working = False
        
        # Test force re-login
        print("4️⃣ Testing force re-login...")
        start_time = time.time()
        if not automator.login_handler.login(force_relogin=True):
            print("❌ Force re-login failed")
            return False
        force_login_time = time.time() - start_time
        print(f"✅ Force re-login completed in {force_login_time:.1f} seconds")
        
        return optimization_working
        
    except Exception as e:
        print(f"❌ Error in optimized login test: {e}")
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

def test_complete_workflow_with_features():
    """Test complete workflow using new features"""
    print("\n🎵 TESTING COMPLETE WORKFLOW WITH NEW FEATURES")
    print("Headless mode + optimized login + track isolation + download")
    print("="*60)
    
    try:
        # Use headless mode for production-like testing
        print("1️⃣ Initializing in headless mode for efficiency...")
        automator = KaraokeVersionAutomator(headless=True)
        
        # Optimized login
        print("2️⃣ Optimized login...")
        if not automator.login():
            print("❌ Login failed")
            return False
        
        # Test workflow
        song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
        tracks = automator.get_available_tracks(song_url)
        
        if not tracks:
            print("❌ No tracks found")
            return False
        
        print(f"✅ Found {len(tracks)} tracks in headless mode")
        
        # Find and solo bass track
        bass_tracks = [t for t in tracks if 'bass' in t['name'].lower()]
        if bass_tracks:
            bass_track = bass_tracks[0]
            print(f"3️⃣ Soloing bass track: {bass_track['name']}")
            
            if automator.solo_track(bass_track, song_url):
                print("✅ Bass track soloed successfully in headless mode")
                
                # Download test
                time.sleep(2)
                if automator.track_handler.download_current_mix(song_url, "headless_bass_test"):
                    print("✅ Download initiated successfully in headless mode")
                    workflow_success = True
                else:
                    print("❌ Download failed in headless mode")
                    workflow_success = False
            else:
                print("❌ Solo failed in headless mode")
                workflow_success = False
        else:
            print("❌ No bass track found")
            workflow_success = False
        
        if workflow_success:
            print("🎉 Complete workflow successful with new features!")
        
        return workflow_success
        
    except Exception as e:
        print(f"❌ Error in complete workflow test: {e}")
        return False
    finally:
        try:
            automator.driver.quit()
        except:
            pass

if __name__ == "__main__":
    print("🚀 TESTING FINAL FEATURES")
    print("Testing headless mode and optimized login functionality")
    print("="*60)
    
    # Test 1: Headless mode
    headless_success = test_headless_mode()
    
    # Test 2: Visible mode (brief)
    visible_success = test_visible_mode()
    
    # Test 3: Optimized login
    optimized_login_success = test_optimized_login()
    
    # Test 4: Complete workflow with features
    workflow_success = test_complete_workflow_with_features()
    
    print("\n" + "="*60)
    print("🏁 FINAL FEATURE TEST RESULTS:")
    print(f"Headless Mode: {'SUCCESS' if headless_success else 'FAILED'}")
    print(f"Visible Mode: {'SUCCESS' if visible_success else 'FAILED'}")
    print(f"Optimized Login: {'SUCCESS' if optimized_login_success else 'FAILED'}")
    print(f"Complete Workflow: {'SUCCESS' if workflow_success else 'FAILED'}")
    
    all_success = all([headless_success, visible_success, optimized_login_success, workflow_success])
    
    if all_success:
        print("🎉 ALL FINAL FEATURES WORKING PERFECTLY!")
        print("🚀 System is 100% complete and production-ready!")
    else:
        print("⚠️ Some features need attention")
    
    print("="*60)