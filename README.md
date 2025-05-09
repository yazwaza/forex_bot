# OANDA Arbitrage Trading System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

An automated trading system that identifies and executes currency arbitrage opportunities on the OANDA forex platform.

## Overview

This trading system continuously monitors currency pairs to detect profitable arbitrage cycles in the forex market. It uses the OANDA API to fetch real-time exchange rates and execute trades when profitable opportunities are found.

### What is Arbitrage?

Arbitrage is the practice of taking advantage of price differences in different markets for the same asset. In the context of forex trading, triangular arbitrage involves converting one currency to another through a series of exchanges to profit from pricing inefficiencies.

For example: USD → EUR → GBP → USD, where the final amount in USD is greater than the initial amount.

## Features

- **Real-time Monitoring**: Continuously monitors exchange rates for multiple currency pairs
- **Triangular Arbitrage**: Identifies profitable currency cycles
- **Risk Management**: Built-in circuit breakers, position sizing, and loss limits
- **Market Session Awareness**: Automatically adjusts strategy based on active trading sessions (Tokyo, London, New York)
- **Performance Tracking**: Records and analyzes trade history
- **Demo Mode**: Simulates trades without risking real money
- **Parallel Processing**: Uses concurrent API calls to fetch rates efficiently

## Requirements

- Python 3.8+
- OANDA API key and account
- Required Python packages:
  - requests
  - numpy
  - logging
  - concurrent.futures (included in Python's standard library)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/oanda-arbitrage-trader.git
cd oanda-arbitrage-trader
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create or modify `config.json` with your OANDA credentials and preferences:
```json
{
    "api_key": "YOUR_OANDA_API_KEY",
    "account_id": "YOUR_OANDA_ACCOUNT_ID",
    "practice_mode": true,
    "check_interval": 3,
    "min_profit_threshold": 0.001
}
```

## Usage

### Basic Usage

Run in demo mode (simulates trades):
```bash
python main.py --demo
```

Run with practice account:
```bash
python main.py --practice
```

Run with custom configuration:
```bash
python main.py --config my_config.json
```

### Command Line Options

- `--demo`: Run in demo mode (simulate trades)
- `--practice`: Use OANDA practice environment
- `--config`: Path to configuration file
- `--interval`: Check interval in seconds
- `--runtime`: Maximum runtime in seconds
- `--verbose`: Enable verbose logging

### Example

```bash
# Run in demo mode with verbose logging for 1 hour
python main.py --demo --verbose --runtime 3600
```

## Configuration

The `config.json` file allows you to customize the trading system:

```json
{
    "api_key": "YOUR_OANDA_API_KEY",
    "account_id": "YOUR_OANDA_ACCOUNT_ID",
    "practice_mode": true,
    "check_interval": 3,
    "min_profit_threshold": 0.001,
    "max_runtime": null,
    "max_consecutive_losses": 3,
    "daily_loss_limit_pct": 0.05,
    "currencies_to_monitor": ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"],
    "risk_per_trade": {
        "small_account": 0.01,
        "medium_account": 0.02,
        "large_account": 0.03
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
```

| Parameter | Description |
|-----------|-------------|
| `api_key` | Your OANDA API key |
| `account_id` | Your OANDA account ID |
| `practice_mode` | Set to `true` to use practice environment, `false` for live trading |
| `check_interval` | Seconds between checks for arbitrage opportunities |
| `min_profit_threshold` | Minimum profit percentage required to execute a trade (0.001 = 0.1%) |
| `max_runtime` | Maximum runtime in seconds (null for unlimited) |
| `max_consecutive_losses` | Stop trading after this many consecutive losses |
| `daily_loss_limit_pct` | Maximum allowed daily loss as percentage of account (0.05 = 5%) |
| `currencies_to_monitor` | List of currencies to include in arbitrage searches |
| `risk_per_trade` | Position sizing parameters based on account size |
| `session_multipliers` | Strategy adjustments for different market sessions |

## Project Structure

- `main.py`: Entry point for the application
- `trader.py`: Main trading class handling strategy and execution
- `config.py`: Configuration handling and validation
- `api/oanda_api.py`: OANDA API client
- `strategies/arbitrage.py`: Arbitrage detection algorithms
- `utils/logger.py`: Logging configuration
- `utils/performance.py`: Performance tracking and analysis

## How it Works

1. The system fetches current exchange rates for all currency pairs
2. It searches for profitable arbitrage cycles (e.g., USD → EUR → GBP → USD)
3. If a profitable cycle is found, it calculates the optimal position size
4. It executes the trade sequence and records the results
5. Circuit breakers monitor for adverse conditions and can pause trading

## Risk Warning

Forex trading involves substantial risk. This software is provided for educational and research purposes only:

- Test thoroughly in a practice environment before live trading
- Past performance is not indicative of future results
- Arbitrage opportunities may be short-lived or illusory due to spreads, fees, and slippage
- The system includes risk management features, but there is no guarantee against losses

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [OANDA API Documentation](https://developer.oanda.com/)
- [Triangular Arbitrage Concept](https://en.wikipedia.org/wiki/Triangular_arbitrage)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
