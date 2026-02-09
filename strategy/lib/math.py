"""Mathematical utility functions for trading strategies"""

def linear_regression(history_list):
    """Calculate linear regression slope over recent history for any indicator
    
    Args:
        history_list (list): List of numerical values to analyze
        
    Returns:
        float: Trend strength (slope weighted by correlation)
    """
    if len(history_list) < 3:
        return 0
    
    # Use last 5 values or all available if less than 5
    lookback_period = min(5, len(history_list))
    recent_values = history_list[-lookback_period:]
    
    # Create x values (time indices)
    x = list(range(lookback_period))
    y = recent_values
    
    # Calculate linear regression slope using least squares method
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(x[i] * y[i] for i in range(n))
    sum_x2 = sum(x[i] * x[i] for i in range(n))
    
    # Calculate slope (trend direction and strength)
    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return 0
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    
    # Calculate correlation coefficient to measure trend strength
    mean_x = sum_x / n
    mean_y = sum_y / n
    
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(n))
    
    if sum_sq_x == 0 or sum_sq_y == 0:
        correlation = 0
    else:
        correlation = numerator / (sum_sq_x * sum_sq_y) ** 0.5
    
    # Weight the slope by correlation strength to get trend confidence
    trend_strength = slope * abs(correlation)
    
    return trend_strength