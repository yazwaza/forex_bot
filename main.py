#!/usr/bin/env python3
"""
OANDA Arbitrage Trading System - Main Entry Point

This script initializes and runs the arbitrage trading system.
"""
import os
import argparse
import logging
from datetime import datetime
from config import load_config
from trader import OandaArbitrageTrader
from utils.logger import setup_logging

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='OANDA Arbitrage Trading System')
    
    parser.add_argument('--demo', action='store_true', help='Run in demo mode (simulate trades)')
    parser.add_argument('--practice', action='store_true', help='Use practice environment instead of live')
    parser.add_argument('--config', type=str, default='config.json', help='Path to configuration file')
    parser.add_argument('--interval', type=int, help='Check interval in seconds')
    parser.add_argument('--runtime', type=int, help='Maximum runtime in seconds')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    return parser.parse_args()

def main():
    """Main function to run the trading system."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(log_level)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command line arguments if provided
    if args.interval:
        config['check_interval'] = args.interval
    if args.runtime:
        config['max_runtime'] = args.runtime
    
    # Determine practice/live mode
    practice_mode = args.practice or config.get('practice_mode', True)
    
    # Get credentials
    api_key = os.environ.get('OANDA_API_KEY') or config.get('api_key')
    account_id = os.environ.get('OANDA_ACCOUNT_ID') or config.get('account_id')
    
    if not api_key or not account_id:
        logger.error("API key and account ID must be provided in config or environment variables")
        return
    
    # Print startup information
    logger.info("OANDA Arbitrage Trading System")
    logger.info("-" * 40)
    logger.info(f"Starting time: {datetime.now()}")
    logger.info(f"Mode: {'Demo' if args.demo else 'Live trading'}")
    logger.info(f"Environment: {'Practice' if practice_mode else 'Production'}")
    logger.info(f"Check interval: {config['check_interval']} seconds")
    if config.get('max_runtime'):
        logger.info(f"Maximum runtime: {config['max_runtime']} seconds")
    logger.info("-" * 40)
    
    # Initialize the trader
    trader = OandaArbitrageTrader(
        api_key=api_key,
        account_id=account_id,
        practice_mode=practice_mode,
        config=config
    )
    
    # Run the trader
    trader.run(
        check_interval=config['check_interval'],
        max_runtime=config.get('max_runtime'),
        demo_mode=args.demo
    )

if __name__ == "__main__":
    main()