#!/usr/bin/env python3
"""
Unit tests for enhanced key parsing functionality
Tests support for multiple key formats: 2, "+2", "-3", etc.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.configuration.config_manager import ConfigurationManager


def test_key_parsing_formats():
    """Test key parsing with various input formats"""
    config_manager = ConfigurationManager()
    
    # Test cases: (input_value, expected_output, description)
    test_cases = [
        # Integer inputs
        (2, 2, "Integer positive"),
        (-3, -3, "Integer negative"),
        (0, 0, "Integer zero"),
        (12, 12, "Integer max positive"),
        (-12, -12, "Integer max negative"),
        
        # String inputs with explicit positive sign
        ("+2", 2, "String with explicit positive sign"),
        ("+0", 0, "String with explicit positive zero"),
        ("+12", 12, "String with explicit positive max"),
        
        # String inputs without sign (positive)
        ("2", 2, "String without sign (positive)"),
        ("5", 5, "String without sign (positive)"),
        ("12", 12, "String without sign max"),
        
        # String inputs with negative sign
        ("-2", -2, "String with negative sign"),
        ("-5", -5, "String with negative sign"),
        ("-12", -12, "String with negative max"),
        
        # Edge cases
        (None, 0, "None input"),
        ("", 0, "Empty string"),
        ("  +3  ", 3, "String with whitespace"),
        ("  -2  ", -2, "String with whitespace and negative"),
        
        # Out of range values (should be clamped to 0)
        (15, 0, "Out of range positive"),
        (-15, 0, "Out of range negative"),
        ("+15", 0, "Out of range positive string"),
        ("-15", 0, "Out of range negative string"),
        
        # Invalid values (should default to 0)
        ("abc", 0, "Invalid string"),
        ("2.5", 0, "Float string"),
        (2.5, 0, "Float input"),
        ([], 0, "List input"),
        ({}, 0, "Dict input"),
    ]
    
    print("🧪 TESTING KEY PARSING FUNCTIONALITY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for input_value, expected, description in test_cases:
        try:
            result = config_manager._validate_key_value(input_value, "Test Song")
            
            if result == expected:
                print(f"✅ {description}: {input_value} → {result}")
                passed += 1
            else:
                print(f"❌ {description}: {input_value} → {result} (expected {expected})")
                failed += 1
                
        except Exception as e:
            print(f"💥 {description}: {input_value} → ERROR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {failed} tests failed")
        return False


def test_key_parsing_integration():
    """Test key parsing through the full configuration loading process"""
    import os
    
    # Import centralized YAML utilities
    from tests.yaml_test_helpers import YAMLTestHelper, StandardYAMLContent
    
    print("\n🔗 TESTING INTEGRATION WITH YAML LOADING")
    print("="*60)
    
    # Get test YAML content with various key formats
    test_yaml_content = StandardYAMLContent.get_key_format_test_config()
    
    # Create temporary YAML file using helper
    temp_file_path = YAMLTestHelper.create_temp_yaml_file(test_yaml_content)
    
    try:
        # Test configuration loading
        config_manager = ConfigurationManager(temp_file_path)
        songs = config_manager.load_songs_config()
        
        # Verify results
        expected_results = [
            ('Song_With_Integer_Key', 2),
            ('Song_With_Plus_String_Key', 3),
            ('Song_With_Negative_String_Key', -2),
            ('Song_With_No_Key', 0),
            ('Song_With_String_Number_Key', 5)
        ]
        
        print(f"Loaded {len(songs)} songs from test configuration")
        
        all_passed = True
        for song, (expected_name, expected_key) in zip(songs, expected_results):
            if song['name'] == expected_name and song['key'] == expected_key:
                print(f"✅ {expected_name}: key={song['key']}")
            else:
                print(f"❌ {expected_name}: expected key={expected_key}, got key={song['key']}")
                all_passed = False
        
        return all_passed
        
    finally:
        # Clean up temporary file
        YAMLTestHelper.cleanup_temp_file(temp_file_path)


if __name__ == "__main__":
    print("🎹 KEY PARSING ENHANCEMENT TESTS")
    print("Testing support for multiple key format inputs")
    print()
    
    # Run unit tests
    unit_tests_passed = test_key_parsing_formats()
    
    # Run integration tests  
    integration_tests_passed = test_key_parsing_integration()
    
    # Final result
    print("\n" + "="*60)
    if unit_tests_passed and integration_tests_passed:
        print("🎉 ALL KEY PARSING TESTS PASSED!")
        print("✅ Enhanced key parsing is working correctly")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        print("⚠️  Key parsing enhancement needs attention")
        sys.exit(1)