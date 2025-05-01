"""
Performance tracking module.

This module handles tracking and analyzing trading performance.
"""
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("ArbitrageTrader")

class PerformanceTracker:
    def __init__(self, data_dir="./data"):
        """
        Initialize the performance tracker.
        
        Args:
            data_dir (str): Directory to store performance data
        """
        self.data_dir = data_dir
        self.trades = []
        self.start_time = datetime.now()
        
        # Create data directory if it doesn't exist
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
            except OSError as e:
                logger.error(f"Error creating data directory: {e}")
    
    def record_trade(self, trade_data):
        """
        Record a trade in the performance history.
        
        Args:
            trade_data (dict): Trade information including expected profit, actual profit, slippage
        """
        # Add timestamp if not already present
        if 'timestamp' not in trade_data:
            trade_data['timestamp'] = datetime.now().isoformat()
        
        self.trades.append(trade_data)
    
    def get_recent_trades(self, count=5):
        """
        Get the most recent trades.
        
        Args:
            count (int): Number of recent trades to retrieve
            
        Returns:
            list: List of recent trades
        """
        return self.trades[-count:] if len(self.trades) >= count else self.trades
    
    def calculate_metrics(self):
        """
        Calculate performance metrics.
        
        Returns:
            dict: Dictionary of performance metrics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'profitable_trades': 0,
                'loss_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'avg_slippage': 0,
                'total_profit': 0
            }
        
        # Calculate basic metrics
        total_trades = len(self.trades)
        profitable_trades = sum(1 for trade in self.trades if trade.get('actual_profit', 0) > 0)
        loss_trades = total_trades - profitable_trades
        
        # Win rate
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        # Profit/loss metrics
        profits = [t.get('actual_profit', 0) for t in self.trades if t.get('actual_profit', 0) > 0]
        losses = [t.get('actual_profit', 0) for t in self.trades if t.get('actual_profit', 0) <= 0]
        
        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Slippage
        slippages = [t.get('slippage', 0) for t in self.trades]
        avg_slippage = sum(slippages) / len(slippages) if slippages else 0
        
        # Total profit
        total_profit = sum(t.get('actual_profit', 0) for t in self.trades)
        
        return {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'loss_trades': loss_trades,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'avg_slippage': avg_slippage,
            'total_profit': total_profit
        }
    
    def save_data(self):
        """Save performance data to a file."""
        try:
            metrics = self.calculate_metrics()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.data_dir}/performance_{timestamp}.json"
            
            data = {
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'metrics': metrics,
                'trades': self.trades
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
                
            logger.info(f"Performance data saved to {filename}")
            
            # Also save a summary report
            self.generate_report(metrics, f"{self.data_dir}/summary_{timestamp}.txt")
            
        except Exception as e:
            logger.error(f"Error saving performance data: {e}")
    
    def generate_report(self, metrics, filename):
        """
        Generate a human-readable performance report.
        
        Args:
            metrics (dict): Performance metrics
            filename (str): File to save the report
        """
        try:
            with open(filename, 'w') as f:
                f.write("OANDA Arbitrage Trading System - Performance Report\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Report generated: {datetime.now()}\n")
                f.write(f"Trading session: {self.start_time} to {datetime.now()}\n")
                f.write(f"Duration: {datetime.now() - self.start_time}\n\n")
                
                f.write("Performance Metrics:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total trades: {metrics['total_trades']}\n")
                f.write(f"Profitable trades: {metrics['profitable_trades']} ({metrics['win_rate']*100:.2f}%)\n")
                f.write(f"Loss trades: {metrics['loss_trades']}\n")
                
                f.write(f"Average profit: {metrics['avg_profit']*100:.4f}%\n")
                f.write(f"Average loss: {metrics['avg_loss']*100:.4f}%\n")
                f.write(f"Average slippage: {metrics['avg_slippage']*100:.4f}%\n")
                f.write(f"Total profit: {metrics['total_profit']*100:.4f}%\n\n")
                
                f.write("Recent Trades:\n")
                f.write("-" * 20 + "\n")
                
                for i, trade in enumerate(self.trades[-10:]):  # Show last 10 trades
                    f.write(f"Trade {i+1}:\n")
                    f.write(f"  Timestamp: {trade.get('timestamp', 'N/A')}\n")
                    f.write(f"  Expected profit: {trade.get('expected_profit', 0)*100:.4f}%\n")
                    f.write(f"  Actual profit: {trade.get('actual_profit', 0)*100:.4f}%\n")
                    f.write(f"  Slippage: {trade.get('slippage', 0)*100:.4f}%\n")
                    f.write("\n")
            
            logger.info(f"Performance report saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")