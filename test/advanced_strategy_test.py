"""
Advanced strategy example with the tick backtesting engine.
"""

import sys
import os
import pandas as pd
import numpy as np
from typing import Type

# Add the parent directory to path to import our modules (since we're now in test subfolder)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.data_bento import DataBento

def create_realistic_market_data(n_ticks: int = 1000, 
                                start_time: str = '2025-01-27T09:00:00.000000000Z',
                                base_price: float = 4.0,
                                symbol: str = 'DPRO') -> pd.DataFrame:
    """Create realistic market data with tight spreads."""
    np.random.seed(42)
    
    # Generate timestamps
    start_ts = pd.to_datetime(start_time)
    time_deltas = np.random.exponential(0.1, n_ticks)
    timestamps_recv = [start_ts + pd.Timedelta(milliseconds=np.sum(time_deltas[:i+1])) 
                       for i in range(n_ticks)]
    timestamps_event = [ts - pd.Timedelta(microseconds=np.random.randint(1, 1000)) 
                        for ts in timestamps_recv]
    
    # Generate prices (smaller movements)
    returns = np.random.normal(0, 0.00005, n_ticks)
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
    
    # Add realistic order book levels with tighter spreads
    for i in range(10):
        # Much tighter spreads (0.01-0.05% instead of 0.1-1%)
        spread = np.random.uniform(0.0001, 0.0005, n_ticks)
        bid_px = prices * (1 - spread * (i + 1) * 0.1)  # Smaller level separation
        ask_px = prices * (1 + spread * (i + 1) * 0.1)
        
        data[f'bid_px_{i:02d}'] = bid_px
        data[f'ask_px_{i:02d}'] = ask_px
        data[f'bid_sz_{i:02d}'] = np.random.randint(100, 1000, n_ticks) if i < 3 else np.random.choice([0, 100, 200], n_ticks)
        data[f'ask_sz_{i:02d}'] = np.random.randint(100, 1000, n_ticks) if i < 3 else np.random.choice([0, 100, 200], n_ticks)
        data[f'bid_ct_{i:02d}'] = np.random.randint(0, 5, n_ticks)
        data[f'ask_ct_{i:02d}'] = np.random.randint(0, 5, n_ticks)
    
    return pd.DataFrame(data)


class MomentumStrategy:
    """A momentum strategy that uses tick-level price movements and order book data."""
    
    def __init__(self, data, lookback_window=20):
        self.data = data
        self.lookback_window = lookback_window
        self.position = 0
        self.cash = 10000
        self.trades = []
        self.current_idx = 0
        self.price_history = []
        
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
    
    def get_order_book_imbalance(self):
        """Calculate order book imbalance (bid depth vs ask depth)."""
        if self.current_idx < len(self.data):
            row = self.data.iloc[self.current_idx]
            bid_depth = sum(row[f'bid_sz_{i:02d}'] for i in range(3))  # Top 3 levels
            ask_depth = sum(row[f'ask_sz_{i:02d}'] for i in range(3))
            total_depth = bid_depth + ask_depth
            if total_depth > 0:
                return (bid_depth - ask_depth) / total_depth  # Positive = more bids
            return 0
        return 0
    
    def get_momentum_signal(self):
        """Calculate momentum based on recent price changes."""
        if len(self.price_history) < self.lookback_window:
            return 0
        
        recent_prices = self.price_history[-self.lookback_window:]
        if len(recent_prices) < 2:
            return 0
            
        # Calculate momentum as percentage change
        momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        return momentum
    
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
        if not price:
            return
            
        # Update price history
        self.price_history.append(price)
        if len(self.price_history) > self.lookback_window * 2:
            self.price_history = self.price_history[-self.lookback_window * 2:]
        
        spread = self.get_current_spread()
        order_imbalance = self.get_order_book_imbalance()
        momentum = self.get_momentum_signal()
        
        # Strategy signals
        spread_ok = spread and spread < 0.01  # Spread less than 1 cent
        strong_momentum_up = momentum > 0.0001  # 0.01% positive momentum
        strong_momentum_down = momentum < -0.0001  # 0.01% negative momentum
        order_book_bullish = order_imbalance > 0.1  # More bids than asks
        order_book_bearish = order_imbalance < -0.1  # More asks than bids
        
        # Entry signals
        if (spread_ok and strong_momentum_up and order_book_bullish and 
            self.position == 0 and len(self.price_history) >= self.lookback_window):
            if self.buy(100):
                print(f"Tick {self.current_idx}: BUY at {price:.4f} | momentum={momentum:.4f}, imbalance={order_imbalance:.2f}")
        
        # Exit signals
        elif (strong_momentum_down or order_book_bearish) and self.position > 0:
            if self.sell(100):
                print(f"Tick {self.current_idx}: SELL at {price:.4f} | momentum={momentum:.4f}, imbalance={order_imbalance:.2f}")
    
    def run(self):
        """Run strategy on all ticks."""
        print(f"Running momentum strategy on {len(self.data)} ticks (lookback={self.lookback_window})...")
        
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


def test_momentum_strategy():
    """Test the momentum strategy with realistic market data."""
    print("Momentum Strategy Backtesting Test")
    print("=" * 50)
    
    # Create realistic market data with tighter spreads
    #market_data = create_realistic_market_data(3000, base_price=4.0)
    csv_file = "C:\\Users\\fy37bby\\user\\dev\misc\\backtest\\rsc\\XNAS-20260127-WTVN5DQMQ6\\xnas-itch-20260115.mbp-10_ONDS.csv"
    bento_loader = DataBento()
    market_data = bento_loader.load_csv(csv_file)
    print(f"Created {len(market_data)} ticks with {len(market_data.columns)} columns")
    
    # Show sample data
    print("\nSample market data:")
    sample_cols = ['ts_event', 'price', 'size', 'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00']
    print(market_data[sample_cols].head())
    
    # Show spread analysis
    spreads = market_data['ask_px_00'] - market_data['bid_px_00']
    print(f"\nSpread statistics:")
    print(f"Average spread: {spreads.mean():.4f}")
    print(f"Spread range: {spreads.min():.4f} - {spreads.max():.4f}")
    print(f"Spreads < 0.01: {(spreads < 0.01).sum()}/{len(spreads)} ({(spreads < 0.01).mean()*100:.1f}%)")
    
    # Run strategy
    strategy = MomentumStrategy(market_data, lookback_window=50)
    results = strategy.run()
    
    # Display results
    print("\n" + "=" * 50)
    print("BACKTEST RESULTS")
    print("=" * 50)
    print(f"Initial Cash: ${results['initial_cash']:,.2f}")
    print(f"Final Cash: ${results['final_cash']:,.2f}")
    print(f"Position: {results['position']} shares")
    print(f"Final Equity: ${results['final_equity']:,.2f}")
    print(f"Total Return: {results['total_return']:.2f}%")
    print(f"Number of Trades: {results['num_trades']}")
    
    if results['trades']:
        print("\nTrade Analysis:")
        buy_trades = [t for t in results['trades'] if t['type'] == 'BUY']
        sell_trades = [t for t in results['trades'] if t['type'] == 'SELL']
        print(f"Buy trades: {len(buy_trades)}")
        print(f"Sell trades: {len(sell_trades)}")
        
        if buy_trades and sell_trades:
            avg_buy_price = np.mean([t['price'] for t in buy_trades])
            avg_sell_price = np.mean([t['price'] for t in sell_trades])
            print(f"Average buy price: ${avg_buy_price:.4f}")
            print(f"Average sell price: ${avg_sell_price:.4f}")
            print(f"Price difference: {((avg_sell_price - avg_buy_price) / avg_buy_price * 100):.3f}%")
        
        # Show recent trades
        if len(results['trades']) > 0:
            print("\nRecent trades:")
            for trade in results['trades'][-5:]:  # Last 5 trades
                print(f"  {trade['type']} {trade['size']} @ ${trade['price']:.4f} (tick {trade['idx']})")
    
    # Market analysis
    print("\n" + "-" * 40)
    print("Market Data Analysis")
    print("-" * 40)
    
    # Price movement
    price_change = (market_data['price'].iloc[-1] - market_data['price'].iloc[0]) / market_data['price'].iloc[0] * 100
    print(f"Total price movement: {price_change:.3f}%")
    print(f"Price range: ${market_data['price'].min():.4f} - ${market_data['price'].max():.4f}")
    
    # Order book depth
    total_bid_depth = market_data[[f'bid_sz_{i:02d}' for i in range(3)]].sum(axis=1)
    total_ask_depth = market_data[[f'ask_sz_{i:02d}' for i in range(3)]].sum(axis=1)
    print(f"Average bid depth (levels 0-2): {total_bid_depth.mean():.0f}")
    print(f"Average ask depth (levels 0-2): {total_ask_depth.mean():.0f}")
    
    # Time analysis
    time_span = market_data['ts_event'].max() - market_data['ts_event'].min()
    print(f"Data time span: {time_span}")
    
    return results


if __name__ == "__main__":
    test_momentum_strategy()