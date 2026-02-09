import pandas as pd
from data.data_bento import DataBento

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


class PriceIndicator(BaseIndicator):
    """Price indicator that calculates average price from trailing data"""
    
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
            if col in trailing_df.columns and not pd.isna(row[col]):
                price_value = row[col]
                if price_value > 0:
                    self.values.append(price_value)
                break
    
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
        elif indicator_type == 'price':
            return PriceIndicator(name, **kwargs)
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


def get_default_indicator_rules():
    """Get default indicator rules configuration
    
    Returns:
        list: Default indicator rules configuration
    """
    return [
        {
            'name': 'obi',
            'type': 'obi',
            'depth': 10
        },
        {
            'name': 'volume',
            'type': 'volume',
        },
        {
            'name': 'cancelations',
            'type': 'cancelations',
            'action_column': 'action',
            'cancel_value': 'C'
        },
        {
            'name': 'spread',
            'type': 'spread',
            'bid_column': 'bid_px_00',
            'ask_column': 'ask_px_00'
        },
        {
            'name': 'price',
            'type': 'price'
        }
    ]


def update_indicators_history(indicators_history, current_indicators, max_history_length=10):
    """Update indicators history with current values
    
    Args:
        indicators_history (dict): Dictionary containing history lists for each indicator
        current_indicators (dict): Dictionary with current indicator values
        max_history_length (int): Maximum length for each history list
        
    Returns:
        dict: Updated indicators_history
    """
    for indicator_name, value in current_indicators.items():
        if indicator_name not in indicators_history:
            indicators_history[indicator_name] = []
        
        indicators_history[indicator_name].append(value)
        if len(indicators_history[indicator_name]) > max_history_length:
            indicators_history[indicator_name].pop(0)
    
    return indicators_history


def monitor_indicators(data_df, current_index, current_time, last_monitor_time, 
                      indicator_rules=None, monitor_frequency=30.0, trailing_duration=30.0,
                      fallback_close_price=None):
    """Monitor and calculate indicators
    
    Args:
        data_df (pd.DataFrame): DataFrame containing market data
        current_index (int): Current iteration index
        current_time (datetime): Current timestamp
        last_monitor_time (datetime): Last time monitoring was performed
        indicator_rules (list, optional): List of indicator rules. Uses default if None.
        monitor_frequency (float): How often to calculate indicators (in seconds)
        trailing_duration (float): Duration in seconds for trailing calculations
        fallback_close_price (float, optional): Fallback price if price indicator fails
        
    Returns:
        tuple: (current_indicators, new_last_monitor_time) or (None, last_monitor_time)
    """
    # Check if it's time to monitor (based on time frequency)
    if last_monitor_time is not None:
        time_diff = (current_time - last_monitor_time).total_seconds()
        if time_diff < monitor_frequency:
            return None, last_monitor_time
    
    print(current_time)
    
    new_last_monitor_time = current_time
    current_indicators = {}
    
    # Use default indicator rules if none provided
    if indicator_rules is None:
        indicator_rules = get_default_indicator_rules()
    
    # Calculate indicators using trailing data
    if data_df is not None:
        data_bento = DataBento()
        trailing_df = data_bento.get_trailing_ticks(df=data_df, current_index=current_index-1, trailing_duration=trailing_duration)
        
        results = run_trailing_indicators(trailing_df, indicator_rules)

        current_indicators['obi'] = results['obi']
        current_indicators['volume'] = results['volume']
        current_indicators['cancelations'] = results['cancelations']
        current_indicators['spread'] = results['spread']
        current_indicators['price'] = results.get('price', fallback_close_price)
    
    return current_indicators, new_last_monitor_time