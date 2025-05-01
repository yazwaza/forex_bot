"""
Logging configuration module.

This module provides utilities for setting up logging.
"""
import logging
import os
from datetime import datetime

def setup_logging(level=logging.INFO, log_dir="./logs"):
    """
    Configure logging for the application.
    
    Args:
        level (int): Logging level (e.g., logging.INFO, logging.DEBUG)
        log_dir (str): Directory to store log files
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"Error creating log directory: {e}")
    
    # Create unique log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/arbitrage_{timestamp}.log"
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remove any existing handlers to avoid duplication
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Create a specific logger for our app
    app_logger = logging.getLogger("ArbitrageTrader")
    
    # Log startup
    app_logger.info(f"Logging initialized at {timestamp}")
    app_logger.info(f"Log file: {log_file}")
    
    return app_logger