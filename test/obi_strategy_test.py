import os
import sys


# Add the parent directory to path to import our modules (since we're now in test subfolder)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.tick_backtesting import TickBacktest
from strategy.strategy import ObiStrategy
from strategy.price_strategy import PriceStrategy
from data.data_bento import DataBento

def test_obi_strategy():
    """Test the Obi strategy with realistic market data."""
    print("Obi Strategy Backtesting Test")
    print("=" * 50)
    
    csv_file = "C:\\Users\\Derba\\Documents\\projects\\rsc\\ONDS\\xnas-itch-20260126.mbp-10_ONDS.csv"
    csv_file = "C:\\Users\\fy37bby\\user\\dev\\misc\\backtest\\rsc\\XNAS-20260127-WTVN5DQMQ6\\xnas-itch-20260116.mbp-10_ONDS.csv"
    #csv_file = "C:\\Users\\fy37bby\\user\\dev\\misc\\backtest\\rsc\\XNAS-20260127-WTVN5DQMQ6\\xnas-itch-20250508.mbp-10_ONDS.csv"
    bento_loader = DataBento()
    market_data = bento_loader.load_csv(csv_file)
    market_data = bento_loader.filter_data(market_data, symbol=None, exclude_cancel=False, depth_level=None, exclude_morning_minutes=10, min_size=20)
    print(f"Created {len(market_data)} ticks with {len(market_data.columns)} columns")
    
    # Run strategy
    #bt = TickBacktest(market_data, ObiStrategy, cash=10000, commission=.002, exclusive_orders=True, finalize_trades=True)
    bt = TickBacktest(market_data, PriceStrategy, cash=10000, commission=.002, exclusive_orders=True, finalize_trades=True)
    stats = bt.run()
    #bt.strategy.plot_obi_change_history(granularity_seconds=10)
    bt.strategy.plot_results()
    
    # Display results
    print("\n" + "=" * 50)
    print("BACKTEST RESULTS")
    print("=" * 50)
    print(stats)
    return stats


if __name__ == "__main__":
    test_obi_strategy()