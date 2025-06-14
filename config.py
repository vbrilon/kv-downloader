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
            return config.get('songs', [])
    except FileNotFoundError:
        print(f"Songs config file '{SONGS_CONFIG_FILE}' not found. Please create it.")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing songs config file: {e}")
        return []