"""
Simple strategy test without full engine dependencies.
"""

import sys
import os
import pandas as pd
import numpy as np
from typing import Type

# Add the current directory to path to import our modules
sys.path.insert(0, os.path.dirname(__file__))

def create_sample_market_data(n_ticks: int = 1000, 
                             start_time: str = '2025-01-27T09:00:00.000000000Z',
                             base_price: float = 4.0,
                             symbol: str = 'DPRO') -> pd.DataFrame:
    """Create sample market data matching user's format."""
    np.random.seed(42)
    
    # Generate timestamps
    start_ts = pd.to_datetime(start_time)
    time_deltas = np.random.exponential(0.1, n_ticks)
    timestamps_recv = [start_ts + pd.Timedelta(milliseconds=np.sum(time_deltas[:i+1])) 
                       for i in range(n_ticks)]
    timestamps_event = [ts - pd.Timedelta(microseconds=np.random.randint(1, 1000)) 
                        for ts in timestamps_recv]
    
    # Generate prices (random walk)
    returns = np.random.normal(0, 0.0001, n_ticks)
    prices = base_price * np.cumprod(1 + returns)
    sizes = np.random.choice([50, 100, 150, 200, 250], n_ticks)
    
    # Create main data structure
    data = {
        'ts_recv': timestamps_recv,
        'ts_event': timestamps_event,
        'rtype': np.full(n_ticks, 10),
        'publisher_id': np.full(n_ticks, 2),
        'instrument_id': np.full(n_ticks, 4559),
        'action': np.random.choice(['A', 'C', 'M', 'D'], n_ticks),
        'side': np.random.choice(['B', 'A', 'N'], n_ticks),
        'depth': np.random.randint(0, 10, n_ticks),
        'price': prices,
        'size': sizes,
        'flags': np.random.randint(128, 132, n_ticks),
        'ts_in_delta': np.random.randint(100000, 200000, n_ticks),
        'sequence': np.arange(826376, 826376 + n_ticks),
        'symbol': [symbol] * n_ticks,
    }
    
    # Add order book levels
    for i in range(10):
        spread = np.random.uniform(0.0001, 0.001, n_ticks)
        bid_px = prices * (1 - spread * (i + 1))
        ask_px = prices * (1 + spread * (i + 1))
        
        data[f'bid_px_{i:02d}'] = bid_px
        data[f'ask_px_{i:02d}'] = ask_px
        data[f'bid_sz_{i:02d}'] = np.random.randint(50, 500, n_ticks) if i < 3 else np.random.choice([0, 100, 200], n_ticks)
        data[f'ask_sz_{i:02d}'] = np.random.randint(50, 500, n_ticks) if i < 3 else np.random.choice([0, 100, 200], n_ticks)
        data[f'bid_ct_{i:02d}'] = np.random.randint(0, 5, n_ticks)
        data[f'ask_ct_{i:02d}'] = np.random.randint(0, 5, n_ticks)
    
    return pd.DataFrame(data)


class SimpleStrategy:
    """A simple strategy class to demonstrate tick-by-tick processing."""
    
    def __init__(self, data):
        self.data = data
        self.position = 0
        self.cash = 10000
        self.trades = []
        self.current_idx = 0
        
    def get_current_price(self):
        """Get current tick price."""
        if self.current_idx < len(self.data):
            return self.data['price'].iloc[self.current_idx]
        return None
    
    def get_current_spread(self):
        """Get current bid-ask spread."""
        if self.current_idx < len(self.data):
            row = self.data.iloc[self.current_idx]
            return row['ask_px_00'] - row['bid_px_00']
        return None
    
    def get_order_book_depth(self, level=0):
        """Get order book depth at specific level."""
        if self.current_idx < len(self.data):
            row = self.data.iloc[self.current_idx]
            bid_size = row[f'bid_sz_{level:02d}']
            ask_size = row[f'ask_sz_{level:02d}']
            return bid_size, ask_size
        return 0, 0
    
    def buy(self, size=100):
        """Execute buy order."""
        price = self.get_current_price()
        if price and self.cash >= price * size:
            self.position += size
            self.cash -= price * size
            self.trades.append({
                'type': 'BUY',
                'size': size,
                'price': price,
                'timestamp': self.data['ts_event'].iloc[self.current_idx],
                'idx': self.current_idx
            })
            return True
        return False
    
    def sell(self, size=100):
        """Execute sell order."""
        price = self.get_current_price()
        if price and self.position >= size:
            self.position -= size
            self.cash += price * size
            self.trades.append({
                'type': 'SELL',
                'size': size,
                'price': price,
                'timestamp': self.data['ts_event'].iloc[self.current_idx],
                'idx': self.current_idx
            })
            return True
        return False
    
    def next(self):
        """Strategy logic for each tick."""
        price = self.get_current_price()
        spread = self.get_current_spread()
        bid_depth, ask_depth = self.get_order_book_depth(0)
        
        if not price:
            return
        
        # Simple strategy: buy on low spread + high depth, sell on high spread
        if spread and spread < 0.01 and bid_depth > 200 and self.position == 0:
            self.buy(100)
            print(f"Tick {self.current_idx}: BUY at {price:.4f}, spread={spread:.4f}, depth={bid_depth}")
            
        elif spread and spread > 0.02 and self.position > 0:
            self.sell(100)
            print(f"Tick {self.current_idx}: SELL at {price:.4f}, spread={spread:.4f}")
    
    def run(self):
        """Run strategy on all ticks."""
        print(f"Running simple strategy on {len(self.data)} ticks...")
        
        for i in range(len(self.data)):
            self.current_idx = i
            self.next()
        
        # Calculate final equity
        final_price = self.data['price'].iloc[-1]
        final_equity = self.cash + self.position * final_price
        
        results = {
            'initial_cash': 10000,
            'final_cash': self.cash,
            'position': self.position,
            'final_equity': final_equity,
            'total_return': (final_equity - 10000) / 10000 * 100,
            'num_trades': len(self.trades),
            'trades': self.trades
        }
        
        return results


def test_simple_strategy():
    """Test the simple strategy with market data."""
    print("Simple Strategy Backtesting Test")
    print("=" * 50)
    
    # Create market data
    market_data = create_sample_market_data(2000, base_price=100.0)
    print(f"Created {len(market_data)} ticks with {len(market_data.columns)} columns")
    
    # Show sample data
    print("\nSample market data:")
    print(market_data[['ts_event', 'price', 'size', 'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00']].head())
    
    # Run strategy
    strategy = SimpleStrategy(market_data)
    results = strategy.run()
    
    # Display results
    print("\n" + "=" * 40)
    print("BACKTEST RESULTS")
    print("=" * 40)
    print(f"Initial Cash: ${results['initial_cash']:,.2f}")
    print(f"Final Cash: ${results['final_cash']:,.2f}")
    print(f"Position: {results['position']} shares")
    print(f"Final Equity: ${results['final_equity']:,.2f}")
    print(f"Total Return: {results['total_return']:.2f}%")
    print(f"Number of Trades: {results['num_trades']}")
    
    if results['trades']:
        print("\nTrade Summary:")
        buy_trades = [t for t in results['trades'] if t['type'] == 'BUY']
        sell_trades = [t for t in results['trades'] if t['type'] == 'SELL']
        print(f"Buy trades: {len(buy_trades)}")
        print(f"Sell trades: {len(sell_trades)}")
        
        if buy_trades:
            avg_buy_price = np.mean([t['price'] for t in buy_trades])
            print(f"Average buy price: ${avg_buy_price:.4f}")
        
        if sell_trades:
            avg_sell_price = np.mean([t['price'] for t in sell_trades])
            print(f"Average sell price: ${avg_sell_price:.4f}")
    
    # Test order book access
    print("\n" + "-" * 30)
    print("Order Book Analysis")
    print("-" * 30)
    
    # Calculate average spreads
    spreads = market_data['ask_px_00'] - market_data['bid_px_00']
    print(f"Average spread: {spreads.mean():.4f}")
    print(f"Spread range: {spreads.min():.4f} - {spreads.max():.4f}")
    
    # Analyze depth
    total_bid_depth = market_data[[f'bid_sz_{i:02d}' for i in range(3)]].sum(axis=1)
    total_ask_depth = market_data[[f'ask_sz_{i:02d}' for i in range(3)]].sum(axis=1)
    print(f"Average bid depth (levels 0-2): {total_bid_depth.mean():.0f}")
    print(f"Average ask depth (levels 0-2): {total_ask_depth.mean():.0f}")
    
    # Time analysis
    time_span = market_data['ts_event'].max() - market_data['ts_event'].min()
    print(f"Data time span: {time_span}")
    print(f"Average tick interval: {time_span.total_seconds() / len(market_data) * 1000:.1f} ms")
    
    return results


if __name__ == "__main__":
    test_simple_strategy()