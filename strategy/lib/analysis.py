"""
Analysis utilities for indicator monitoring
"""
import numpy as np
from strategy.lib.math import linear_regression


def print_indicators_history(timestamp, indicators_history):
    """
    Print the complete history of all indicators including OBI, spread, volume, cancelations, and price
    
    Args:
        timestamp (datetime): Current timestamp for the detection
        indicators_history (dict): Dictionary containing indicator histories
    """
    print("\n" + "="*80)
    print("INDICATOR HISTORY SNAPSHOT")
    if timestamp:
        print(f"Timestamp: {timestamp}")
    print("="*80)
    
    for indicator_name, history in indicators_history.items():
        if not history:
            continue
            
        print(f"\n{indicator_name.upper()} HISTORY:")
        print("-" * 40)
        
        # Print each value in the history with index
        for i, value in enumerate(history):
            if isinstance(value, (int, float)):
                print(f"  [{i:2d}]: {value:8.4f}")
            else:
                print(f"  [{i:2d}]: {value}")
        
        # Calculate and print statistics if numeric
        if history and all(isinstance(v, (int, float)) for v in history):
            mean_val = np.mean(history)
            std_val = np.std(history)
            min_val = np.min(history)
            max_val = np.max(history)
            trend = linear_regression(history) if len(history) > 1 else 0
            
            print(f"  Statistics:")
            print(f"    Mean:  {mean_val:8.4f}")
            print(f"    Std:   {std_val:8.4f}")
            print(f"    Min:   {min_val:8.4f}")
            print(f"    Max:   {max_val:8.4f}")
            print(f"    Trend: {trend:8.4f}")
    
    print("="*80)