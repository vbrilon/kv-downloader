#!/usr/bin/env python3
"""
Unit tests for session persistence functionality
Tests login session saving and restoration
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.authentication.login_manager import LoginManager


def test_session_persistence_logic():
    """Test session persistence logic without real browser"""
    print("🧪 TESTING SESSION PERSISTENCE LOGIC")
    print("="*60)
    
    # Create temporary session file
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as temp_file:
        session_file = temp_file.name
    
    try:
        # Mock driver and wait
        mock_driver = Mock()
        mock_wait = Mock()
        
        # Create login manager with temp session file
        login_manager = LoginManager(mock_driver, mock_wait, session_file)
        
        # Test 1: No session file exists initially
        print("1️⃣ Testing initial state (no session)...")
        assert not login_manager.is_session_valid(), "Should have no valid session initially"
        assert not login_manager.load_session(), "Should not be able to load non-existent session"
        print("✅ No session initially - correct")
        
        # Test 2: Session file operations
        print("\n2️⃣ Testing session file operations...")
        
        # Mock successful session save
        mock_driver.get_cookies.return_value = [{'name': 'test_cookie', 'value': 'test_value'}]
        mock_driver.current_url = 'https://www.karaoke-version.com/test'
        mock_driver.execute_script.side_effect = lambda script: {
            "return navigator.userAgent": "test-agent",
            "return window.localStorage;": {'test_key': 'test_value'},
            "return window.sessionStorage;": {}
        }.get(script, None)
        mock_driver.get_window_size.return_value = {'width': 1920, 'height': 1080}
        
        # Save session
        save_result = login_manager.save_session()
        print(f"Session save result: {save_result}")
        assert save_result, "Session save should succeed"
        
        # Check session file exists
        session_path = Path(session_file)
        assert session_path.exists(), "Session file should exist after save"
        print("✅ Session file created successfully")
        
        # Test 3: Session validity check
        print("\n3️⃣ Testing session validity...")
        assert login_manager.is_session_valid(), "Session should be valid immediately after save"
        print("✅ Session validity check works")
        
        # Test 4: Session age simulation
        print("\n4️⃣ Testing session age limits...")
        
        # Manually modify session to be old
        import pickle
        with open(session_file, 'rb') as f:
            session_data = pickle.load(f)
        
        # Make session 25 hours old (should be too old)
        session_data['timestamp'] = time.time() - (25 * 60 * 60)
        
        with open(session_file, 'wb') as f:
            pickle.dump(session_data, f)
        
        assert not login_manager.is_session_valid(), "Old session should be invalid"
        print("✅ Old session correctly identified as invalid")
        
        # Test 5: Clear session
        print("\n5️⃣ Testing session clearing...")
        clear_result = login_manager.clear_session()
        assert clear_result, "Session clear should succeed"
        assert not session_path.exists(), "Session file should be deleted after clear"
        print("✅ Session clearing works correctly")

        print("\n🎉 ALL SESSION PERSISTENCE TESTS PASSED!")

    finally:
        # Clean up temp file if it still exists
        try:
            Path(session_file).unlink()
        except FileNotFoundError:
            pass


def test_session_workflow():
    """Test the complete session workflow logic"""
    print("\n🔄 TESTING COMPLETE SESSION WORKFLOW")
    print("="*60)

    # Create temporary session file
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as temp_file:
        session_file = temp_file.name

    try:
        # Mock everything needed
        mock_driver = Mock()
        mock_wait = Mock()

        login_manager = LoginManager(mock_driver, mock_wait, session_file)

        # login_with_session_persistence first checks Chrome's native session via
        # is_logged_in(); only if that fails does it fall back to fresh login().
        login_manager.login = Mock(return_value=True)
        login_manager.is_logged_in = Mock(return_value=False)
        # save_session is invoked when native session is detected; stub it out so
        # the pickle path on the mocked driver is not exercised.
        login_manager.save_session = Mock(return_value=True)

        print("1️⃣ Testing first login (no native session, no saved session)...")
        result1 = login_manager.login_with_session_persistence()
        assert result1, "First login should succeed"
        login_manager.login.assert_called_once()
        # is_logged_in is consulted before falling back to fresh login.
        login_manager.is_logged_in.assert_called_once()
        print("✅ Fresh login performed correctly")

        print("\n2️⃣ Testing native Chrome session shortcut...")
        login_manager.login.reset_mock()
        login_manager.save_session.reset_mock()
        login_manager.is_logged_in = Mock(return_value=True)

        result2 = login_manager.login_with_session_persistence()
        assert result2, "Native session shortcut should succeed"
        login_manager.login.assert_not_called()
        login_manager.save_session.assert_called_once()
        print("✅ Native session shortcut skipped fresh login correctly")

        print("\n3️⃣ Testing force relogin...")
        login_manager.login.reset_mock()
        login_manager.save_session.reset_mock()
        login_manager.is_logged_in.reset_mock()

        result3 = login_manager.login_with_session_persistence(force_relogin=True)
        assert result3, "Force relogin should succeed"
        login_manager.login.assert_called_once()
        # Force relogin must bypass the native-session shortcut entirely.
        login_manager.is_logged_in.assert_not_called()
        print("✅ Force relogin performed fresh login correctly")

        print("\n🎉 ALL WORKFLOW TESTS PASSED!")

    finally:
        # Cleanup
        try:
            Path(session_file).unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    print("🔐 SESSION PERSISTENCE TESTING")
    print("Testing login session saving and restoration functionality")
    print()

    try:
        test_session_persistence_logic()
        test_session_workflow()
    except AssertionError as e:
        print("\n" + "="*60)
        print("❌ SOME TESTS FAILED!")
        print(f"⚠️  {e}")
        sys.exit(1)

    print("\n" + "="*60)
    print("🎉 ALL SESSION PERSISTENCE TESTS PASSED!")
    print("✅ Session persistence is working correctly")
    sys.exit(0)