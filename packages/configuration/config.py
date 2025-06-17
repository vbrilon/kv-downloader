"""
Application Configuration
Contains only configuration values and constants
Logic moved to config_manager.py for clean separation
"""

import os
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

# Track isolation timing settings
SOLO_ACTIVATION_DELAY = 2.0  # seconds to wait after solo button activation for audio sync

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

# URLs
LOGIN_URL = os.getenv("KV_LOGIN_URL", "https://www.karaoke-version.com/login")

# Configuration files
SONGS_CONFIG_FILE = "songs.yaml"

# Key adjustment limits
MIN_KEY_ADJUSTMENT = -12
MAX_KEY_ADJUSTMENT = 12

