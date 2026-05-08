#!/usr/bin/env python3
"""
Test Configuration Refactor
Verify the new ConfigurationManager works correctly
"""

import sys
import json
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.configuration import ConfigurationManager, load_songs_config


@pytest.mark.live
def test_configuration_refactor():
    """Test the refactored configuration system"""

    print("🔧 TESTING CONFIGURATION REFACTOR")
    print("=" * 50)

    # Test 1: Direct ConfigurationManager usage
    print("\n1. Testing ConfigurationManager class...")
    config_manager = ConfigurationManager("songs.yaml")

    songs = config_manager.load_songs_config()
    assert songs, "ConfigurationManager failed to load songs from songs.yaml"
    print(f"✅ ConfigurationManager loaded {len(songs)} songs")
    for song in songs:
        print(f"   - {song['name']}: key={song['key']:+d}")

    # Test 2: Backward compatibility function
    print("\n2. Testing backward compatibility...")
    compat_songs = load_songs_config()
    assert len(compat_songs) == len(songs), (
        f"Backward compatibility broken: load_songs_config() returned "
        f"{len(compat_songs)} songs, expected {len(songs)}"
    )
    print("✅ Backward compatibility maintained")

    # Test 3: Configuration validation
    print("\n3. Testing configuration validation...")
    assert config_manager.validate_configuration_file(), (
        "validate_configuration_file() returned False for songs.yaml"
    )
    print("✅ Configuration file validation passed")

    # Test 4: Configuration summary
    print("\n4. Testing configuration summary...")
    config_manager = ConfigurationManager()
    summary = config_manager.get_configuration_summary()
    assert 'config_file' in summary and 'total_songs' in summary, (
        f"Configuration summary missing expected keys: {summary}"
    )
    print("✅ Configuration summary generated:")
    print(f"   - Config file: {summary['config_file']}")
    print(f"   - Total songs: {summary['total_songs']}")
    print(f"   - Songs with key adjustment: {summary['songs_with_key_adjustment']}")
    if summary['key_adjustments']:
        print(f"   - Key adjustments: {summary['key_adjustments']}")

    # Test 5: Integration with KaraokeVersionAutomator
    print("\n5. Testing integration with main automator...")
    automator = None
    try:
        from karaoke_automator import KaraokeVersionAutomator

        try:
            automator = KaraokeVersionAutomator(headless=True, show_progress=False)
        except Exception as e:
            # Browser-driven smoke test requires a working Chrome installation;
            # skip rather than fail when running in environments without it.
            import pytest
            pytest.skip(f"KaraokeVersionAutomator could not start Chrome: {e}")

        automator_songs = automator.load_songs_config()
        assert len(automator_songs) == len(songs), (
            f"Automator integration failed: automator loaded {len(automator_songs)} songs, "
            f"expected {len(songs)}"
        )
        print("✅ Automator integration working")

        automator_summary = automator.get_configuration_summary()
        assert automator_summary['total_songs'] > 0, (
            f"Automator configuration summary reports zero songs: {automator_summary}"
        )
        print("✅ Automator configuration summary working")

    finally:
        if automator is not None:
            try:
                automator.driver.quit()
            except Exception:
                pass

    print("\n🎉 ALL CONFIGURATION REFACTOR TESTS PASSED!")
    print("\n📊 REFACTOR BENEFITS:")
    print("✅ Clean separation of concerns")
    print("✅ Better error handling and logging")
    print("✅ Enhanced validation")
    print("✅ Backward compatibility maintained")
    print("✅ Type hints and documentation")


if __name__ == "__main__":
    print("=" * 50)
    try:
        test_configuration_refactor()
    except AssertionError as e:
        print(f"❌ CONFIGURATION REFACTOR FAILED: {e}")
        print("=" * 50)
        sys.exit(1)
    print("✅ CONFIGURATION REFACTOR SUCCESSFUL")
    print("=" * 50)