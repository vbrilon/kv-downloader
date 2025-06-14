import os
import yaml
from dotenv import load_dotenv

load_dotenv()

# Karaoke-Version.com credentials
USERNAME = os.getenv("KV_USERNAME")
PASSWORD = os.getenv("KV_PASSWORD")

# Download settings
DOWNLOAD_FOLDER = "./downloads"
DELAY_BETWEEN_DOWNLOADS = 5  # seconds - increased for processing time
MAX_RETRIES = 3
DOWNLOAD_TIMEOUT = 30  # seconds to wait for download to complete

# Track types to attempt (used for validation)
COMMON_TRACK_TYPES = [
    "Lead Vocal",
    "Lead Electric Guitar", 
    "Rhythm Electric Guitar",
    "Acoustic Guitar",
    "Bass Guitar",
    "Electronic Drum Kit",
    "Synthesizer",
    "Piano",
    "Strings",
    "Brass",
    "Intro count Click"
]

# URLs (you'll need to inspect the actual site structure)
LOGIN_URL = os.getenv("KV_LOGIN_URL", "https://www.karaoke-version.com/login")

# Songs configuration file
SONGS_CONFIG_FILE = "songs.yaml"

def load_songs_config():
    """Load songs configuration from YAML file"""
    try:
        with open(SONGS_CONFIG_FILE, 'r') as file:
            config = yaml.safe_load(file)
            songs = config.get('songs', [])
            
            # Validate song entries and add defaults
            validated_songs = []
            for song in songs:
                if 'url' in song and 'name' in song:
                    # Set default key to 0 if not specified
                    if 'key' not in song:
                        song['key'] = 0
                    else:
                        # Validate key is an integer between -12 and +12
                        try:
                            key_value = int(song['key'])
                            if key_value < -12 or key_value > 12:
                                print(f"Warning: Key value {key_value} out of range (-12 to +12), setting to 0")
                                song['key'] = 0
                            else:
                                song['key'] = key_value
                        except (ValueError, TypeError):
                            print(f"Warning: Invalid key value '{song['key']}', setting to 0")
                            song['key'] = 0
                    
                    validated_songs.append(song)
                else:
                    print(f"Warning: Invalid song entry missing 'url' or 'name': {song}")
            
            return validated_songs
            
    except FileNotFoundError:
        print(f"Songs config file '{SONGS_CONFIG_FILE}' not found. Please create it.")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing songs config file: {e}")
        return []