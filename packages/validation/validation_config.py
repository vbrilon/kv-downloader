"""
Configuration classes for validation system
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ValidationConfig:
    """Configuration for validation behavior
    
    Attributes:
        threshold: Minimum percentage of checks that must pass (0.0-1.0)
        max_retries: Maximum number of retry attempts
        retry_delay: Seconds to wait between retry attempts
        validation_type: Type of validation ('strict' or 'audio_mix')
        return_format: Format of return value ('boolean' or 'detailed')
        enable_javascript: Whether to use JavaScript-based validation
        log_details: Whether to log detailed validation information
    """
    threshold: float = 1.0
    max_retries: int = 3
    retry_delay: int = 2
    validation_type: str = 'strict'  # 'strict' or 'audio_mix'
    return_format: str = 'boolean'   # 'boolean' or 'detailed'
    enable_javascript: bool = False
    log_details: bool = True
    
    def __post_init__(self):
        """Validate configuration values"""
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        if self.max_retries < 1:
            raise ValueError("max_retries must be at least 1")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        if self.validation_type not in ['strict', 'audio_mix']:
            raise ValueError("validation_type must be 'strict' or 'audio_mix'")
        if self.return_format not in ['boolean', 'detailed']:
            raise ValueError("return_format must be 'boolean' or 'detailed'")


# Predefined configurations for common use cases
DOWNLOAD_MANAGER_CONFIG = ValidationConfig(
    threshold=1.0,
    max_retries=3, 
    retry_delay=2,
    validation_type='strict',
    return_format='boolean',
    enable_javascript=False,
    log_details=True
)

TRACK_MANAGER_CONFIG = ValidationConfig(
    threshold=0.67,
    max_retries=3,
    retry_delay=2, 
    validation_type='audio_mix',
    return_format='detailed',
    enable_javascript=True,
    log_details=True
)