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
DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER", "./downloads")
DELAY_BETWEEN_DOWNLOADS = 5  # seconds - increased for processing time
MAX_RETRIES = 3
DOWNLOAD_TIMEOUT = 30  # seconds to wait for download to complete

# Track isolation timing settings
SOLO_ACTIVATION_DELAY = 5.0   # seconds to wait after solo button activation for audio sync (restored from pre-optimization)
SOLO_ACTIVATION_DELAY_SIMPLE = 7.0   # seconds for simple arrangements (8 tracks or fewer) - optimized from 15.0s
SOLO_ACTIVATION_DELAY_COMPLEX = 10.0  # seconds for complex arrangements (9+ tracks) - optimized from 21.0s

# Track-type-specific timeout settings (Bug Fix: Click track isolation failures)
SOLO_ACTIVATION_DELAY_CLICK = 12.0   # seconds for click tracks (extended timeout due to server processing differences)
SOLO_ACTIVATION_DELAY_SPECIAL = 10.0  # seconds for bass/drums tracks (moderate extension for reliability)

# WebDriver Timeouts
WEBDRIVER_DEFAULT_TIMEOUT = 10
WEBDRIVER_SHORT_TIMEOUT = 3
WEBDRIVER_BRIEF_TIMEOUT = 2
WEBDRIVER_MICRO_TIMEOUT = 0.5

# Sleep/Delay Constants
PROGRESS_UPDATE_INTERVAL = 0.5
CLICK_HANDLER_DELAY = 0.5
TRACK_INTERACTION_DELAY = 0.5
BETWEEN_TRACKS_PAUSE = 0.5  # Reduced from 2s - download completion monitoring ensures readiness
RETRY_VERIFICATION_DELAY = 2

# Retry and Loop Constants
TRACK_SELECTION_MAX_RETRIES = 3
SOLO_BUTTON_MAX_RETRIES = 3
SOLO_ACTIVATION_MAX_WAIT = 10
FILE_OPERATION_MAX_WAIT = 30
DOWNLOAD_MAX_WAIT = 90
DOWNLOAD_COMPLETION_TIMEOUT = 60

# Polling Intervals
DOWNLOAD_CHECK_INTERVAL = 3  # Reduced from 5s - faster polling for quicker completion detection
FILE_CHECK_INTERVAL = 1
SOLO_CHECK_INTERVAL = 0.5
DOWNLOAD_MONITORING_INITIAL_WAIT = 10  # Performance optimization: reduced from 15s - test server generation reliability

# Session Constants
SESSION_MAX_AGE_SECONDS = 24 * 60 * 60  # 24 hours

# UI Constants
PROGRESS_BAR_WIDTH = 20
LOG_INTERVAL_SECONDS = 10
PROGRESS_UPDATE_LOG_INTERVAL = 20

# File Matching Constants
FILE_MATCH_MIN_RATIO = 0.3
FILE_MATCH_HIGH_RATIO = 0.7
TRACK_MATCH_MIN_RATIO = 0.6

# URLs
LOGIN_URL = os.getenv("KV_LOGIN_URL", "https://www.karaoke-version.com/login")

# Configuration files
SONGS_CONFIG_FILE = "songs.yaml"

