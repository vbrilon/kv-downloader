#!/usr/bin/env python3
"""
Test Configuration Refactor
Verify the new ConfigurationManager works correctly
"""

import sys
import json
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config_manager import ConfigurationManager, load_songs_config, get_configuration_summary

def test_configuration_refactor():
    """Test the refactored configuration system"""
    
    print("🔧 TESTING CONFIGURATION REFACTOR")
    print("=" * 50)
    
    # Test 1: Direct ConfigurationManager usage
    print("\n1. Testing ConfigurationManager class...")
    config_manager = ConfigurationManager("songs.yaml")
    
    songs = config_manager.load_songs_config()
    if songs:
        print(f"✅ ConfigurationManager loaded {len(songs)} songs")
        for song in songs:
            print(f"   - {song['name']}: key={song['key']:+d}")
    else:
        print("❌ ConfigurationManager failed to load songs")
        return False
    
    # Test 2: Backward compatibility function
    print("\n2. Testing backward compatibility...")
    compat_songs = load_songs_config()
    if len(compat_songs) == len(songs):
        print("✅ Backward compatibility maintained")
    else:
        print("❌ Backward compatibility broken")
        return False
    
    # Test 3: Configuration validation
    print("\n3. Testing configuration validation...")
    is_valid = config_manager.validate_configuration_file()
    if is_valid:
        print("✅ Configuration file validation passed")
    else:
        print("❌ Configuration file validation failed")
        return False
    
    # Test 4: Configuration summary
    print("\n4. Testing configuration summary...")
    summary = get_configuration_summary()
    print("✅ Configuration summary generated:")
    print(f"   - Config file: {summary['config_file']}")
    print(f"   - Total songs: {summary['total_songs']}")
    print(f"   - Songs with key adjustment: {summary['songs_with_key_adjustment']}")
    if summary['key_adjustments']:
        print(f"   - Key adjustments: {summary['key_adjustments']}")
    
    # Test 5: Integration with KaraokeVersionAutomator
    print("\n5. Testing integration with main automator...")
    try:
        from karaoke_automator import KaraokeVersionAutomator
        
        # Test with default config
        automator = KaraokeVersionAutomator(headless=True, show_progress=False)
        automator_songs = automator.load_songs_config()
        
        if len(automator_songs) == len(songs):
            print("✅ Automator integration working")
        else:
            print("❌ Automator integration failed")
            return False
        
        # Test configuration summary through automator
        automator_summary = automator.get_configuration_summary()
        if automator_summary['total_songs'] > 0:
            print("✅ Automator configuration summary working")
        else:
            print("❌ Automator configuration summary failed")
            return False
        
        automator.driver.quit()
        
    except Exception as e:
        print(f"❌ Automator integration test failed: {e}")
        return False
    
    print("\n🎉 ALL CONFIGURATION REFACTOR TESTS PASSED!")
    print("\n📊 REFACTOR BENEFITS:")
    print("✅ Clean separation of concerns")
    print("✅ Better error handling and logging")
    print("✅ Enhanced validation")
    print("✅ Backward compatibility maintained")
    print("✅ Type hints and documentation")
    
    return True

if __name__ == "__main__":
    success = test_configuration_refactor()
    print("\n" + "=" * 50)
    if success:
        print("✅ CONFIGURATION REFACTOR SUCCESSFUL")
    else:
        print("❌ CONFIGURATION REFACTOR FAILED")
    print("=" * 50)