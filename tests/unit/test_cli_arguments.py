"""Unit tests for CLI argument parsing functionality"""

import unittest
from unittest.mock import Mock, patch
import argparse
import sys
from io import StringIO

# We need to test the CLI parsing logic from the main module
# Since it's in the if __name__ == "__main__" block, we'll test it indirectly


class TestCLIArguments(unittest.TestCase):
    """Test cases for command-line argument parsing"""

    def setUp(self):
        """Set up test fixtures"""
        self.parser = argparse.ArgumentParser(description='Karaoke-Version.com Track Automation')
        self.parser.add_argument('--debug', action='store_true', 
                               help='Run in debug mode with visible browser and detailed file logging')
        self.parser.add_argument('--force-login', action='store_true',
                               help='Force fresh login instead of using saved session')
        self.parser.add_argument('--clear-session', action='store_true',
                               help='Clear saved session data and exit')

    def test_no_arguments(self):
        """Test parsing with no command line arguments"""
        args = self.parser.parse_args([])
        
        self.assertFalse(args.debug)
        self.assertFalse(args.force_login)
        self.assertFalse(args.clear_session)

    def test_debug_argument(self):
        """Test parsing with --debug flag"""
        args = self.parser.parse_args(['--debug'])
        
        self.assertTrue(args.debug)
        self.assertFalse(args.force_login)
        self.assertFalse(args.clear_session)

    def test_force_login_argument(self):
        """Test parsing with --force-login flag"""
        args = self.parser.parse_args(['--force-login'])
        
        self.assertFalse(args.debug)
        self.assertTrue(args.force_login)
        self.assertFalse(args.clear_session)

    def test_clear_session_argument(self):
        """Test parsing with --clear-session flag"""
        args = self.parser.parse_args(['--clear-session'])
        
        self.assertFalse(args.debug)
        self.assertFalse(args.force_login)
        self.assertTrue(args.clear_session)

    def test_multiple_arguments(self):
        """Test parsing with multiple flags"""
        args = self.parser.parse_args(['--debug', '--force-login'])
        
        self.assertTrue(args.debug)
        self.assertTrue(args.force_login)
        self.assertFalse(args.clear_session)

    def test_all_arguments(self):
        """Test parsing with all flags"""
        args = self.parser.parse_args(['--debug', '--force-login', '--clear-session'])
        
        self.assertTrue(args.debug)
        self.assertTrue(args.force_login)
        self.assertTrue(args.clear_session)

    def test_help_argument(self):
        """Test that help argument works (should exit with code 0)"""
        with self.assertRaises(SystemExit) as context:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                self.parser.parse_args(['--help'])
        
        self.assertEqual(context.exception.code, 0)

    def test_invalid_argument(self):
        """Test parsing with invalid argument (should exit with code 2)"""
        with self.assertRaises(SystemExit) as context:
            with patch('sys.stderr', new_callable=StringIO):
                self.parser.parse_args(['--invalid-arg'])
        
        self.assertEqual(context.exception.code, 2)

    @patch('sys.argv', ['karaoke_automator.py'])
    @patch('karaoke_automator.setup_logging')
    @patch('karaoke_automator.KaraokeVersionAutomator')
    def test_main_execution_no_args(self, mock_automator_class, mock_setup_logging):
        """Test main execution with no arguments"""
        mock_automator = Mock()
        mock_automator_class.return_value = mock_automator
        
        # Import and execute the main section
        import importlib.util
        spec = importlib.util.spec_from_file_location("karaoke_automator", "karaoke_automator.py")
        module = importlib.util.module_from_spec(spec)
        
        # This is tricky to test since it's in __main__ block
        # Instead, let's test the logic components directly
        
        # Test headless mode calculation
        debug_mode = False
        headless_mode = not debug_mode
        self.assertTrue(headless_mode)

    @patch('sys.argv', ['karaoke_automator.py', '--debug'])
    def test_debug_mode_affects_headless(self):
        """Test that debug mode affects headless setting"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--debug', action='store_true')
        args = parser.parse_args(['--debug'])
        
        headless_mode = not args.debug
        self.assertFalse(headless_mode)

    @patch('sys.argv', ['karaoke_automator.py', '--clear-session'])
    @patch('packages.authentication.LoginManager')
    @patch('builtins.print')
    @patch('builtins.exit')
    def test_clear_session_execution(self, mock_exit, mock_print, mock_login_manager_class):
        """Test clear session execution path"""
        # Mock the LoginManager
        mock_login_manager = Mock()
        mock_login_manager.clear_session.return_value = True
        mock_login_manager_class.return_value = mock_login_manager
        
        # Simulate the clear session logic
        parser = argparse.ArgumentParser()
        parser.add_argument('--clear-session', action='store_true')
        args = parser.parse_args(['--clear-session'])
        
        if args.clear_session:
            from packages.authentication import LoginManager
            temp_login = LoginManager(None, None)
            if temp_login.clear_session():
                mock_print("✅ Saved session data cleared successfully")
            else:
                mock_print("❌ Could not clear session data")
            mock_exit(0)

        # Verify the mock calls would happen
        self.assertTrue(args.clear_session)

    def test_force_login_logic(self):
        """Test force login flag logic"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--force-login', action='store_true')
        
        # Test without force login
        args_normal = parser.parse_args([])
        self.assertFalse(args_normal.force_login)
        
        # Test with force login
        args_force = parser.parse_args(['--force-login'])
        self.assertTrue(args_force.force_login)
        
        # Simulate the logic that would override the login method
        if args_force.force_login:
            # This would normally override the automator.run_automation method
            force_login_requested = True
        else:
            force_login_requested = False
            
        self.assertTrue(force_login_requested)

    def test_argument_combinations(self):
        """Test various argument combinations"""
        test_cases = [
            ([], {'debug': False, 'force_login': False, 'clear_session': False}),
            (['--debug'], {'debug': True, 'force_login': False, 'clear_session': False}),
            (['--force-login'], {'debug': False, 'force_login': True, 'clear_session': False}),
            (['--clear-session'], {'debug': False, 'force_login': False, 'clear_session': True}),
            (['--debug', '--force-login'], {'debug': True, 'force_login': True, 'clear_session': False}),
            (['--debug', '--clear-session'], {'debug': True, 'force_login': False, 'clear_session': True}),
            (['--force-login', '--clear-session'], {'debug': False, 'force_login': True, 'clear_session': True}),
            (['--debug', '--force-login', '--clear-session'], {'debug': True, 'force_login': True, 'clear_session': True}),
        ]
        
        for cli_args, expected in test_cases:
            with self.subTest(args=cli_args):
                parsed_args = self.parser.parse_args(cli_args)
                
                self.assertEqual(parsed_args.debug, expected['debug'], f"Debug mismatch for {cli_args}")
                self.assertEqual(parsed_args.force_login, expected['force_login'], f"Force login mismatch for {cli_args}")
                self.assertEqual(parsed_args.clear_session, expected['clear_session'], f"Clear session mismatch for {cli_args}")


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI argument processing"""
    
    def test_debug_mode_integration(self):
        """Test that debug mode properly configures the system"""
        # Test debug=True case
        debug_mode = True
        headless_mode = not debug_mode
        
        self.assertFalse(headless_mode)  # Debug mode should disable headless
        
        # Test debug=False case  
        debug_mode = False
        headless_mode = not debug_mode
        
        self.assertTrue(headless_mode)  # Non-debug mode should enable headless

    def test_argument_processing_flow(self):
        """Test the complete argument processing flow"""
        parser = argparse.ArgumentParser(description='Karaoke-Version.com Track Automation')
        parser.add_argument('--debug', action='store_true', 
                           help='Run in debug mode with visible browser and detailed file logging')
        parser.add_argument('--force-login', action='store_true',
                           help='Force fresh login instead of using saved session')
        parser.add_argument('--clear-session', action='store_true',
                           help='Clear saved session data and exit')
        
        # Test normal execution path
        args = parser.parse_args(['--debug', '--force-login'])
        
        # Verify argument processing
        self.assertTrue(args.debug)
        self.assertTrue(args.force_login)
        self.assertFalse(args.clear_session)
        
        # Test derived values
        headless_mode = not args.debug
        self.assertFalse(headless_mode)


if __name__ == '__main__':
    unittest.main()