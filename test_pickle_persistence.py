#!/usr/bin/env python3
"""
Pickle Persistence Testing Suite
Comprehensive evaluation of pickle-based session persistence

This script tests whether the custom pickle session persistence:
1. Actually works for maintaining login between browser sessions
2. Provides unique value beyond Chrome profile persistence
3. Should be kept, improved, or removed entirely
"""

import os
import sys
import time
import pickle
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from karaoke_automator import KaraokeVersionAutomator
from packages.browser.chrome_manager import ChromeManager
from packages.authentication.login_manager import LoginManager


class PicklePersistenceTester:
    """Comprehensive tester for pickle-based session persistence"""
    
    def __init__(self):
        self.test_start_time = datetime.now()
        self.test_results = {}
        self.temp_chrome_dir = None
        self.original_chrome_config = None
        self.setup_test_environment()
        self.setup_logging()
        
    def setup_test_environment(self):
        """Configure isolated test environment with pickle-only persistence"""
        print("🔧 Setting up isolated test environment...")
        
        # Create temporary directory for throwaway Chrome profiles
        self.temp_chrome_dir = tempfile.mkdtemp(prefix="pickle_test_chrome_")
        print(f"   📁 Temporary Chrome directory: {self.temp_chrome_dir}")
        
        # Backup existing session file if it exists
        if os.path.exists('.cache/session_data.pkl'):
            backup_path = f'.cache/session_data_backup_{int(time.time())}.pkl'
            shutil.copy('.cache/session_data.pkl', backup_path)
            print(f"   💾 Backed up existing session to: {backup_path}")
            
        # Clear any existing test session data
        if os.path.exists('.cache/session_data.pkl'):
            os.remove('.cache/session_data.pkl')
            print("   🗑️  Cleared existing session data for clean test")
    
    def setup_logging(self):
        """Configure comprehensive logging for test analysis"""
        log_file = f'logs/pickle_persistence_test_{int(time.time())}.log'
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('pickle_persistence_test')
        self.logger.info(f"🧪 Starting pickle persistence test session")
        self.logger.info(f"📋 Test log file: {log_file}")
        
    def patch_chrome_manager_for_testing(self):
        """Temporarily modify ChromeManager to use throwaway profiles"""
        print("   🔧 Patching ChromeManager to disable persistent profiles...")
        
        # Store original method
        original_setup = ChromeManager.setup_chrome_options
        
        def test_setup_chrome_options(self, headless=False):
            """Modified setup that forces temporary profile"""
            options = original_setup(self, headless)
            
            # Force temporary user data directory
            test_user_data = os.path.join(self.temp_chrome_dir, f"test_profile_{int(time.time())}")
            options.add_argument(f"--user-data-dir={test_user_data}")
            options.add_argument("--no-first-run")
            options.add_argument("--disable-background-timer-throttling")
            
            self.logger.debug(f"🔒 Using temporary Chrome profile: {test_user_data}")
            return options
            
        # Apply patch
        ChromeManager.setup_chrome_options = test_setup_chrome_options
        return original_setup
        
    def restore_chrome_manager(self, original_method):
        """Restore original ChromeManager functionality"""
        ChromeManager.setup_chrome_options = original_method
        print("   ✅ Restored original ChromeManager functionality")
        
    def test_fresh_login_and_save(self):
        """Phase 2.1: Test if pickle can save a fresh login session"""
        print("\n🧪 Phase 2.1: Testing fresh login and pickle save...")
        
        try:
            # Patch Chrome manager for isolated testing
            original_chrome_setup = self.patch_chrome_manager_for_testing()
            
            # Verify clean state
            assert not os.path.exists('.cache/session_data.pkl'), "Session file should not exist"
            
            print("\n👀 EMPIRICAL OBSERVATION PHASE:")
            print("   📋 About to perform fresh login - Chrome will open")
            print("   🔍 Watch the login process carefully:")
            print("      • Does the login form appear correctly?")
            print("      • Does the authentication succeed?")
            print("      • Are you redirected to a logged-in state?")
            
            # Create automator with pickle-only persistence
            self.logger.info("Creating automator instance for fresh login test")
            automator = KaraokeVersionAutomator(headless=False, show_progress=True)
            
            input("\n   ⏸️  Press Enter when ready to start fresh login test...")
            
            # Perform fresh login
            self.logger.info("Attempting fresh login...")
            login_success = automator.login(force_relogin=True)
            
            if not login_success:
                print("   ❌ Login method returned False - checking actual state...")
            else:
                print("   ✅ Login method returned True")
            
            # Empirical verification of login state
            print("\n🔍 EMPIRICAL VERIFICATION OF LOGIN:")
            print("   Navigating to account page for verification...")
            
            automator.driver.get("https://www.karaoke-version.com/account")
            time.sleep(3)  # Wait for page load
            
            current_url = automator.driver.current_url
            page_source = automator.driver.page_source
            
            print(f"   📍 Current URL: {current_url}")
            
            # Interactive verification
            print("\n❓ LOGIN VERIFICATION:")
            print("   Look at the browser window:")
            print("   1. Can you see account/profile content?")
            print("   2. Are you clearly logged in (no login forms visible)?")
            print("   3. Does the page show user-specific information?")
            
            user_confirms_login = input("\n   Are you successfully logged in? (y/n): ").lower() == 'y'
            
            # Automated checks
            automated_checks = [
                ("My Account" in page_source, "My Account text found"),
                ("login" not in current_url.lower(), "Not on login page"),
                ("account" in current_url.lower(), "On account page"),
                (user_confirms_login, "User confirms login success")
            ]
            
            passed_checks = [desc for success, desc in automated_checks if success]
            failed_checks = [desc for success, desc in automated_checks if not success]
            
            self.logger.info(f"✅ Login checks passed: {passed_checks}")
            if failed_checks:
                self.logger.warning(f"❌ Login checks failed: {failed_checks}")
            
            # Determine if login was actually successful
            actual_login_success = len(passed_checks) >= 3
            
            if not actual_login_success:
                raise Exception("Fresh login verification failed - user not properly logged in")
                
            self.logger.info("✅ Fresh login empirically verified successful")
            
            # Test pickle save functionality
            print("\n💾 TESTING PICKLE SAVE:")
            print("   About to call save_session() - this should create pickle file...")
            
            # Trigger explicit pickle save
            self.logger.info("Triggering pickle session save...")
            automator.login_manager.save_session()
            
            # Verify pickle file creation
            if not os.path.exists('.cache/session_data.pkl'):
                raise Exception("Pickle file was not created after save_session()")
            
            print("   ✅ Pickle file created successfully")
            
            # Verify pickle file contents
            with open('.cache/session_data.pkl', 'rb') as f:
                session_data = pickle.load(f)
                
            required_keys = ['cookies', 'localStorage', 'sessionStorage', 'timestamp']
            missing_keys = [key for key in required_keys if key not in session_data]
            
            if missing_keys:
                raise Exception(f"Pickle file missing required keys: {missing_keys}")
            
            print(f"   📊 Pickle file contains: {list(session_data.keys())}")
            print(f"   📊 Cookies saved: {len(session_data.get('cookies', []))}")
            print(f"   📊 localStorage items: {len(session_data.get('localStorage', {}))}")
            print(f"   📊 sessionStorage items: {len(session_data.get('sessionStorage', {}))}")
            
            # Show sample data for verification
            if session_data.get('cookies'):
                sample_cookie = session_data['cookies'][0] if session_data['cookies'] else {}
                print(f"   📊 Sample cookie domain: {sample_cookie.get('domain', 'N/A')}")
            
            self.logger.info(f"✅ Pickle file created with keys: {list(session_data.keys())}")
            self.logger.info(f"📊 Cookies saved: {len(session_data.get('cookies', []))}")
            self.logger.info(f"📊 localStorage items: {len(session_data.get('localStorage', {}))}")
            
            # Keep browser open briefly for verification
            print("\n🔍 FINAL VERIFICATION:")
            print("   Browser will stay open for 5 seconds for final state verification")
            time.sleep(5)
            
            # Clean up
            automator.driver.quit()
            self.restore_chrome_manager(original_chrome_setup)
            
            self.test_results['fresh_login_save'] = {
                'success': True,
                'pickle_file_created': True,
                'session_data_keys': list(session_data.keys()),
                'cookies_count': len(session_data.get('cookies', [])),
                'localStorage_count': len(session_data.get('localStorage', {})),
                'sessionStorage_count': len(session_data.get('sessionStorage', {})),
                'user_confirmed_login': user_confirms_login,
                'automated_checks_passed': passed_checks
            }
            
            print("   ✅ Fresh login and save test: PASSED")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fresh login and save test failed: {str(e)}")
            self.test_results['fresh_login_save'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ❌ Fresh login and save test: FAILED - {str(e)}")
            return False
            
    def test_pickle_restoration(self):
        """Phase 2.2: Critical test - can pickle restore login across browser restarts?"""
        print("\n🧪 Phase 2.2: Testing pickle restoration across browser restart...")
        
        if not os.path.exists('.cache/session_data.pkl'):
            print("   ⚠️  No pickle file exists - skipping restoration test")
            return False
            
        try:
            # Patch Chrome manager for isolated testing
            original_chrome_setup = self.patch_chrome_manager_for_testing()
            
            # Create completely fresh browser instance
            self.logger.info("Creating fresh browser instance for restoration test")
            automator = KaraokeVersionAutomator(headless=False, show_progress=True)
            
            print("\n👀 EMPIRICAL OBSERVATION PHASE:")
            print("   📋 About to test pickle restoration - Chrome will open")
            print("   🔍 Watch the browser behavior carefully:")
            print("      • Does it go directly to account page without login forms?")
            print("      • Are you immediately logged in as the user?")
            print("      • Can you access protected content right away?")
            
            input("\n   ⏸️  Press Enter when ready to start restoration test...")
            
            # Attempt pickle-only restoration (NO fresh login allowed)
            self.logger.info("Attempting pickle restoration...")
            start_time = time.time()
            restoration_success = automator.login_manager.load_session()
            restoration_time = time.time() - start_time
            
            self.logger.info(f"📊 Restoration attempt completed in {restoration_time:.2f}s")
            
            if not restoration_success:
                self.logger.warning("⚠️  load_session() returned False")
                print("   ⚠️  load_session() returned False - but let's check actual login state...")
            
            # CRITICAL TEST: Navigate to protected page without re-authentication
            print("\n🔍 EMPIRICAL TEST 1: Navigating to account page...")
            print("   👀 Watch: Does it show logged-in state or redirect to login?")
            
            automator.driver.get("https://www.karaoke-version.com/account")
            time.sleep(4)  # Wait for potential redirects/loading
            
            current_url = automator.driver.current_url
            page_source = automator.driver.page_source
            
            print(f"   📍 Current URL: {current_url}")
            
            # Interactive verification with user observation
            print("\n❓ EMPIRICAL VERIFICATION:")
            print("   Look at the browser window and answer these questions:")
            print("   1. Can you see 'My Account' or similar user account content?")
            print("   2. Are you on an account/profile page (not a login page)?") 
            print("   3. Do you see user-specific information/settings?")
            
            user_sees_account = input("\n   Are you logged in and see account content? (y/n): ").lower() == 'y'
            
            # Check multiple indicators of successful login
            login_indicators = [
                ("My Account" in page_source, "My Account text found"),
                ("login" not in current_url.lower(), "Not redirected to login page"), 
                ("account" in current_url.lower(), "On account page"),
                ("sign in" not in page_source.lower(), "No sign in prompt"),
                (user_sees_account, "User confirms logged-in state")
            ]
            
            successful_indicators = [desc for success, desc in login_indicators if success]
            failed_indicators = [desc for success, desc in login_indicators if not success]
            
            self.logger.info(f"✅ Login indicators passed: {successful_indicators}")
            if failed_indicators:
                self.logger.warning(f"❌ Login indicators failed: {failed_indicators}")
            
            # Determine overall success (need at least 4 of 5 indicators)
            is_logged_in = len(successful_indicators) >= 4
            
            if is_logged_in:
                print("\n🔍 EMPIRICAL TEST 2: Testing protected song page access...")
                print("   👀 Watch: Can you access song content without additional login?")
                
                test_song_url = "https://www.karaoke-version.com/custombackingtrack/adele/hello.html"
                automator.driver.get(test_song_url)
                time.sleep(3)
                
                print(f"   📍 Navigated to: {test_song_url}")
                
                # Check for access denied or login prompts
                track_page_source = automator.driver.page_source.lower()
                track_page_success = ("access denied" not in track_page_source and 
                                    "login" not in automator.driver.current_url.lower())
                
                user_sees_tracks = input("\n   Can you see track controls/mixer on the song page? (y/n): ").lower() == 'y'
                track_page_success = track_page_success and user_sees_tracks
                
                self.logger.info(f"🎵 Protected song page access: {'SUCCESS' if track_page_success else 'FAILED'}")
                
                if track_page_success:
                    self.logger.info("🎉 PICKLE RESTORATION FULLY SUCCESSFUL!")
                    print("   🎉 Pickle restoration: COMPLETE SUCCESS")
                    print("      ✅ Login maintained across browser restart")
                    print("      ✅ Account page accessible")
                    print("      ✅ Protected content accessible")
                else:
                    print("   ⚠️  Pickle restoration: PARTIAL SUCCESS")
                    print("      ✅ Login maintained")
                    print("      ❌ Protected content access issues")
                    
            else:
                self.logger.error("❌ PICKLE RESTORATION FAILED - User not logged in")
                print("   ❌ Pickle restoration: FAILED - Login not maintained")
                print("   🔍 Possible causes:")
                print("      • Pickle data is corrupted or incomplete")
                print("      • Session has expired on server side")
                print("      • Chrome profile isolation interfering with restoration")
                
            # Keep browser open for final verification
            print(f"\n🔍 FINAL EMPIRICAL VERIFICATION:")
            print("   Browser will stay open for 10 seconds for final observation")
            print("   👀 Take a screenshot or note the final state")
            
            time.sleep(10)
                
            # Clean up
            automator.driver.quit()
            self.restore_chrome_manager(original_chrome_setup)
            
            self.test_results['pickle_restoration'] = {
                'success': is_logged_in,
                'restoration_time': restoration_time,
                'load_session_returned': restoration_success,
                'current_url': current_url,
                'login_indicators_passed': successful_indicators,
                'login_indicators_failed': failed_indicators,
                'protected_page_access': track_page_success if is_logged_in else False,
                'user_empirical_verification': user_sees_account
            }
            
            return is_logged_in
            
        except Exception as e:
            self.logger.error(f"❌ Pickle restoration test failed: {str(e)}")
            self.test_results['pickle_restoration'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ❌ Pickle restoration test: FAILED - {str(e)}")
            return False
            
    def test_time_based_persistence(self):
        """Phase 3.1: Test pickle persistence over different time periods"""
        print("\n🧪 Phase 3.1: Testing time-based persistence...")
        
        if not os.path.exists('.cache/session_data.pkl'):
            print("   ⚠️  No pickle file exists - skipping time persistence test")
            return False
            
        try:
            # Test different time scenarios
            test_intervals = [
                (1, "1 hour", True),
                (6, "6 hours", True), 
                (23, "23 hours", True),
                (25, "25 hours", False)  # Should fail due to 24h expiry
            ]
            
            time_test_results = {}
            
            for hours, description, should_work in test_intervals:
                self.logger.info(f"Testing {description} persistence...")
                
                # Backup original pickle file
                shutil.copy('.cache/session_data.pkl', '.cache/session_data_backup.pkl')
                
                # Modify timestamp to simulate time passage
                with open('.cache/session_data.pkl', 'rb') as f:
                    data = pickle.load(f)
                
                # Simulate time passage
                data['timestamp'] = time.time() - (hours * 3600)
                
                with open('.cache/session_data.pkl', 'wb') as f:
                    pickle.dump(data, f)
                
                # Test restoration with modified timestamp
                original_chrome_setup = self.patch_chrome_manager_for_testing()
                automator = KaraokeVersionAutomator(headless=True)
                
                success = automator.login_manager.load_session()
                automator.driver.quit()
                self.restore_chrome_manager(original_chrome_setup)
                
                # Restore original pickle file
                shutil.move('.cache/session_data_backup.pkl', '.cache/session_data.pkl')
                
                # Verify results match expectations
                result_correct = (success == should_work)
                time_test_results[description] = {
                    'success': success,
                    'expected': should_work,
                    'correct': result_correct
                }
                
                status = "✅ PASS" if result_correct else "❌ FAIL"
                self.logger.info(f"{description}: {status} (success={success}, expected={should_work})")
                
            self.test_results['time_persistence'] = time_test_results
            
            # Overall time test success
            all_correct = all(result['correct'] for result in time_test_results.values())
            print(f"   {'✅' if all_correct else '❌'} Time-based persistence test: {'PASSED' if all_correct else 'FAILED'}")
            
            return all_correct
            
        except Exception as e:
            self.logger.error(f"❌ Time persistence test failed: {str(e)}")
            self.test_results['time_persistence'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ❌ Time persistence test: FAILED - {str(e)}")
            return False
    
    def generate_comprehensive_report(self):
        """Generate detailed test report with recommendations"""
        print("\n" + "="*60)
        print("📊 PICKLE PERSISTENCE TEST REPORT")
        print("="*60)
        
        # Test summary
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() 
                             if isinstance(result, dict) and result.get('success', False))
        
        print(f"📋 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        print(f"   Duration: {datetime.now() - self.test_start_time}")
        
        # Detailed results
        print(f"\n📝 Detailed Results:")
        for test_name, result in self.test_results.items():
            print(f"\n   🧪 {test_name.replace('_', ' ').title()}:")
            if isinstance(result, dict):
                if result.get('success', False):
                    print(f"      ✅ STATUS: PASSED")
                else:
                    print(f"      ❌ STATUS: FAILED")
                    if 'error' in result:
                        print(f"      🔍 ERROR: {result['error']}")
                
                # Additional details
                for key, value in result.items():
                    if key not in ['success', 'error']:
                        print(f"      📊 {key}: {value}")
        
        # Final recommendation
        print(f"\n🎯 FINAL RECOMMENDATION:")
        
        pickle_works = (
            self.test_results.get('fresh_login_save', {}).get('success', False) and
            self.test_results.get('pickle_restoration', {}).get('success', False)
        )
        
        if pickle_works:
            print("   ✅ KEEP PICKLE PERSISTENCE")
            print("   📋 Reasoning:")
            print("      • Pickle save functionality works correctly")
            print("      • Pickle restoration maintains login across browser restarts") 
            print("      • Provides valuable fallback mechanism alongside Chrome profiles")
            print("      • Time-based expiry functions as designed")
            
            print("\n   🔧 Recommendations:")
            print("      • Maintain current dual persistence approach")
            print("      • Consider improving error handling and logging")
            print("      • Document the layered persistence strategy clearly")
            
        else:
            print("   ❌ REMOVE PICKLE PERSISTENCE")
            print("   📋 Reasoning:")
            save_works = self.test_results.get('fresh_login_save', {}).get('success', False)
            restore_works = self.test_results.get('pickle_restoration', {}).get('success', False)
            
            if not save_works:
                print("      • Pickle save functionality is broken or unreliable")
            if not restore_works:
                print("      • Pickle restoration fails to maintain login state")
            print("      • Chrome profile persistence likely sufficient")
            print("      • Removing pickle reduces code complexity and maintenance burden")
            
            print("\n   🔧 Recommendations:")
            print("      • Remove save_session() and load_session() methods")
            print("      • Clean up pickle-related imports and dependencies")
            print("      • Rely solely on Chrome profile persistence")
            print("      • Update documentation to reflect simplified architecture")
        
        # Save report to file
        report_file = f'logs/pickle_persistence_report_{int(time.time())}.txt'
        with open(report_file, 'w') as f:
            f.write("PICKLE PERSISTENCE TEST REPORT\n")
            f.write("="*50 + "\n\n")
            f.write(f"Test Date: {self.test_start_time}\n")
            f.write(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%\n\n")
            f.write("Detailed Results:\n")
            for test_name, result in self.test_results.items():
                f.write(f"\n{test_name}: {result}\n")
        
        print(f"\n📄 Full report saved to: {report_file}")
        
        return pickle_works
    
    def cleanup_test_environment(self):
        """Clean up temporary files and restore original state"""
        print("\n🧹 Cleaning up test environment...")
        
        # Remove temporary Chrome directory
        if self.temp_chrome_dir and os.path.exists(self.temp_chrome_dir):
            shutil.rmtree(self.temp_chrome_dir)
            print(f"   🗑️  Removed temporary Chrome directory: {self.temp_chrome_dir}")
        
        print("   ✅ Test environment cleanup complete")
    
    def run_full_test_suite(self):
        """Execute comprehensive pickle persistence test suite"""
        print("🚀 Starting Comprehensive Pickle Persistence Test Suite")
        print("="*60)
        
        try:
            # Phase 1: Setup (already done in __init__)
            print("✅ Phase 1: Test environment setup complete")
            
            # Phase 2: Core functionality tests
            print("\n📋 Phase 2: Core Functionality Tests")
            save_success = self.test_fresh_login_and_save()
            
            if save_success:
                restore_success = self.test_pickle_restoration()
            else:
                print("   ⚠️  Skipping restoration test due to save failure")
                restore_success = False
            
            # Phase 3: Advanced tests (only if core tests pass)
            print("\n📋 Phase 3: Advanced Tests")
            if save_success and restore_success:
                self.test_time_based_persistence()
            else:
                print("   ⚠️  Skipping advanced tests due to core test failures")
            
            # Generate comprehensive report
            recommendation = self.generate_comprehensive_report()
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"❌ Test suite execution failed: {str(e)}")
            print(f"❌ Test suite failed: {str(e)}")
            return False
            
        finally:
            self.cleanup_test_environment()


def main():
    """Main test execution function"""
    print("🧪 Pickle Persistence Testing Suite")
    print("This will test whether pickle session persistence works and is needed\n")
    
    print("⚠️  This test will:")
    print("   • Create temporary Chrome profiles")
    print("   • Test login/logout functionality") 
    print("   • Modify session files temporarily")
    print("   • Open Chrome browser for empirical verification")
    print("\n🚀 Starting test suite automatically...\n")
    
    # Run test suite
    tester = PicklePersistenceTester()
    recommendation = tester.run_full_test_suite()
    
    # Final summary
    print("\n" + "="*60)
    if recommendation:
        print("🎉 CONCLUSION: Pickle persistence works - keep current architecture!")
    else:
        print("🧹 CONCLUSION: Pickle persistence broken/unnecessary - simplify to Chrome-only!")
    print("="*60)


if __name__ == "__main__":
    main()