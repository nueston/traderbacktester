"""
Tick-based backtesting engine that converts tick data to OHLCV format
and supports the same Strategy interface as the original backtesting engine.
"""

from __future__ import annotations

import warnings
from typing import Optional, Union, Tuple, Type

import numpy as np
import pandas as pd

from .backtesting import Backtest as _OriginalBacktest, Strategy
from .tick_util import _EnhancedData


class TickBacktest(_OriginalBacktest):
    """
    Tick-based backtest engine that converts tick data to OHLCV format.
    
    This class extends the original Backtest class to handle tick-based data
    with columns: ts_event, price, size, and optionally other columns.
    
    The tick data is converted to OHLCV format with configurable time intervals
    before running the backtest using the same Strategy interface.
    """
    
    def __init__(self,
                 tick_data: pd.DataFrame,
                 strategy: Type[Strategy],
                 *,
                 time_interval: str = '1min',  # Only used for plotting
                 cash: float = 10_000,
                 spread: float = .0,
                 commission: Union[float, Tuple[float, float]] = .0,
                 margin: float = 1.,
                 trade_on_close=False,
                 hedging=False,
                 exclusive_orders=False,
                 finalize_trades=False,
                 ):
        """
        Initialize tick-based backtest.
        
        Parameters:
        -----------
        tick_data : pd.DataFrame
            DataFrame with required columns: 'ts_event', 'price', 'size'
            and optional additional columns that will be preserved.
        time_interval : str, default '1min'
            Time interval for plotting only (e.g., '1min', '5min', '1h')
        **kwargs
            Other parameters passed to the base Backtest class
        """
        # Validate tick data
        self._validate_tick_data(tick_data)
        
        # Store original tick data and conversion parameters
        self._original_tick_data = tick_data.copy()
        self._time_interval = time_interval
        self._strategy_instance = None  # Store strategy instance after run
        
        # Prepare tick data for backtesting (ensure proper datetime index)
        processed_tick_data = self._prepare_tick_data(tick_data)
        
        # Initialize the base class with processed tick data
        super().__init__(
            data=processed_tick_data,
            strategy=strategy,
            cash=cash,
            spread=spread,
            commission=commission,
            margin=margin,
            trade_on_close=trade_on_close,
            hedging=hedging,
            exclusive_orders=exclusive_orders,
            finalize_trades=finalize_trades,
        )
    
    def run(self, **kwargs) -> pd.Series:
        """
        Run the backtest and store strategy instance for later access.
        
        Returns `pd.Series` with results and statistics.
        Keyword arguments are interpreted as strategy parameters.
        """
        # Run the original backtest
        results = super().run(**kwargs)
        
        # Store the strategy instance for external access
        if hasattr(results, '_strategy'):
            self._strategy_instance = results._strategy
        
        return results
    
    @property
    def strategy(self):
        """
        Access the strategy instance after running the backtest.
        
        Returns:
        --------
        Strategy instance or None if backtest hasn't been run yet
        """
        return self._strategy_instance
    
    def get_strategy_instance(self):
        """
        Get the strategy instance with all custom methods available.
        
        Returns:
        --------
        Strategy instance or None if backtest hasn't been run yet
        """
        return self._strategy_instance
    
    def _validate_tick_data(self, tick_data: pd.DataFrame):
        """Validate that tick data has required columns."""
        if not isinstance(tick_data, pd.DataFrame):
            raise TypeError("`tick_data` must be a pandas.DataFrame")
        
        # Check for timestamp column (prefer ts_event, fallback to ts_recv)
        timestamp_cols = {'ts_event', 'ts_recv'}
        available_timestamp_cols = timestamp_cols.intersection(tick_data.columns)
        if not available_timestamp_cols:
            raise ValueError(f"tick_data must contain at least one timestamp column: {timestamp_cols}")
        
        # Check for price and size columns
        if 'price' not in tick_data.columns:
            raise ValueError("tick_data must contain 'price' column")
        
        if 'size' not in tick_data.columns:
            raise ValueError("tick_data must contain 'size' column")
        
        if len(tick_data) == 0:
            raise ValueError('tick_data is empty')
        
        # Check for non-null prices (sizes can be 0 for some market data)
        if tick_data['price'].isnull().values.any():
            raise ValueError('Some price values are missing (NaN). '
                           'Please clean the data first.')
        
        # Only check positive prices for non-null values
        valid_prices = tick_data['price'].dropna()
        if len(valid_prices) > 0 and not np.all(valid_prices > 0):
            raise ValueError('All non-null prices must be positive')
        
    def _prepare_tick_data(self, tick_data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare tick data for backtesting without time-based sampling.
        
        Parameters:
        -----------
        tick_data : pd.DataFrame
            Raw tick data with market data format
            
        Returns:
        --------
        pd.DataFrame
            Prepared tick data with proper datetime index and required columns
        """
        # Work with a copy
        tick_data = tick_data.copy()
        
        # Determine which timestamp column to use
        timestamp_col = 'ts_event' if 'ts_event' in tick_data.columns else 'ts_recv'
        
        # Ensure timestamp is datetime
        if not isinstance(tick_data[timestamp_col], pd.DatetimeIndex):
            tick_data[timestamp_col] = pd.to_datetime(tick_data[timestamp_col])
        
        # Set timestamp as index
        if tick_data.index.name != timestamp_col:
            tick_data = tick_data.set_index(timestamp_col)
        
        # Sort by timestamp to ensure proper ordering
        tick_data = tick_data.sort_index()
        
        # Filter out rows with null prices (but keep other columns)
        valid_price_mask = tick_data['price'].notna()
        if not valid_price_mask.all():
            print(f"Warning: Filtering out {(~valid_price_mask).sum()} rows with null prices")
            tick_data = tick_data[valid_price_mask]
        
        # Create OHLCV columns that map to tick data for compatibility
        # Each tick represents a single "bar" with O=H=L=C=price
        tick_data['Open'] = tick_data['price']
        tick_data['High'] = tick_data['price'] 
        tick_data['Low'] = tick_data['price']
        tick_data['Close'] = tick_data['price']
        tick_data['Volume'] = tick_data['size'].fillna(0)  # Handle null sizes
        
        return tick_data
    
    def _convert_ticks_to_ohlcv(self, tick_data: pd.DataFrame, time_interval: str) -> pd.DataFrame:
        """
        Convert tick data to OHLCV format with specified time interval.
        
        Parameters:
        -----------
        tick_data : pd.DataFrame
            Tick data with timestamp, price, size columns
        time_interval : str
            Time interval for resampling (e.g., '1min', '5min', '1h')
            
        Returns:
        --------
        pd.DataFrame
            OHLCV data with additional columns from original tick data
        """
        # Work with a copy
        tick_data = tick_data.copy()
        
        # Determine which timestamp column to use
        timestamp_col = 'ts_event' if 'ts_event' in tick_data.columns else 'ts_recv'
        
        # Ensure timestamp is datetime
        if not isinstance(tick_data[timestamp_col], pd.DatetimeIndex):
            tick_data[timestamp_col] = pd.to_datetime(tick_data[timestamp_col])
        
        # Set timestamp as index for resampling
        if tick_data.index.name != timestamp_col:
            tick_data = tick_data.set_index(timestamp_col)
        
        # Sort by timestamp to ensure proper ordering
        tick_data = tick_data.sort_index()
        
        # Filter valid price data for OHLCV calculation
        valid_data = tick_data[tick_data['price'].notna()].copy()
        
        if len(valid_data) == 0:
            raise ValueError('No valid price data for OHLCV conversion')
        
        # Create OHLCV aggregation - only use columns that exist
        ohlcv_agg = {
            'Open': ('price', 'first'),
            'High': ('price', 'max'),
            'Low': ('price', 'min'),
            'Close': ('price', 'last'),
            'Volume': ('size', lambda x: x.fillna(0).sum()),
        }
        
        # Add aggregation rules for other columns
        other_columns = set(valid_data.columns) - {'price', 'size'}
        for col in other_columns:
            if col in valid_data.columns:
                if pd.api.types.is_numeric_dtype(valid_data[col]):
                    # For numeric columns, take mean (ignoring NaN)
                    ohlcv_agg[col] = (col, lambda x: x.dropna().mean() if len(x.dropna()) > 0 else np.nan)
                else:
                    # For non-numeric columns, take last non-null value
                    ohlcv_agg[col] = (col, lambda x: x.dropna().iloc[-1] if len(x.dropna()) > 0 else None)
        
        # Perform resampling
        ohlcv_data = valid_data.resample(time_interval).agg(ohlcv_agg)
        
        # Flatten column names if they are MultiIndex
        if isinstance(ohlcv_data.columns, pd.MultiIndex):
            ohlcv_data.columns = ohlcv_data.columns.get_level_values(0)
        
        # Remove rows with no data (NaN in Open, High, Low, Close)
        ohlcv_data = ohlcv_data.dropna(subset=['Open', 'High', 'Low', 'Close'])
        
        # Ensure Volume is not NaN (set to 0 if missing)
        ohlcv_data['Volume'] = ohlcv_data['Volume'].fillna(0)
        
        if len(ohlcv_data) == 0:
            raise ValueError(f'No data remains after {time_interval} resampling. '
                           'Try a smaller time interval.')
        
        return ohlcv_data
    
    def get_ohlcv_data(self, time_interval: str = None) -> pd.DataFrame:
        """
        Return OHLCV data converted from tick data using specified time interval.
        This is mainly used for plotting purposes.
        
        Parameters:
        -----------
        time_interval : str, optional
            Time interval for aggregation. If None, uses the default from init.
            
        Returns:
        --------
        pd.DataFrame
            OHLCV data aggregated at specified time interval
        """
        if time_interval is None:
            time_interval = self._time_interval
        
        return self._convert_ticks_to_ohlcv(self._original_tick_data, time_interval)
    
    def get_original_tick_data(self) -> pd.DataFrame:
        """Return the original tick data."""
        return self._original_tick_data.copy()
    
    def plot_tick_data(self, 
                       max_ticks: int = 10000,
                       show_size: bool = True,
                       **plot_kwargs):
        """
        Plot the original tick data.
        
        Parameters:
        -----------
        max_ticks : int
            Maximum number of ticks to plot (for performance)
        show_size : bool
            Whether to show size as scatter point sizes
        **plot_kwargs
            Additional arguments for plotting
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not available - cannot plot tick data")
            return None
        
        tick_data = self._original_tick_data.copy()
        
        # Determine timestamp column
        timestamp_col = 'ts_event' if 'ts_event' in tick_data.columns else 'ts_recv'
        
        # Sample data if too large
        if len(tick_data) > max_ticks:
            sample_idx = np.linspace(0, len(tick_data)-1, max_ticks, dtype=int)
            tick_data = tick_data.iloc[sample_idx]
            warnings.warn(f'Sampled {max_ticks} ticks from {len(self._original_tick_data)} '
                         'for plotting performance')
        
        # Convert timestamp to datetime if needed
        if not isinstance(tick_data[timestamp_col], pd.DatetimeIndex):
            tick_data[timestamp_col] = pd.to_datetime(tick_data[timestamp_col])
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), 
                                      gridspec_kw={'height_ratios': [3, 1]})
        
        # Price plot
        valid_price_data = tick_data[tick_data['price'].notna()]
        if len(valid_price_data) == 0:
            print("No valid price data to plot")
            return None
            
        if show_size and 'size' in valid_price_data.columns:
            # Scale sizes for visibility
            sizes = valid_price_data['size'].fillna(0)
            if sizes.max() > sizes.min():
                scaled_sizes = 10 + (sizes - sizes.min()) / (sizes.max() - sizes.min()) * 90
            else:
                scaled_sizes = np.full(len(sizes), 50)  # Default size if all sizes are equal
            ax1.scatter(valid_price_data[timestamp_col], valid_price_data['price'], 
                       s=scaled_sizes, alpha=0.6, **plot_kwargs)
        else:
            ax1.plot(valid_price_data[timestamp_col], valid_price_data['price'], **plot_kwargs)
        
        ax1.set_title(f'Tick Data - Price (Total: {len(self._original_tick_data)} ticks)')
        ax1.set_ylabel('Price')
        ax1.grid(True)
        
        # Size plot
        if 'size' in tick_data.columns:
            valid_size_data = tick_data[tick_data['size'].notna()]
            if len(valid_size_data) > 0:
                ax2.bar(valid_size_data[timestamp_col], valid_size_data['size'], 
                       width=pd.Timedelta(seconds=1), alpha=0.7)
        ax2.set_title('Tick Sizes')
        ax2.set_ylabel('Size')
        ax2.set_xlabel('Time')
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()
        
        return fig
    
    def plot_ohlcv_comparison(self, time_interval: str = None):
        """
        Plot both tick data and corresponding OHLCV bars for comparison.
        
        Parameters:
        -----------
        time_interval : str, optional
            Time interval for OHLCV aggregation
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not available - cannot plot comparison")
            return None
        
        if time_interval is None:
            time_interval = self._time_interval
        
        # Get OHLCV data for comparison
        ohlcv_data = self.get_ohlcv_data(time_interval)
        tick_data = self._original_tick_data.copy()
        
        # Determine timestamp column
        timestamp_col = 'ts_event' if 'ts_event' in tick_data.columns else 'ts_recv'
        
        # Convert timestamp to datetime if needed
        if not isinstance(tick_data[timestamp_col], pd.DatetimeIndex):
            tick_data[timestamp_col] = pd.to_datetime(tick_data[timestamp_col])
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Plot tick data (only valid prices)
        valid_tick_data = tick_data[tick_data['price'].notna()]
        ax1.plot(valid_tick_data[timestamp_col], valid_tick_data['price'], 
                alpha=0.7, linewidth=0.5, label='Tick Prices')
        ax1.set_title(f'Tick Data vs OHLCV Bars ({time_interval})')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot OHLCV data as candlesticks (simplified)
        for i, (timestamp, row) in enumerate(ohlcv_data.iterrows()):
            color = 'green' if row['Close'] >= row['Open'] else 'red'
            ax2.plot([timestamp, timestamp], [row['Low'], row['High']], 
                    color=color, linewidth=1)
            ax2.plot([timestamp, timestamp], [row['Open'], row['Close']], 
                    color=color, linewidth=3, alpha=0.8)
        
        ax2.set_title(f'OHLCV Bars ({time_interval}) - {len(ohlcv_data)} bars from {len(tick_data)} ticks')
        ax2.set_ylabel('Price')
        ax2.set_xlabel('Time')
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()
        
        return fig


# Convenience function to create and run tick-based backtests
def run_tick_backtest(tick_data: pd.DataFrame,
                      strategy: Type[Strategy],
                      time_interval: str = '1min',
                      **backtest_kwargs) -> pd.Series:
    """
    Convenience function to run a tick-based backtest.
    
    Parameters:
    -----------
    tick_data : pd.DataFrame
        Tick data with ts_event, price, size columns
    strategy : Type[Strategy]
        Strategy class to test
    time_interval : str
        Time interval for OHLCV conversion
    **backtest_kwargs
        Additional arguments for TickBacktest
        
    Returns:
    --------
    pd.Series
        Backtest results
    """
    backtest = TickBacktest(tick_data, strategy, 
                           time_interval=time_interval,
                           **backtest_kwargs)
    return backtest.run()


# Example usage and helper functions
def create_sample_tick_data(n_ticks: int = 1000, 
                           start_time: str = '2023-01-01 09:30:00',
                           base_price: float = 100.0) -> pd.DataFrame:
    """
    Create sample tick data for testing.
    
    Parameters:
    -----------
    n_ticks : int
        Number of ticks to generate
    start_time : str
        Start timestamp
    base_price : float
        Base price for random walk
        
    Returns:
    --------
    pd.DataFrame
        Sample tick data
    """
    np.random.seed(42)
    
    # Generate timestamps (irregular intervals)
    start_ts = pd.to_datetime(start_time)
    time_deltas = np.random.exponential(1.0, n_ticks)  # Seconds between ticks
    timestamps = [start_ts + pd.Timedelta(seconds=np.sum(time_deltas[:i+1])) 
                  for i in range(n_ticks)]
    
    # Generate prices (random walk)
    returns = np.random.normal(0, 0.001, n_ticks)
    prices = base_price * np.cumprod(1 + returns)
    
    # Generate sizes (random)
    sizes = np.random.lognormal(2, 1, n_ticks)
    sizes = np.round(sizes).astype(int)
    
    # Generate some additional columns
    bid_prices = prices * (1 - np.random.uniform(0.0001, 0.001, n_ticks))
    ask_prices = prices * (1 + np.random.uniform(0.0001, 0.001, n_ticks))
    
    tick_data = pd.DataFrame({
        'ts_event': timestamps,
        'price': prices,
        'size': sizes,
        'bid_price': bid_prices,
        'ask_price': ask_prices,
        'trade_type': np.random.choice(['B', 'S'], n_ticks),  # Buy/Sell
    })
    
    return tick_data


def create_sample_market_data(n_ticks: int = 1000, 
                             start_time: str = '2025-01-27T09:00:00.000000000Z',
                             base_price: float = 4.0,
                             symbol: str = 'DPRO') -> pd.DataFrame:
    """
    Create sample market data in the format similar to user's data.
    
    Parameters:
    -----------
    n_ticks : int
        Number of ticks to generate
    start_time : str
        Start timestamp in ISO format
    base_price : float
        Base price for random walk
    symbol : str
        Symbol/instrument identifier
        
    Returns:
    --------
    pd.DataFrame
        Sample market data with order book depth columns
    """
    np.random.seed(42)
    
    # Generate timestamps (irregular intervals)
    start_ts = pd.to_datetime(start_time)
    time_deltas = np.random.exponential(0.1, n_ticks)  # Milliseconds between ticks
    timestamps_recv = [start_ts + pd.Timedelta(milliseconds=np.sum(time_deltas[:i+1])) 
                       for i in range(n_ticks)]
    timestamps_event = [ts - pd.Timedelta(microseconds=np.random.randint(1, 1000)) 
                        for ts in timestamps_recv]
    
    # Generate prices (random walk)
    returns = np.random.normal(0, 0.0001, n_ticks)
    prices = base_price * np.cumprod(1 + returns)
    
    # Generate sizes (random)
    sizes = np.random.choice([50, 100, 150, 200, 250], n_ticks)
    
    # Create the DataFrame with main columns
    data = {
        'ts_recv': timestamps_recv,
        'ts_event': timestamps_event,
        'rtype': np.full(n_ticks, 10),  # Record type
        'publisher_id': np.full(n_ticks, 2),
        'instrument_id': np.full(n_ticks, 4559),
        'action': np.random.choice(['A', 'C', 'M', 'D'], n_ticks),  # Add, Cancel, Modify, Delete
        'side': np.random.choice(['B', 'A', 'N'], n_ticks),  # Bid, Ask, None
        'depth': np.random.randint(0, 10, n_ticks),
        'price': prices,
        'size': sizes,
        'flags': np.random.randint(128, 132, n_ticks),
        'ts_in_delta': np.random.randint(100000, 200000, n_ticks),
        'sequence': np.arange(826376, 826376 + n_ticks),
        'symbol': [symbol] * n_ticks,
    }
    
    # Add order book levels (10 levels of depth)
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