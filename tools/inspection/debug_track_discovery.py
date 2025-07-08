#!/usr/bin/env python3
"""
Debug Track Discovery Tool

This tool helps investigate track discovery issues by providing detailed 
analysis of track elements on Karaoke-Version.com song pages.

Usage:
    python debug_track_discovery.py

Features:
- Lists all discovered tracks with their data-index values
- Shows track names and positions
- Helps identify missing rhythm guitar or other expected tracks
- Compares track arrangements between different songs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.browser import ChromeManager
from packages.authentication import LoginManager
from packages.track_management import TrackManager
from packages.configuration import load_songs_config
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def debug_track_discovery():
    """Debug track discovery for all configured songs"""
    
    print("🔍 TRACK DISCOVERY DEBUG TOOL")
    print("=" * 50)
    
    # Load configuration
    try:
        songs = load_songs_config()
        if not songs:
            print("❌ No songs configured in songs.yaml")
            return
    except Exception as e:
        print(f"❌ Error loading songs configuration: {e}")
        return
    
    # Initialize browser and managers
    chrome_manager = ChromeManager()
    driver, wait = chrome_manager.setup_driver(headless=False, download_path=None)
    
    try:
        # Login
        login_manager = LoginManager(driver, wait)
        print("\n🔐 Logging in...")
        if not login_manager.login():
            print("❌ Login failed")
            return
        
        # Initialize track manager
        track_manager = TrackManager(driver, wait)
        
        # Analyze each song
        for i, song in enumerate(songs, 1):
            song_url = song['url']
            song_name = song.get('name', 'Unknown Song')
            
            print(f"\n📀 SONG {i}: {song_name}")
            print(f"🔗 URL: {song_url}")
            print("-" * 40)
            
            # Discover tracks
            try:
                tracks = track_manager.discover_tracks(song_url)
                
                if not tracks:
                    print("❌ No tracks discovered")
                    continue
                
                print(f"✅ Discovered {len(tracks)} tracks:")
                
                # Sort tracks by data-index for better readability
                sorted_tracks = sorted(tracks, key=lambda x: int(x['index']))
                
                for track in sorted_tracks:
                    index = track['index']
                    name = track['name']
                    print(f"   [{index:2}] {name}")
                    
                    # Highlight guitar tracks specifically
                    if 'guitar' in name.lower():
                        if 'rhythm' in name.lower():
                            print(f"       ^^^ RHYTHM GUITAR FOUND!")
                        elif 'lead' in name.lower():
                            print(f"       ^^^ LEAD GUITAR FOUND!")
                        else:
                            print(f"       ^^^ GUITAR TRACK FOUND!")
                
                # Check for common missing instruments
                track_names_lower = [t['name'].lower() for t in tracks]
                missing_instruments = []
                
                common_instruments = [
                    ('rhythm guitar', 'rhythm'),
                    ('lead guitar', 'lead'),
                    ('bass guitar', 'bass'),
                    ('drums', 'drum'),
                    ('vocals', 'vocal'),
                    ('piano', 'piano'),
                    ('organ', 'organ')
                ]
                
                for instrument, keyword in common_instruments:
                    if not any(keyword in name for name in track_names_lower):
                        missing_instruments.append(instrument)
                
                if missing_instruments:
                    print(f"\n⚠️  Potentially missing instruments:")
                    for instrument in missing_instruments:
                        print(f"     - {instrument}")
                else:
                    print(f"\n✅ All common instruments appear to be present")
                    
            except Exception as e:
                print(f"❌ Error discovering tracks: {e}")
                continue
        
        print(f"\n🎉 Track discovery analysis complete!")
        print(f"📋 Summary: Analyzed {len(songs)} songs")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    finally:
        try:
            driver.quit()
            chrome_manager.quit()
        except:
            pass

if __name__ == "__main__":
    debug_track_discovery()