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


class OBIIndicator(BaseIndicator):
    """Order Book Imbalance indicator"""
    
    def __init__(self, name, depth=10, **kwargs):
        super().__init__(name, **kwargs)
        self.depth = depth
        self.values = []
    
    def initialize(self):
        self.values = []
    
    def process_row(self, row, trailing_df):
        tick_obi_sum = 0.0
        valid_levels = 0
        
        for level in range(self.depth):
            bid_col = f'bid_sz_{level:02d}'
            ask_col = f'ask_sz_{level:02d}'
            
            if bid_col in trailing_df.columns and ask_col in trailing_df.columns:
                bid_size = row[bid_col] if not pd.isna(row[bid_col]) else 0
                ask_size = row[ask_col] if not pd.isna(row[ask_col]) else 0
                
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


class CancelationIndicator(BaseIndicator):
    """Cancelation counting indicator"""
    
    def __init__(self, name, action_column='action', cancel_value='C', **kwargs):
        super().__init__(name, **kwargs)
        self.action_column = action_column
        self.cancel_value = cancel_value
        self.count = 0
    
    def initialize(self):
        self.count = 0
    
    def process_row(self, row, trailing_df):
        if self.action_column in trailing_df.columns and not pd.isna(row[self.action_column]):
            if self.cancel_value in str(row[self.action_column]):
                self.count += 1
    
    def finalize(self):
        return self.count


class VolumeIndicator(BaseIndicator):
    """Volume indicator that calculates mean size"""
    
    def __init__(self, name, size_column='size', **kwargs):
        super().__init__(name, **kwargs)
        self.size_column = size_column
        self.values = []
    
    def initialize(self):
        self.values = []
    
    def process_row(self, row, trailing_df):
        if self.size_column in trailing_df.columns and not pd.isna(row[self.size_column]):
            size_value = row[self.size_column]
            if size_value > 0:  # Only include positive sizes
                self.values.append(size_value)
    
    def finalize(self):
        if len(self.values) > 0:
            return sum(self.values) / len(self.values)
        else:
            return 0.0


class SpreadIndicator(BaseIndicator):
    """Spread indicator that calculates bid-ask spread"""
    
    def __init__(self, name, bid_column='bid_px_00', ask_column='ask_px_00', **kwargs):
        super().__init__(name, **kwargs)
        self.bid_column = bid_column
        self.ask_column = ask_column
        self.values = []
    
    def initialize(self):
        self.values = []
    
    def process_row(self, row, trailing_df):
        if (self.bid_column in trailing_df.columns and 
            self.ask_column in trailing_df.columns and 
            not pd.isna(row[self.bid_column]) and 
            not pd.isna(row[self.ask_column])):
            
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
    
    # Initialize all indicators
    for indicator in indicators:
        indicator.initialize()
    
    # Single loop through all trailing data - process all indicators in parallel
    for idx, row in trailing_df.iterrows():
        for indicator in indicators:
            indicator.process_row(row, trailing_df)
    
    # Calculate final results for all indicators
    results = {}
    for indicator in indicators:
        results[indicator.name] = indicator.finalize()
    
    return results