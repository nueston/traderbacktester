
import pandas as pd
import numpy as np

try:
    from .data_bento import DataBento
except ImportError:
    from data_bento import DataBento


class DataOhlcBento:
    def __init__(self, ohlcv_data):
        """
        Initialize with OHLCV data that contains Bento market data columns
        
        Args:
            ohlcv_data (pd.DataFrame): DataFrame with OHLCV data and Bento columns
        """
        self.ohlcv = ohlcv_data
        self.current_index = 0
        
    def get_bento_column(self, column_name):
        """
        Helper method to access Bento-specific columns
        
        Args:
            column_name (str): Name of the Bento column (without 'bento_' prefix)
            
        Returns:
            pd.Series or None: The Bento column data
        """
        full_column_name = f'bento_{column_name}'
        if full_column_name in self.ohlcv.columns:
            return self.ohlcv[full_column_name]
        return None
    
    def get_total_bid_liquidity(self, level=10, iterations=1, current_index=None):
        """
        Calculate total bid liquidity across specified depth levels for given iterations
        
        Args:
            level (int): Number of depth levels to include (0 to level-1)
            iterations (int): Number of past iterations to consider (1 = current only)
            current_index (int, optional): Index to use as reference. If None, uses self.current_index
            
        Returns:
            float or list: Total bid liquidity for current iteration or list for multiple iterations
        """
        if current_index is None:
            current_index = self.current_index
            
        if iterations == 1:
            # Return liquidity for current iteration only
            total_liquidity = 0
            for depth_level in range(level):
                bid_size_col = self.get_bento_column(f'bid_sz_{depth_level:02d}')
                if bid_size_col is not None and current_index < len(bid_size_col):
                    size = bid_size_col.iloc[current_index]
                    if not pd.isna(size):
                        total_liquidity += size
            return total_liquidity
        else:
            # Return liquidity for multiple iterations
            liquidity_list = []
            start_idx = max(0, current_index - iterations + 1)
            
            for idx in range(start_idx, current_index + 1):
                total_liquidity = 0
                for depth_level in range(level):
                    bid_size_col = self.get_bento_column(f'bid_sz_{depth_level:02d}')
                    if bid_size_col is not None and idx < len(bid_size_col):
                        size = bid_size_col.iloc[idx]
                        if not pd.isna(size):
                            total_liquidity += size
                liquidity_list.append(total_liquidity)
            return liquidity_list
    
    def get_total_ask_liquidity(self, level=10, iterations=1, current_index=None):
        """
        Calculate total ask liquidity across specified depth levels for given iterations
        
        Args:
            level (int): Number of depth levels to include (0 to level-1)
            iterations (int): Number of past iterations to consider (1 = current only)
            current_index (int, optional): Index to use as reference. If None, uses self.current_index
            
        Returns:
            float or list: Total ask liquidity for current iteration or list for multiple iterations
        """
        if current_index is None:
            current_index = self.current_index
            
        if iterations == 1:
            # Return liquidity for current iteration only
            total_liquidity = 0
            for depth_level in range(level):
                ask_size_col = self.get_bento_column(f'ask_sz_{depth_level:02d}')
                if ask_size_col is not None and current_index < len(ask_size_col):
                    size = ask_size_col.iloc[current_index]
                    if not pd.isna(size):
                        total_liquidity += size
            return total_liquidity
        else:
            # Return liquidity for multiple iterations
            liquidity_list = []
            start_idx = max(0, current_index - iterations + 1)
            
            for idx in range(start_idx, current_index + 1):
                total_liquidity = 0
                for depth_level in range(level):
                    ask_size_col = self.get_bento_column(f'ask_sz_{depth_level:02d}')
                    if ask_size_col is not None and idx < len(ask_size_col):
                        size = ask_size_col.iloc[idx]
                        if not pd.isna(size):
                            total_liquidity += size
                liquidity_list.append(total_liquidity)
            return liquidity_list
    
    def get_current_spread(self, current_index=None):
        """
        Get current bid-ask spread
        
        Args:
            current_index (int, optional): Index to use. If None, uses self.current_index
        
        Returns:
            float or None: Current spread value
        """
        if current_index is None:
            current_index = self.current_index
            
        spread_col = self.get_bento_column('spread')
        if spread_col is not None and current_index < len(spread_col):
            return spread_col.iloc[current_index]
        
        # Fallback: calculate spread from bid/ask prices
        bid_px_col = self.get_bento_column('bid_px_00')
        ask_px_col = self.get_bento_column('ask_px_00')
        
        if (bid_px_col is not None and ask_px_col is not None and 
            current_index < len(bid_px_col) and current_index < len(ask_px_col)):
            bid_price = bid_px_col.iloc[current_index]
            ask_price = ask_px_col.iloc[current_index]
            if not pd.isna(bid_price) and not pd.isna(ask_price):
                return ask_price - bid_price
        
        return None
    
    def get_volume(self, iteration=1, current_index=None):
        """
        Get volume for specified iteration(s)
        
        Args:
            iteration (int): Number of iterations back (1 = current, 2 = previous, etc.)
            current_index (int, optional): Index to use as reference. If None, uses self.current_index
            
        Returns:
            float or None: Volume value for the specified iteration
        """
        if current_index is None:
            current_index = self.current_index
            
        target_index = current_index - iteration + 1
        if target_index >= 0 and target_index < len(self.ohlcv):
            return self.ohlcv['Volume'].iloc[target_index]
        return None
    
    def get_liquidity_trend(self, current_index, iterations=10):
        """
        Calculate liquidity trend over specified iterations relative to current index
        Returns percentage change in total liquidity (bid + ask)
        
        Args:
            current_index (int): The index to use as reference point
            iterations (int): Number of iterations to analyze
            
        Returns:
            dict: Dictionary with bid_trend, ask_trend, and total_trend percentages
        """
        if iterations < 2 or current_index < iterations - 1:
            return {'bid_trend': 0.0, 'ask_trend': 0.0, 'total_trend': 0.0}
        
        # Calculate liquidity data over the specified range
        bid_liquidity_data = []
        ask_liquidity_data = []
        
        start_idx = current_index - iterations + 1
        for idx in range(start_idx, current_index + 1):
            bid_liquidity_data.append(self.get_total_bid_liquidity(level=10, iterations=1, current_index=idx))
            ask_liquidity_data.append(self.get_total_ask_liquidity(level=10, iterations=1, current_index=idx))
        
        if len(bid_liquidity_data) < 2 or len(ask_liquidity_data) < 2:
            return {'bid_trend': 0.0, 'ask_trend': 0.0, 'total_trend': 0.0}
        
        # Calculate percentage changes
        bid_start = bid_liquidity_data[0]
        bid_end = bid_liquidity_data[-1]
        ask_start = ask_liquidity_data[0]
        ask_end = ask_liquidity_data[-1]
        
        # Avoid division by zero
        bid_trend = 0.0
        if bid_start != 0:
            bid_trend = ((bid_end - bid_start) / bid_start) * 100
        
        ask_trend = 0.0
        if ask_start != 0:
            ask_trend = ((ask_end - ask_start) / ask_start) * 100
        
        # Calculate total liquidity trend
        total_start = bid_start + ask_start
        total_end = bid_end + ask_end
        total_trend = 0.0
        if total_start != 0:
            total_trend = ((total_end - total_start) / total_start) * 100
        
        return {
            'bid_trend': round(bid_trend, 2),
            'ask_trend': round(ask_trend, 2),
            'total_trend': round(total_trend, 2)
        }
    
    def set_current_index(self, index):
        """
        Set the current index for data access
        
        Args:
            index (int): Index to set as current
        """
        if 0 <= index < len(self.ohlcv):
            self.current_index = index
    
    def advance_index(self):
        """
        Advance to the next index (useful for backtesting iterations)
        
        Returns:
            bool: True if advanced successfully, False if at end
        """
        if self.current_index < len(self.ohlcv) - 1:
            self.current_index += 1
            return True
        return False
    
    def get_current_ohlcv(self, current_index=None):
        """
        Get current OHLCV data for the specified index
        
        Args:
            current_index (int, optional): Index to use. If None, uses self.current_index
        
        Returns:
            pd.Series: OHLCV data for the specified index
        """
        if current_index is None:
            current_index = self.current_index
            
        if current_index < len(self.ohlcv):
            return self.ohlcv.iloc[current_index]
        return None
    
    def trailing_obi(self, df, current_index, trailing_duration=1.0, depth=10):
        """
        Calculate Order Book Imbalance (OBI) for trailing duration across specified depth levels
        
        OBI = (bid_size - ask_size) / (bid_size + ask_size)
        
        Args:
            df (pd.DataFrame): DataFrame containing tick data
            current_index (int): Current index reference point
            trailing_duration (float): Duration in seconds to look back from current_index time
            depth (int): Number of depth levels to include (0 to depth-1)
            
        Returns:
            float: Average OBI across all depth levels for the trailing duration
        """
        # Create DataBento instance to access get_trailing_ticks method
        data_bento = DataBento()
        
        # Get trailing ticks for the specified duration
        trailing_df = data_bento.get_trailing_ticks(df, current_index, trailing_duration)
        
        if len(trailing_df) == 0:
            return 0.0
        
        obi_values = []
        
        # Calculate OBI for each tick in the trailing data
        for idx, row in trailing_df.iterrows():
            tick_obi_sum = 0.0
            valid_levels = 0
            
            # Calculate OBI for each depth level
            for level in range(depth):
                bid_col = f'bid_sz_{level:02d}'
                ask_col = f'ask_sz_{level:02d}'
                
                # Check if columns exist
                if bid_col in trailing_df.columns and ask_col in trailing_df.columns:
                    bid_size = row[bid_col] if not pd.isna(row[bid_col]) else 0
                    ask_size = row[ask_col] if not pd.isna(row[ask_col]) else 0
                    
                    # Calculate OBI for this level
                    total_size = bid_size + ask_size
                    if total_size > 0:
                        level_obi = (bid_size - ask_size) / total_size
                        tick_obi_sum += level_obi
                        valid_levels += 1
            
            # Average OBI across all valid levels for this tick
            if valid_levels > 0:
                tick_avg_obi = tick_obi_sum / valid_levels
                obi_values.append(tick_avg_obi)
        
        # Return average OBI across all ticks in the trailing duration
        if len(obi_values) > 0:
            return sum(obi_values) / len(obi_values)
        else:
            return 0.0