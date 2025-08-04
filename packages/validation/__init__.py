"""
Validation Module for Karaoke Track Automation

Provides unified validation logic for track selection and audio state verification.
Consolidates duplicate validation code from download_manager and track_manager.
"""

from .track_validator import TrackValidator
from .audio_validator import AudioValidator
from .validation_config import ValidationConfig, DOWNLOAD_MANAGER_CONFIG, TRACK_MANAGER_CONFIG

__all__ = ['TrackValidator', 'AudioValidator', 'ValidationConfig', 'DOWNLOAD_MANAGER_CONFIG', 'TRACK_MANAGER_CONFIG']