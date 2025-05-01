"""
OANDA Arbitrage Trader Module

This module contains the main trader class for executing arbitrage strategies.
"""
import time
import threading
import numpy as np
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import concurrent.futures

from api.oanda_api import OandaAPI
from strategies.arbitrage import find_profitable_cycles
from utils.performance import PerformanceTracker

logger = logging.getLogger("ArbitrageTrader")

class OandaArbitrageTrader:
    def __init__(self, api_key, account_id, practice_mode=True, config=None):
        """
        Initialize the OANDA arbitrage trader.
        
        Args:
            api_key (str): Your OANDA API key
            account_id (str): Your OANDA account ID
            practice_mode (bool): If True, use practice environment, else use live
            config (dict): Configuration dictionary
        """
        self.api_key = api_key
        self.account_id = account_id
        self.practice_mode = practice_mode
        self.config = config or {}
        
        # Initialize API client
        self.api = OandaAPI(api_key, account_id, practice_mode)
        
        # Performance tracking
        self.performance = PerformanceTracker()
        
        # Circuit breakers
        self.consecutive_losses = 0
        self.max_consecutive_losses = config.get('max_consecutive_losses', 3)
        self.daily_loss_limit_pct = config.get('daily_loss_limit_pct', 0.05)  # 5% of account
        self.starting_balance = self.api.get_account_balance()
        self.daily_loss_limit = self.starting_balance * self.daily_loss_limit_pct
        
        # Market data
        self.exchange_rates = {}
        self.rate_history = defaultdict(list)
        self.volatility = {}
        self.last_update = {}
        
        # Available instruments and currencies
        self.instruments = self.api.get_tradable_instruments()
        self.currencies = self._extract_currencies()
        self.valid_pairs = self._build_valid_pairs()
        
        # Strategy parameters
        self.min_profit_threshold = config.get('min_profit_threshold', 0.001)  # 0.1%
        self.volatility_window = config.get('volatility_window', 20)
        self.max_spread_threshold = config.get('max_spread_threshold', 0.0003)  # 3 pips
        self.market_session = "unknown"
        
        # Trading state
        self.is_trading_active = False
        self.trade_lock = threading.Lock()
        self.last_opportunity_time = None
        
        logger.info(f"OANDA Arbitrage Trader initialized in {'practice' if practice_mode else 'live'} mode")
        logger.info(f"Account ID: {account_id}")
        logger.info(f"Starting balance: {self.starting_balance}")
        logger.info(f"Monitoring {len(self.valid_pairs)} valid currency pairs")
    
    def _extract_currencies(self):
        """Extract unique currencies from the list of instruments."""
        currencies = set()
        
        for instrument in self.instruments:
            name = instrument['name']
            if '_' in name:
                base, quote = name.split('_')
                currencies.add(base)
                currencies.add(quote)
        
        logger.info(f"Found {len(currencies)} unique currencies")
        return list(currencies)
    
    def _build_valid_pairs(self):
        """Build a list of valid tradable currency pairs."""
        valid_pairs = []
        
        for instrument in self.instruments:
            if instrument['type'] == 'CURRENCY' and '_' in instrument['name']:
                base, quote = instrument['name'].split('_')
                valid_pairs.append((base, quote))
        
        return valid_pairs
    
    def determine_market_session(self):
        """Determine which market sessions are currently open."""
        now = datetime.utcnow()
        hour = now.hour
        
        # Check if Tokyo session is open (midnight-9am UTC)
        tokyo_open = 0 <= hour < 9
        
        # Check if London session is open (8am-4pm UTC)
        london_open = 8 <= hour < 16
        
        # Check if New York session is open (1pm-10pm UTC)
        ny_open = 13 <= hour < 22
        
        # Determine overlaps for optimal trading
        if london_open and ny_open:
            return "london_ny_overlap"
        elif tokyo_open and london_open:
            return "tokyo_london_overlap"
        elif london_open:
            return "london"
        elif ny_open:
            return "new_york"
        elif tokyo_open:
            return "tokyo"
        else:
            return "low_liquidity"
    
    def adjust_strategy_for_session(self):
        """Adjust strategy parameters based on current market session."""
        self.market_session = self.determine_market_session()
        
        # Get session multipliers from config
        session_multipliers = self.config.get('session_multipliers', {
            'london_ny_overlap': 1.2,
            'tokyo_london_overlap': 1.1,
            'london': 1.0,
            'new_york': 1.0,
            'tokyo': 0.8,
            'low_liquidity': 0.5
        })
        
        if self.market_session == "london_ny_overlap":
            # Most liquid time, can be more aggressive
            self.min_profit_threshold = self.config.get('min_profit_threshold', 0.001) * 0.8
            self.check_interval = 1  # Check more frequently
            
        elif self.market_session == "tokyo_london_overlap":
            # Secondary liquid period, moderately aggressive
            self.min_profit_threshold = self.config.get('min_profit_threshold', 0.001) * 0.9
            self.check_interval = 2
            
        elif self.market_session in ["london", "new_york"]:
            # Single major session, standard settings
            self.min_profit_threshold = self.config.get('min_profit_threshold', 0.001)
            self.check_interval = 3
            
        else:
            # Low liquidity period, be more conservative
            self.min_profit_threshold = self.config.get('min_profit_threshold', 0.001) * 1.5
            self.check_interval = 5  # Check less frequently
            
        logger.info(f"Strategy adjusted for {self.market_session} session: "
                   f"profit threshold={self.min_profit_threshold*100:.3f}%, "
                   f"check interval={self.check_interval}s")
    
    def fetch_exchange_rates_parallel(self):
        """Fetch exchange rates for all valid currency pairs in parallel."""
        rates = {}
        timestamps = {}
        
        def fetch_single_instrument(pair):
            base, quote = pair
            instrument = f"{base}_{quote}"
            
            result = self.api.get_current_price(instrument)
            return pair, result
        
        # Use thread pool to fetch rates in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_single_instrument, pair) for pair in self.valid_pairs]
            results = []
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error(f"Error in parallel rate fetching: {e}")
        
        # Process results
        for pair, result in results:
            if result:
                base, quote = pair
                
                # Store direct rate
                rates[pair] = result
                timestamps[pair] = result['timestamp']
                
                # Also update rate history for volatility calculation
                self.rate_history[pair].append(result['mid'])
                if len(self.rate_history[pair]) > self.volatility_window:
                    self.rate_history[pair].pop(0)
                
                # Calculate volatility if enough data
                if len(self.rate_history[pair]) >= 5:
                    self.volatility[pair] = np.std(self.rate_history[pair]) / np.mean(self.rate_history[pair])
                
                # Also add synthetic pairs if needed (for cross rates)
                inverse_pair = (quote, base)
                if inverse_pair not in rates and inverse_pair not in self.valid_pairs:
                    inverse_rate = {
                        'bid': 1.0 / result['ask'],  # Flip bid/ask for inverse
                        'ask': 1.0 / result['bid'],
                        'mid': 1.0 / result['mid'],
                        'spread': result['spread'] / (result['bid'] * result['ask']),
                        'timestamp': result['timestamp'],
                        'synthetic': True
                    }
                    rates[inverse_pair] = inverse_rate
                    timestamps[inverse_pair] = result['timestamp']
        
        self.exchange_rates = rates
        self.last_update = timestamps
        
        # Calculate effective rates for trading (accounting for spread)
        self.effective_rates = {}
        for (base, quote), data in rates.items():
            # When buying the quote currency, we use the ask price
            self.effective_rates[(base, quote)] = data['ask']
            
            # When selling the quote currency, we use the bid price
            if (quote, base) in rates:
                self.effective_rates[(quote, base)] = 1.0 / data['bid']
        
        logger.info(f"Updated {len(rates)} exchange rates")
        return rates
    
    def execute_arbitrage_cycle(self, cycle, amount):
        """Execute a series of trades to capture an arbitrage opportunity."""
        cycle_pairs = cycle['pairs']
        expected_profit = cycle['effective_profit']
        
        logger.info(f"Executing arbitrage cycle with expected profit: {expected_profit*100:.4f}%")
        logger.info(f"Cycle: {' -> '.join([p[0] for p in cycle_pairs] + [cycle_pairs[-1][1]])}")
        
        # Results tracking
        results = {
            'success': True,
            'trades': [],
            'starting_amount': amount,
            'current_amount': amount
        }
        
        # Execute each trade in sequence
        current_currency = cycle_pairs[0][0]
        current_amount = amount
        
        for from_curr, to_curr in cycle_pairs:
            if from_curr != current_currency:
                logger.error(f"Currency mismatch in trade sequence: expected {current_currency}, got {from_curr}")
                results['success'] = False
                results['error'] = "Currency mismatch in trade sequence"
                return results
            
            # Format the instrument name
            instrument = f"{from_curr}_{to_curr}"
            
            # Get latest price to calculate units
            price_data = self.api.get_current_price(instrument)
            if not price_data:
                logger.error(f"Failed to get price for {instrument}")
                results['success'] = False
                results['error'] = f"Price data unavailable for {instrument}"
                return results
            
            # Calculate units based on currency pair direction
            if from_curr == 'USD':
                units = current_amount
            else:
                # Convert to correct units for this instrument
                units = current_amount / price_data['mid']
            
            # Determine direction (positive units = buy, negative = sell)
            # When trading from base to quote, we're buying the instrument
            units = abs(units)
            
            # Place the order
            order_result = self.api.place_order(instrument, units)
            
            if not order_result:
                logger.error(f"Failed to execute trade: {from_curr} to {to_curr}")
                results['success'] = False
                results['error'] = f"Order failed for {instrument}"
                return results
            
            # Extract fill price from the order result
            fill_details = order_result.get('orderFillTransaction', {})
            executed_price = float(fill_details.get('price', 0))
            executed_units = float(fill_details.get('units', 0))
            
            if executed_price <= 0 or executed_units == 0:
                logger.error(f"Invalid execution details for {instrument}")
                results['success'] = False
                results['error'] = "Invalid execution details"
                return results
            
            # Update current currency and amount
            current_currency = to_curr
            current_amount = executed_units * executed_price
            
            # Record this leg of the arbitrage
            results['trades'].append({
                'instrument': instrument,
                'units': executed_units,
                'price': executed_price,
                'from_currency': from_curr,
                'to_currency': to_curr,
                'amount': current_amount
            })
            
            logger.info(f"Completed trade: {from_curr} -> {to_curr}, Amount: {current_amount:.2f}")
        
        # Calculate final profit
        results['final_amount'] = current_amount
        results['profit'] = current_amount - amount
        results['profit_percentage'] = (current_amount / amount - 1) * 100
        
        # Record profit for performance tracking
        self.performance.record_trade({
            'timestamp': datetime.now(),
            'expected_profit': expected_profit,
            'actual_profit': results['profit_percentage'] / 100,
            'slippage': expected_profit - (results['profit_percentage'] / 100)
        })
        
        if results['profit'] > 0:
            logger.info(f"Arbitrage successful! Profit: {results['profit']:.2f} ({results['profit_percentage']:.4f}%)")
            self.consecutive_losses = 0
        else:
            logger.warning(f"Arbitrage resulted in loss: {results['profit']:.2f} ({results['profit_percentage']:.4f}%)")
            self.consecutive_losses += 1
        
        return results
    
    def calculate_position_size(self, cycle_quality=1.0):
        """Calculate appropriate position size based on account balance and risk parameters."""
        account_balance = self.api.get_account_balance()
        
        # Get risk settings from config
        risk_settings = self.config.get('risk_per_trade', {
            'small_account': 0.01,    # 1% for accounts < 1000
            'medium_account': 0.02,   # 2% for accounts 1000-10000
            'large_account': 0.03     # 3% for accounts > 10000
        })
        
        # Base risk on account size
        if account_balance < 1000:
            risk_per_trade = risk_settings.get('small_account', 0.01)
        elif account_balance < 10000:
            risk_per_trade = risk_settings.get('medium_account', 0.02)
        else:
            risk_per_trade = risk_settings.get('large_account', 0.03)
        
        # Get session multipliers from config
        session_multipliers = self.config.get('session_multipliers', {
            'london_ny_overlap': 1.2,
            'tokyo_london_overlap': 1.1,
            'london': 1.0,
            'new_york': 1.0,
            'tokyo': 0.8,
            'low_liquidity': 0.5
        })
        
        # Adjust based on market session
        session_factor = session_multipliers.get(self.market_session, 1.0)
        
        # Adjust based on cycle quality (profit margin)
        quality_factor = min(max(cycle_quality * 10, 0.5), 2.0)
        
        # Adjust based on consecutive losses
        confidence_factor = max(0.5, 1.0 - (self.consecutive_losses * 0.2))
        
        # Calculate final position size
        position_size = account_balance * risk_per_trade * session_factor * quality_factor * confidence_factor
        
        # Ensure minimum position size
        min_position = 100  # Minimum position size
        position_size = max(position_size, min_position)
        
        # Ensure maximum position size (hard cap)
        max_position = account_balance * 0.1  # Never use more than 10% of account
        position_size = min(position_size, max_position)
        
        return position_size
    
    def check_circuit_breakers(self):
        """Check if any safety circuit breakers should be triggered."""
        # Check for consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            logger.warning(f"Circuit breaker: {self.consecutive_losses} consecutive losses")
            return False
        
        # Check for daily loss limit
        current_balance = self.api.get_account_balance()
        daily_loss = self.starting_balance - current_balance
        
        if daily_loss > self.daily_loss_limit:
            logger.warning(f"Circuit breaker: Daily loss limit exceeded. Loss: {daily_loss}")
            return False
        
        # Check for unusual slippage
        recent_trades = self.performance.get_recent_trades(3)
        if recent_trades:
            recent_slippage = [trade['slippage'] for trade in recent_trades]
            avg_slippage = sum(recent_slippage) / len(recent_slippage)
            
            if avg_slippage > 0.003:  # More than 0.3% slippage on average
                logger.warning(f"Circuit breaker: Unusual slippage detected. Avg: {avg_slippage:.4f}")
                return False
        
        return True
    
    def should_trade_now(self):
        """Determine if current market conditions are favorable for trading."""
        # Check circuit breakers first
        if not self.check_circuit_breakers():
            return False
        
        # Trade during optimal sessions
        if self.market_session in ['london_ny_overlap', 'tokyo_london_overlap', 'london', 'new_york']:
            return True
        
        # Be more selective during less liquid sessions
        if self.market_session in ['tokyo', 'low_liquidity']:
            # Only trade if we find very profitable opportunities
            return self.last_opportunity_time and (datetime.now() - self.last_opportunity_time).total_seconds() < 300
        
        return True
    
    def analyze_performance(self):
        """Analyze trading performance and adjust strategy parameters."""
        recent_trades = self.performance.get_recent_trades(5)
        if not recent_trades:
            return
        
        # Calculate profit metrics
        profits = [trade['actual_profit'] for trade in recent_trades]
        avg_profit = sum(profits) / len(profits)
        
        # Calculate slippage metrics
        slippages = [trade['slippage'] for trade in recent_trades]
        avg_slippage = sum(slippages) / len(slippages)
        
        logger.info(f"Performance analysis: Avg profit: {avg_profit*100:.4f}%, "
                   f"Avg slippage: {avg_slippage*100:.4f}%")
        
        # Adjust strategy based on performance
        if avg_profit < 0:
            # Increase profit threshold if losing money
            self.min_profit_threshold = min(0.005, self.min_profit_threshold * 1.2)
            logger.info(f"Adjusting profit threshold up to {self.min_profit_threshold*100:.4f}%")
        elif avg_profit > 0.002 and avg_slippage < 0.001:
            # If performing well with low slippage, can be more aggressive
            self.min_profit_threshold = max(0.0008, self.min_profit_threshold * 0.9)
            logger.info(f"Adjusting profit threshold down to {self.min_profit_threshold*100:.4f}%")
    
    def run(self, check_interval=3, max_runtime=None, demo_mode=False):
        """
        Main trading loop.
        
        Args:
            check_interval (int): Seconds between checks
            max_runtime (int): Maximum runtime in seconds (None for unlimited)
            demo_mode (bool): If True, simulate trades instead of executing them
        """
        logger.info(f"Starting arbitrage trading system with check interval {check_interval}s")
        logger.info(f"Initial account balance: {self.api.get_account_balance()}")
        logger.info(f"{'DEMO MODE: Simulating trades' if demo_mode else 'LIVE MODE: Executing real trades'}")
        
        self.is_trading_active = True
        start_time = datetime.now()
        
        try:
            while self.is_trading_active:
                # Check if maximum runtime reached
                if max_runtime and (datetime.now() - start_time).total_seconds() >= max_runtime:
                    logger.info(f"Maximum runtime of {max_runtime}s reached. Stopping.")
                    break
                
                # Adjust strategy based on current market session
                self.adjust_strategy_for_session()
                
                # Fetch latest exchange rates
                self.fetch_exchange_rates_parallel()
                
                # Only proceed if we should be trading now
                if not self.should_trade_now():
                    logger.info("Trading conditions not optimal. Waiting...")
                    time.sleep(check_interval * 2)
                    continue
                
                # Look for arbitrage opportunities in primary currencies
                cycles = []
                monitoring_currencies = self.config.get('currencies_to_monitor', ['USD', 'EUR', 'GBP'])
                for currency in monitoring_currencies:
                    currency_cycles = find_profitable_cycles(
                        self.exchange_rates, 
                        self.effective_rates,
                        start_currency=currency,
                        min_profit=self.min_profit_threshold
                    )
                    cycles.extend(currency_cycles)
                
                # Sort all cycles by profit
                cycles.sort(key=lambda x: x['effective_profit'], reverse=True)
                
                if cycles:
                    best_cycle = cycles[0]
                    logger.info(f"Found arbitrage opportunity: "
                               f"{best_cycle['effective_profit']*100:.4f}% profit")
                    
                    # Update last opportunity time
                    self.last_opportunity_time = datetime.now()
                    
                    # Determine position size based on cycle quality
                    position_size = self.calculate_position_size(cycle_quality=best_cycle['effective_profit'] * 100)
                    
                    # Execute the arbitrage cycle (or simulate in demo mode)
                    with self.trade_lock:  # Ensure thread safety
                        if demo_mode:
                            # Simulate trade with estimated slippage
                            expected_profit = best_cycle['effective_profit']
                            simulated_slippage = np.random.normal(0.001, 0.0005)  # Mean 0.1%, std 0.05%
                            actual_profit = max(0, expected_profit - simulated_slippage)
                            
                            logger.info(f"[DEMO] Simulated trade - Expected: {expected_profit*100:.4f}%, "
                                       f"Actual: {actual_profit*100:.4f}%, Slippage: {simulated_slippage*100:.4f}%")
                            
                            # Record simulated result
                            self.performance.record_trade({
                                'timestamp': datetime.now(),
                                'expected_profit': expected_profit,
                                'actual_profit': actual_profit,
                                'slippage': simulated_slippage
                            })
                            
                            if actual_profit > 0:
                                self.consecutive_losses = 0
                            else:
                                self.consecutive_losses += 1
                        else:
                            # Execute real trade
                            result = self.execute_arbitrage_cycle(best_cycle, position_size)
                            
                            if result['success']:
                                # Log results
                                logger.info(f"Trade complete - Profit: {result['profit_percentage']:.4f}%")
                                
                                # Analyze performance periodically
                                self.analyze_performance()
                            else:
                                logger.warning(f"Trade failed: {result.get('error', 'Unknown error')}")
                        
                        # Sleep a bit longer after trade/simulation
                        time.sleep(check_interval * 2)
                else:
                    logger.info("No profitable arbitrage opportunities found")
                    time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("Arbitrage trading stopped by user")
        except Exception as e:
            logger.error(f"Error in trading loop: {e}", exc_info=True)
        finally:
            final_balance = self.api.get_account_balance()
            total_profit = final_balance - self.starting_balance
            logger.info(f"Trading session complete. Final balance: {final_balance}")
            logger.info(f"Total profit/loss: {total_profit} ({total_profit/self.starting_balance*100:.2f}%)")
            
            # Save performance data for analysis
            self.performance.save_data()