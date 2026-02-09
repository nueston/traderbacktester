def print_indicators_history(timestamp, trend, indicators_history):
    """
    Print the timestamp and all indicator history values.

    Args:
        timestamp: The current timestamp to display.
        indicators_history (dict): Dictionary mapping indicator names to lists of historical values.
    """
    print(f"Timestamp: {timestamp}")
    print(f"Trend: {trend}")
    print("-" * 50)
    for name, values in indicators_history.items():
        formatted_values = [f"{v:.6f}" if isinstance(v, float) else str(v) for v in values]
        print(f"  {name}: [{', '.join(formatted_values)}]")
    print("-" * 50)
