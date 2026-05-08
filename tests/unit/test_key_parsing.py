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

    failures = []

    for input_value, expected, description in test_cases:
        try:
            result = config_manager._validate_key_value(input_value, "Test Song")
        except Exception as e:
            failures.append(f"{description}: {input_value!r} → ERROR: {e}")
            print(f"💥 {description}: {input_value} → ERROR: {e}")
            continue

        if result == expected:
            print(f"✅ {description}: {input_value} → {result}")
        else:
            failures.append(f"{description}: {input_value!r} → {result!r} (expected {expected!r})")
            print(f"❌ {description}: {input_value} → {result} (expected {expected})")

    print("\n" + "="*60)
    print(f"📊 RESULTS: {len(test_cases) - len(failures)} passed, {len(failures)} failed")

    assert not failures, "Key parsing failures:\n  - " + "\n  - ".join(failures)


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

        assert len(songs) == len(expected_results), (
            f"Expected {len(expected_results)} songs, got {len(songs)}"
        )

        mismatches = []
        for song, (expected_name, expected_key) in zip(songs, expected_results):
            if song['name'] == expected_name and song['key'] == expected_key:
                print(f"✅ {expected_name}: key={song['key']}")
            else:
                mismatches.append(
                    f"{expected_name}: expected (name={expected_name!r}, key={expected_key}), "
                    f"got (name={song['name']!r}, key={song['key']})"
                )
                print(f"❌ {expected_name}: expected key={expected_key}, got key={song['key']}")

        assert not mismatches, "Key parsing integration mismatches:\n  - " + "\n  - ".join(mismatches)

    finally:
        # Clean up temporary file
        YAMLTestHelper.cleanup_temp_file(temp_file_path)


if __name__ == "__main__":
    print("🎹 KEY PARSING ENHANCEMENT TESTS")
    print("Testing support for multiple key format inputs")
    print()

    try:
        test_key_parsing_formats()
        test_key_parsing_integration()
    except AssertionError as e:
        print("\n" + "="*60)
        print("❌ SOME TESTS FAILED!")
        print(f"⚠️  {e}")
        sys.exit(1)

    print("\n" + "="*60)
    print("🎉 ALL KEY PARSING TESTS PASSED!")
    print("✅ Enhanced key parsing is working correctly")
    sys.exit(0)