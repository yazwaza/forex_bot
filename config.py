"""
Configuration module for the OANDA Arbitrage Trading System.

This module handles loading and validating configuration settings.
"""
import os
import json
import logging

logger = logging.getLogger("ArbitrageTrader")

# Default configuration
DEFAULT_CONFIG = {
    "practice_mode": True,
    "check_interval": 3,
    "min_profit_threshold": 0.001,  # 0.1%
    "max_spread_threshold": 0.0010,  # 10 pips
    "max_consecutive_losses": 3,
    "daily_loss_limit_pct": 0.05,   # 5% of account
    "currencies_to_monitor": ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"],
    "risk_per_trade": {
        "small_account": 0.01,    # 1% for accounts < 1000
        "medium_account": 0.02,   # 2% for accounts 1000-10000
        "large_account": 0.03     # 3% for accounts > 10000
    },
    "session_multipliers": {
        "london_ny_overlap": 1.2,
        "tokyo_london_overlap": 1.1,
        "london": 1.0,
        "new_york": 1.0,
        "tokyo": 0.8,
        "low_liquidity": 0.5
    }
}

def load_config(config_path='config.json'):
    """
    Load configuration from a JSON file.
    
    Args:
        config_path (str): Path to the configuration file
        
    Returns:
        dict: Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()
    
    # Try to load from file
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
                logger.info(f"Loaded configuration from {config_path}")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            logger.info("Using default configuration")
    else:
        logger.warning(f"Configuration file {config_path} not found, using defaults")
        # Create a sample config file if it doesn't exist
        save_sample_config(config_path)
    
    # Validate configuration
    validate_config(config)
    
    return config

def validate_config(config):
    """
    Validate configuration parameters.
    
    Args:
        config (dict): Configuration dictionary
    """
    # Ensure required parameters are present
    required_params = ['check_interval', 'min_profit_threshold']
    for param in required_params:
        if param not in config:
            logger.warning(f"Required parameter '{param}' not in config, using default: {DEFAULT_CONFIG[param]}")
            config[param] = DEFAULT_CONFIG[param]
    
    # Validate parameter types and ranges
    if not isinstance(config['check_interval'], int) or config['check_interval'] < 1:
        logger.warning(f"Invalid check_interval, using default: {DEFAULT_CONFIG['check_interval']}")
        config['check_interval'] = DEFAULT_CONFIG['check_interval']
    
    if not isinstance(config['min_profit_threshold'], (int, float)) or config['min_profit_threshold'] < 0:
        logger.warning(f"Invalid min_profit_threshold, using default: {DEFAULT_CONFIG['min_profit_threshold']}")
        config['min_profit_threshold'] = DEFAULT_CONFIG['min_profit_threshold']

def save_sample_config(config_path):
    """
    Save a sample configuration file.
    
    Args:
        config_path (str): Path to save the sample configuration
    """
    try:
        # Create a sample config with comments
        sample_config = {
            "api_key": "YOUR_OANDA_API_KEY_HERE",
            "account_id": "YOUR_OANDA_ACCOUNT_ID_HERE",
            "practice_mode": True,
            "check_interval": 3,
            "min_profit_threshold": 0.001,
            "max_runtime": None,  # None for unlimited runtime
            "currencies_to_monitor": ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
        }
        
        with open(config_path, 'w') as f:
            json.dump(sample_config, f, indent=4)
            
        logger.info(f"Created sample configuration file at {config_path}")
    except IOError as e:
        logger.error(f"Error creating sample configuration file: {e}")