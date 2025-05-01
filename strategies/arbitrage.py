"""
Arbitrage trading strategies module.

This module contains functions for detecting and analyzing arbitrage opportunities.
"""
import logging

logger = logging.getLogger("ArbitrageTrader")

def find_profitable_cycles(exchange_rates, effective_rates, start_currency='USD', 
                         max_cycle_length=3, min_profit=0.001):
    """
    Find all profitable currency cycles starting with a specific currency.
    
    Args:
        exchange_rates (dict): Dictionary of exchange rates with metadata
        effective_rates (dict): Dictionary of effective rates for trading
        start_currency (str): Currency to start cycles from
        max_cycle_length (int): Maximum number of currencies in a cycle
        min_profit (float): Minimum profit threshold (0.001 = 0.1%)
        
    Returns:
        list: List of profitable cycles with their details
    """
    if not exchange_rates:
        return []
    
    # Get all currencies that have exchange rate data
    currencies = set()
    for base, quote in exchange_rates.keys():
        currencies.add(base)
        currencies.add(quote)
    
    # Get pairs with acceptable spreads
    valid_pairs = {}
    for pair, data in exchange_rates.items():
        if 'spread' in data and data['spread'] <= 0.0010:  # Only consider pairs with spreads under 10 pips
            valid_pairs[pair] = data
    
    profitable_cycles = []
    
    def dfs(current, path, visited, depth=0):
        # Limit cycle length for efficiency
        if depth >= max_cycle_length:
            if current == start_currency:
                # Calculate cycle profit with effective rates (accounting for spread)
                profit_ratio = 1.0
                cycle_pairs = []
                
                for i in range(len(path)):
                    from_curr = path[i]
                    to_curr = path[(i + 1) % len(path)]
                    pair = (from_curr, to_curr)
                    
                    if pair in effective_rates:
                        rate = effective_rates[pair]
                        profit_ratio *= rate
                        cycle_pairs.append((from_curr, to_curr))
                    else:
                        return  # Skip if any pair doesn't exist
                
                # Account for estimated execution costs (commission + slippage)
                transaction_cost_per_trade = 0.0001  # 1 pip per trade as a conservative estimate
                total_transaction_cost = transaction_cost_per_trade * len(cycle_pairs)
                effective_profit = profit_ratio - 1.0 - total_transaction_cost
                
                if effective_profit > min_profit:
                    cycle_info = {
                        'pairs': cycle_pairs,
                        'profit_ratio': profit_ratio,
                        'effective_profit': effective_profit
                    }
                    profitable_cycles.append(cycle_info)
            return
        
        if current in visited and (current != start_currency or depth == 0):
            return
        
        # Add current currency to visited
        new_visited = visited.copy()
        new_visited.add(current)
        
        # Explore all possible next currencies
        for next_curr in currencies:
            pair = (current, next_curr)
            if pair in effective_rates:
                new_path = path + [current]
                dfs(next_curr, new_path, new_visited, depth + 1)
    
    # Start DFS from the specified currency
    dfs(start_currency, [], set(), 0)
    
    # Sort by effective profit in descending order
    profitable_cycles.sort(key=lambda x: x['effective_profit'], reverse=True)
    
    return profitable_cycles

def calculate_cross_rate_opportunities(exchange_rates):
    """
    Find potential arbitrage opportunities through cross rates.
    
    Args:
        exchange_rates (dict): Dictionary of exchange rates with metadata
        
    Returns:
        list: List of cross rate opportunities
    """
    opportunities = []
    
    # Find all currency triplets where we have all three pairs
    for base_curr in set(curr[0] for curr in exchange_rates.keys()):
        for mid_curr in set(curr[1] for curr in exchange_rates.keys() if curr[0] == base_curr):
            for quote_curr in set(curr[1] for curr in exchange_rates.keys() if curr[0] == mid_curr):
                # Check if we have the direct rate too
                if (base_curr, quote_curr) in exchange_rates:
                    # Calculate rates
                    direct_rate = exchange_rates[(base_curr, quote_curr)]['mid']
                    
                    # First leg: base -> mid
                    first_leg = exchange_rates[(base_curr, mid_curr)]['mid']
                    
                    # Second leg: mid -> quote
                    second_leg = exchange_rates[(mid_curr, quote_curr)]['mid']
                    
                    # Cross rate
                    cross_rate = first_leg * second_leg
                    
                    # Calculate discrepancy
                    discrepancy = abs(direct_rate - cross_rate) / direct_rate
                    
                    # If significant discrepancy
                    if discrepancy > 0.0005:  # 0.05% or greater
                        opportunity = {
                            'base': base_curr,
                            'mid': mid_curr,
                            'quote': quote_curr,
                            'direct_rate': direct_rate,
                            'cross_rate': cross_rate,
                            'discrepancy': discrepancy
                        }
                        opportunities.append(opportunity)
    
    # Sort by discrepancy
    opportunities.sort(key=lambda x: x['discrepancy'], reverse=True)
    
    return opportunities

def triangular_arbitrage_opportunities(exchange_rates, min_profit=0.001):
    """
    Find triangular arbitrage opportunities.
    
    Args:
        exchange_rates (dict): Dictionary of exchange rates with metadata
        min_profit (float): Minimum profit threshold (0.001 = 0.1%)
        
    Returns:
        list: List of triangular arbitrage opportunities
    """
    opportunities = []
    
    # Get all currencies
    currencies = set()
    for base, quote in exchange_rates.keys():
        currencies.add(base)
        currencies.add(quote)
    
    # Check each possible triangle
    for base_curr in currencies:
        for mid_curr in currencies:
            if mid_curr == base_curr:
                continue
                
            for quote_curr in currencies:
                if quote_curr == base_curr or quote_curr == mid_curr:
                    continue
                
                # Check if we have all pairs needed
                pairs = [
                    (base_curr, mid_curr),
                    (mid_curr, quote_curr),
                    (quote_curr, base_curr)
                ]
                
                if all(pair in exchange_rates for pair in pairs):
                    # Calculate rates using mid price
                    rate1 = exchange_rates[pairs[0]]['mid']
                    rate2 = exchange_rates[pairs[1]]['mid']
                    rate3 = exchange_rates[pairs[2]]['mid']
                    
                    # Calculate profit ratio
                    profit_ratio = rate1 * rate2 * rate3
                    
                    # Check if profitable
                    if profit_ratio > 1 + min_profit:
                        opportunity = {
                            'base': base_curr,
                            'mid': mid_curr,
                            'quote': quote_curr,
                            'profit_ratio': profit_ratio,
                            'profit_percentage': (profit_ratio - 1) * 100,
                            'pairs': pairs
                        }
                        opportunities.append(opportunity)
    
    # Sort by profit
    opportunities.sort(key=lambda x: x['profit_ratio'], reverse=True)
    
    return opportunities