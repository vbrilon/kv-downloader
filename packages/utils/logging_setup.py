"""Logging setup utilities for karaoke automation"""

import logging
from pathlib import Path


def setup_logging(debug_mode):
    """Setup logging configuration based on debug mode"""
    # Clear existing handlers
    logging.getLogger().handlers.clear()
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    if debug_mode:
        # Debug mode: detailed logs to file, minimal to console
        logging.getLogger().setLevel(logging.DEBUG)
        
        # File handler for all debug output
        file_handler = logging.FileHandler('logs/debug.log', mode='w')  # Overwrite each run
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logging.getLogger().addHandler(file_handler)
        
        # Console handler for important messages only (so progress bar works)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        console_handler.setFormatter(simple_formatter)
        logging.getLogger().addHandler(console_handler)
        
        logging.info("🐛 Debug mode enabled - detailed logs in logs/debug.log")
        logging.info("👁️ Browser will be visible, progress bar on console")
        
    else:
        # Production mode: normal logging to both file and console
        logging.getLogger().setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler('logs/automation.log')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        logging.getLogger().addHandler(file_handler)
        
        # Console handler  
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logging.getLogger().addHandler(console_handler)
        
        logging.info("🚀 Running in production mode - headless browser")