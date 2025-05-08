"""
OANDA API client module.

This module handles all interactions with the OANDA REST API.
"""
import requests
import logging
from datetime import datetime

logger = logging.getLogger("ArbitrageTrader")

class OandaAPI:
    def __init__(self, api_key, account_id, practice_mode=True):
        """
        Initialize the OANDA API client.
        
        Args:
            api_key (str): Your OANDA API key
            account_id (str): Your OANDA account ID
            practice_mode (bool): If True, use practice environment, else use live
        """
        self.api_key = api_key
        self.account_id = account_id
        
        # Set the API URL based on practice or live mode
        if practice_mode:
            self.base_url = "https://api-fxpractice.oanda.com/v3"
        else:
            self.base_url = "https://api-fxtrade.oanda.com/v3"
        
        # API request headers
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_account_balance(self):
        """Get current account balance."""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/summary"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                return float(data['account']['balance'])
            else:
                logger.error(f"Failed to get account balance: {response.status_code}, {response.text}")
                return 10000.0  # Default fallback
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return 10000.0
    
    def get_tradable_instruments(self):
        """Get the list of tradable instruments."""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/instruments"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                return data['instruments']
            else:
                logger.error(f"Failed to get instruments: {response.status_code}, {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting instruments: {e}")
            return []
    
    def get_current_price(self, instrument):
        """
        Get the current price for a specific instrument.
        
        Args:
            instrument (str): Instrument name in format "BASE_QUOTE" (e.g., "EUR_USD")
            
        Returns:
            dict: Price data including bid, ask, and mid prices
        """
        try:
            url = f"{self.base_url}/instruments/{instrument}/candles"
            params = {
                "count": 1,
                "price": "MBA",  # Mid, Bid, Ask
                "granularity": "S5"  # 5-second candles
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'candles' in data and len(data['candles']) > 0:
                    candle = data['candles'][0]
                    
                    # Get bid, ask and mid prices
                    bid = float(candle['bid']['c'])
                    ask = float(candle['ask']['c'])
                    mid = float(candle['mid']['c'])
                    
                    return {
                        'bid': bid,
                        'ask': ask,
                        'mid': mid,
                        'spread': ask - bid,
                        'timestamp': datetime.fromisoformat(candle['time'].replace('Z', '+00:00'))
                    }
                else:
                    logger.warning(f"No candles returned for {instrument}")
                    return None
            else:
                logger.warning(f"Error fetching price for {instrument}: {response.status_code}, {response.text}")
                return None
        except Exception as e:
            logger.warning(f"Exception fetching price for {instrument}: {e}")
            return None
    
    def get_historical_candles(self, instrument, granularity="H1", count=50):
        """
        Get historical candles for an instrument.
        
        Args:
            instrument (str): Instrument name in format "BASE_QUOTE"
            granularity (str): Candle granularity (e.g., "M1", "H1", "D")
            count (int): Number of candles to retrieve
            
        Returns:
            list: List of candle data
        """
        try:
            url = f"{self.base_url}/instruments/{instrument}/candles"
            params = {
                "count": count,
                "price": "M",  # Mid prices
                "granularity": granularity
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'candles' in data:
                    return data['candles']
                else:
                    logger.warning(f"No candles returned for {instrument}")
                    return []
            else:
                logger.warning(f"Error fetching candles for {instrument}: {response.status_code}, {response.text}")
                return []
        except Exception as e:
            logger.warning(f"Exception fetching candles for {instrument}: {e}")
            return []
    
    def place_order(self, instrument, units):
        """
        Place a market order.
        
        Args:
            instrument (str): Instrument name in format "BASE_QUOTE"
            units (float): Number of units to trade (positive for buy, negative for sell)
            
        Returns:
            dict: Order response or None if failed
        """
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/orders"
            
            data = {
                "order": {
                    "units": str(int(units)),  # Convert to integer string
                    "instrument": instrument,
                    "timeInForce": "FOK",  # Fill Or Kill
                    "type": "MARKET",
                    "positionFill": "DEFAULT"
                }
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                order_response = response.json()
                logger.info(f"Order placed successfully: {instrument}, {units} units")
                return order_response
            else:
                logger.error(f"Order failed: {response.status_code}, {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def get_open_trades(self):
        """Get all open trades for the account."""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/openTrades"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('trades', [])
            else:
                logger.error(f"Failed to get open trades: {response.status_code}, {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []
    
    def close_trade(self, trade_id):
        """
        Close a specific trade.
        
        Args:
            trade_id (str): ID of the trade to close
            
        Returns:
            bool: True if successfully closed, False otherwise
        """
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/trades/{trade_id}/close"
            response = requests.put(url, headers=self.headers)
            
            if response.status_code == 200:
                logger.info(f"Successfully closed trade: {trade_id}")
                return True
            else:
                logger.error(f"Failed to close trade {trade_id}: {response.status_code}, {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error closing trade {trade_id}: {e}")
            return False
    
    def get_account_summary(self):
        """Get detailed account summary."""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/summary"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()['account']
            else:
                logger.error(f"Failed to get account summary: {response.status_code}, {response.text}")
                return {}
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {}