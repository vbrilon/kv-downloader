#!/usr/bin/env python3
"""
Attribute Structure Validation Tests
Prevents merge conflicts from breaking attribute names and method access patterns
"""

import sys
import unittest
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from karaoke_automator import KaraokeVersionAutomator


class TestAttributeStructure(unittest.TestCase):
    """Test that critical attributes and methods exist with correct names"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize automator once for all tests"""
        cls.automator = KaraokeVersionAutomator(headless=True, show_progress=False)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up automator"""
        try:
            cls.automator.driver.quit()
        except:
            pass
    
    def test_main_manager_attributes_exist(self):
        """Test that all main manager attributes exist with correct names"""
        required_managers = [
            'config_manager',
            'chrome_manager', 
            'login_handler',
            'file_manager',
            'track_manager',  # CRITICAL: Was track_handler in broken test
            'download_manager',
            'progress',
            'stats'
        ]
        
        for manager_name in required_managers:
            with self.subTest(manager=manager_name):
                self.assertTrue(
                    hasattr(self.automator, manager_name),
                    f"Missing required manager attribute: {manager_name}"
                )
                # Ensure it's not None (except progress which can be None)
                if manager_name != 'progress':
                    manager = getattr(self.automator, manager_name)
                    self.assertIsNotNone(
                        manager,
                        f"Manager attribute {manager_name} is None"
                    )
    
    def test_track_manager_methods_exist(self):
        """Test that track manager has required mixer control methods"""
        required_methods = [
            'ensure_intro_count_enabled',
            'adjust_key',
            'discover_tracks',
            'solo_track',
            'clear_all_solos'
        ]
        
        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(
                    hasattr(self.automator.track_manager, method_name),
                    f"Missing track_manager method: {method_name}"
                )
                method = getattr(self.automator.track_manager, method_name)
                self.assertTrue(
                    callable(method),
                    f"track_manager.{method_name} is not callable"
                )
    
    def test_download_manager_methods_exist(self):
        """Test that download manager has required download methods"""
        required_methods = [
            'download_current_mix',
            'extract_song_folder_name',
            'sanitize_filesystem_name'
        ]
        
        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(
                    hasattr(self.automator.download_manager, method_name),
                    f"Missing download_manager method: {method_name}"
                )
                method = getattr(self.automator.download_manager, method_name)
                self.assertTrue(
                    callable(method),
                    f"download_manager.{method_name} is not callable"
                )
    
    def test_main_automator_methods_exist(self):
        """Test that main automator has required public methods"""
        required_methods = [
            'login',
            'is_logged_in',
            'get_available_tracks',
            'solo_track',
            'clear_all_solos',
            'load_songs_config',
            'sanitize_filename',
            'run_automation'
        ]
        
        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(
                    hasattr(self.automator, method_name),
                    f"Missing automator method: {method_name}"
                )
                method = getattr(self.automator, method_name)
                self.assertTrue(
                    callable(method),
                    f"automator.{method_name} is not callable"
                )
    
    def test_method_delegation_works(self):
        """Test that method delegation between managers works correctly"""
        # Test that main automator methods properly delegate to managers
        
        # track_manager delegation
        self.assertEqual(
            self.automator.get_available_tracks.__func__.__name__,
            'get_available_tracks',
            "get_available_tracks delegation broken"
        )
        
        # login_handler delegation  
        self.assertEqual(
            self.automator.login.__func__.__name__,
            'login',
            "login delegation broken"
        )
        
        # Test that managers are properly connected
        self.assertIs(
            self.automator.track_manager.driver,
            self.automator.driver,
            "track_manager driver not connected"
        )
        
        self.assertIs(
            self.automator.download_manager.driver,
            self.automator.driver,
            "download_manager driver not connected"
        )
    
    def test_regression_test_attribute_consistency(self):
        """Test that attributes match what regression tests expect"""
        # This is the critical test that would have caught the merge conflict issue
        
        # Test mixer control methods are on track_manager (not track_handler)
        self.assertTrue(
            hasattr(self.automator, 'track_manager'),
            "track_manager attribute missing - regression tests will fail"
        )
        self.assertTrue(
            hasattr(self.automator.track_manager, 'ensure_intro_count_enabled'),
            "track_manager.ensure_intro_count_enabled missing - mixer_controls test will fail"
        )
        self.assertTrue(
            hasattr(self.automator.track_manager, 'adjust_key'),
            "track_manager.adjust_key missing - mixer_controls test will fail"
        )
        
        # Test download methods are on download_manager (not track_handler)
        self.assertTrue(
            hasattr(self.automator, 'download_manager'),
            "download_manager attribute missing - regression tests will fail"
        )
        self.assertTrue(
            hasattr(self.automator.download_manager, 'download_current_mix'),
            "download_manager.download_current_mix missing - download_setup test will fail"
        )
        
        # Ensure the old incorrect names do NOT exist
        self.assertFalse(
            hasattr(self.automator, 'track_handler'),
            "track_handler attribute should not exist - this will confuse tests"
        )
    
    def test_manager_interconnections(self):
        """Test that managers are properly interconnected"""
        # Test progress tracker connections
        if self.automator.progress:
            # These connections should exist based on __init__
            self.assertIsNotNone(
                getattr(self.automator.track_manager, 'progress_tracker', None),
                "track_manager progress_tracker not set"
            )
        
        # Test download manager connections
        self.assertIsNotNone(
            getattr(self.automator.download_manager, 'file_manager', None),
            "download_manager file_manager not connected"
        )
        self.assertIsNotNone(
            getattr(self.automator.download_manager, 'chrome_manager', None),
            "download_manager chrome_manager not connected"
        )
        self.assertIsNotNone(
            getattr(self.automator.download_manager, 'stats_reporter', None),
            "download_manager stats_reporter not connected"
        )


if __name__ == '__main__':
    unittest.main()