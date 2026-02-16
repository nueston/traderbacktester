import pandas as pd

class BaseIndicator:
    """Base class for all indicators"""
    
    def __init__(self, name, **kwargs):
        self.name = name
    
    def initialize(self):
        """Initialize indicator state"""
        pass
    
    def process_row(self, row, trailing_df):
        """Process a single row of data"""
        raise NotImplementedError
    
    def finalize(self):
        """Calculate final result"""
        raise NotImplementedError


class PriceIndicator(BaseIndicator):
    """average"""
    
    def __init__(self, name, price_column='price', **kwargs):
        super().__init__(name, **kwargs)
        self.price_column = price_column
        self.values = []
    
    def initialize(self):
        self.values = []
    
    def process_row(self, row, trailing_df):
        # Try different possible price columns
        price_columns = [self.price_column, 'price']
        
        for col in price_columns:
            price_value = row[col]
            if price_value > 0:
                self.values.append(price_value)
            break
    
    def finalize(self):
        if len(self.values) > 0:
            return sum(self.values) / len(self.values)
        else:
            return 0.0
        
class OBIIndicator(BaseIndicator):
    """Order Book Imbalance indicator - Optimized with vectorized operations"""
    
    def __init__(self, name, depth=10, **kwargs):
        super().__init__(name, **kwargs)
        self.depth = depth
        self.values = []
        # Pre-compute column names once
        self.bid_cols = [f'bid_sz_{level:02d}' for level in range(depth)]
        self.ask_cols = [f'ask_sz_{level:02d}' for level in range(depth)]
        self.valid_cols = []  # Will store tuples of (bid_col, ask_col) that exist
    
    def initialize(self):
        self.values = []
    
    def process_row(self, row, trailing_df):
        # Use pre-computed valid columns
        tick_obi_sum = 0.0
        valid_levels = 0
        
        for bid_col, ask_col in self.valid_cols:
            bid_size = row[bid_col]
            ask_size = row[ask_col]
            
            total_size = bid_size + ask_size
            if total_size > 0:
                level_obi = (bid_size - ask_size) / total_size
                tick_obi_sum += level_obi
                valid_levels += 1
        
        if valid_levels > 0:
            tick_avg_obi = tick_obi_sum / valid_levels
            self.values.append(tick_avg_obi)
    
    def finalize(self):
        if len(self.values) > 0:
            return sum(self.values) / len(self.values)
        else:
            return 0.0


class OBIIndicatorVectorized(BaseIndicator):
    """Order Book Imbalance indicator - Fully vectorized for maximum performance"""
    
    def __init__(self, name, depth=10, **kwargs):
        super().__init__(name, **kwargs)
        self.depth = depth
        self.bid_cols = [f'bid_sz_{level:02d}' for level in range(depth)]
        self.ask_cols = [f'ask_sz_{level:02d}' for level in range(depth)]
        self.result = 0.0
    
    def initialize(self):
        self.result = 0.0
    
    def process_row(self, row, trailing_df):
        # This method intentionally left empty - processing happens in finalize()
        pass
    
    def finalize(self, trailing_df=None):
        """Vectorized calculation - processes entire DataFrame at once"""
        if trailing_df is None or len(trailing_df) == 0:
            return 0.0
        
        # Find which columns actually exist
        valid_pairs = [(bid, ask) for bid, ask in zip(self.bid_cols, self.ask_cols) 
                       if bid in trailing_df.columns and ask in trailing_df.columns]
        
        if not valid_pairs:
            return 0.0
        
        # Vectorized calculation across all rows and depth levels at once
        obi_values = []
        
        for bid_col, ask_col in valid_pairs:
            bid_sizes = trailing_df[bid_col]
            ask_sizes = trailing_df[ask_col]
            total_sizes = bid_sizes + ask_sizes
            
            # Only calculate OBI where total_size > 0
            valid_mask = total_sizes > 0
            if valid_mask.any():
                level_obi = (bid_sizes[valid_mask] - ask_sizes[valid_mask]) / total_sizes[valid_mask]
                obi_values.extend(level_obi.values)
        
        if len(obi_values) > 0:
            return sum(obi_values) / len(obi_values)
        else:
            return 0.0


class CancelationIndicator(BaseIndicator):
    """sum"""
    
    def __init__(self, name, action_column='action', cancel_value='C', side_column=None, side_value='B', **kwargs):
        super().__init__(name, **kwargs)
        self.action_column = action_column
        self.cancel_value = cancel_value
        self.side_column = side_column
        self.side_value = side_value
        self.count = 0
    
    def initialize(self):
        self.count = 0
    
    def process_row(self, row, trailing_df):
        if self.action_column in trailing_df.columns:
            if self.cancel_value in str(row[self.action_column]):
                if self.side_column and self.side_column in trailing_df.columns:
                    if str(row[self.side_column]) != self.side_value:
                        return
                self.count += 1
    
    def finalize(self):
        return self.count


class VolumeIndicator(BaseIndicator):
    """mean"""
    
    def __init__(self, name, size_column='size', **kwargs):
        super().__init__(name, **kwargs)
        self.size_column = size_column
        self.values = []
    
    def initialize(self):
        self.values = []
    
    def process_row(self, row, trailing_df):
        if self.size_column in trailing_df.columns:
            size_value = row[self.size_column]
            if size_value > 0:  # Only include positive sizes
                self.values.append(size_value)
    
    def finalize(self):
        if len(self.values) > 0:
            return sum(self.values) / len(self.values)
        else:
            return 0.0


class SpreadIndicator(BaseIndicator):
    """average"""
    
    def __init__(self, name, bid_column='bid_px_00', ask_column='ask_px_00', **kwargs):
        super().__init__(name, **kwargs)
        self.bid_column = bid_column
        self.ask_column = ask_column
        self.values = []
    
    def initialize(self):
        self.values = []
    
    def process_row(self, row, trailing_df):
        if (self.bid_column in trailing_df.columns and 
            self.ask_column in trailing_df.columns):
            
            bid_price = row[self.bid_column]
            ask_price = row[self.ask_column]
            
            if bid_price > 0 and ask_price > 0:
                spread = ask_price - bid_price
                self.values.append(spread)
    
    def finalize(self):
        if len(self.values) > 0:
            return sum(self.values) / len(self.values)
        else:
            return 0.0


class IndicatorFactory:
    """Factory class to create indicators from rules"""
    
    @staticmethod
    def create_indicator(rule):
        name = rule['name']
        indicator_type = rule['type']
        
        # Create a copy of rule without 'name' and 'type' to avoid parameter conflicts
        kwargs = {k: v for k, v in rule.items() if k not in ['name', 'type']}

        if indicator_type == 'price':
            return PriceIndicator(name, **kwargs)
        if indicator_type == 'obi':
            return OBIIndicator(name, **kwargs)
        elif indicator_type == 'cancelations':
            return CancelationIndicator(name, **kwargs)
        elif indicator_type == 'volume':
            return VolumeIndicator(name, **kwargs)
        elif indicator_type == 'spread':
            return SpreadIndicator(name, **kwargs)
        else:
            raise ValueError(f"Unknown indicator type: {indicator_type}")


def run_trailing_indicators(trailing_df, indicator_rules):
    """
    Calculate multiple indicators for trailing data in a single loop
    
    Args:
        trailing_df (pd.DataFrame): DataFrame containing trailing tick data
        indicator_rules (list): List of indicator configuration dictionaries
            Each rule should have:
            - 'name': string identifier for the indicator
            - 'type': indicator type ('obi', 'cancelations', etc.)
            - Additional parameters specific to the indicator type
            
    Example indicator_rules:
        [
            {
                'name': 'avg_obi',
                'type': 'obi',
                'depth': 10  # Number of depth levels to include
            },
            {
                'name': 'total_cancelations',
                'type': 'cancelations',
                'action_column': 'action',
                'cancel_value': 'C'
            }
        ]
        
    Returns:
        dict: Dictionary with indicator names as keys and calculated values
    """
    if len(trailing_df) == 0:
        return {rule['name']: 0.0 for rule in indicator_rules}
    
    # Create indicators from rules
    indicators = [IndicatorFactory.create_indicator(rule) for rule in indicator_rules]
    
    # Initialize all indicators and cache valid columns for OBI
    for indicator in indicators:
        indicator.initialize()
        if isinstance(indicator, OBIIndicator):
            # Pre-validate which columns exist - do this once instead of per-row
            indicator.valid_cols = [
                (bid, ask) for bid, ask in zip(indicator.bid_cols, indicator.ask_cols)
                if bid in trailing_df.columns and ask in trailing_df.columns
            ]
    
    # Single loop through all trailing data - process all indicators in parallel
    for idx, row in trailing_df.iterrows():
        for indicator in indicators:
            # Skip vectorized indicators in the row loop
            if not isinstance(indicator, OBIIndicatorVectorized):
                indicator.process_row(row, trailing_df)
    
    # Calculate final results for all indicators
    results = {}
    for indicator in indicators:
        # Vectorized indicators need the full DataFrame
        if isinstance(indicator, OBIIndicatorVectorized):
            results[indicator.name] = indicator.finalize(trailing_df)
        else:
            results[indicator.name] = indicator.finalize()
    
    return results