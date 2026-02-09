import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta

def plot_timeseries(df, x_col, y_col, granularity_seconds=1, title="Time Series Plot", 
                   xlabel="Time", ylabel="Value", figsize=(12, 6)):
    """
    Plot time series data with sampling based on granularity
    
    Args:
        df (pd.DataFrame): DataFrame containing x and y data
        x_col (str): Column name for x-axis (datetime values)
        y_col (str): Column name for y-axis (numeric values)
        granularity_seconds (int): Sampling granularity in seconds
        title (str): Plot title
        xlabel (str): X-axis label
        ylabel (str): Y-axis label
        figsize (tuple): Figure size (width, height)
    
    Returns:
        matplotlib.figure.Figure: The created figure
    """
    # Create a copy to avoid modifying original data
    plot_df = df.copy()
    
    # Ensure x column is datetime
    if not pd.api.types.is_datetime64_any_dtype(plot_df[x_col]):
        plot_df[x_col] = pd.to_datetime(plot_df[x_col], utc=True)
    
    # Sort by time to ensure proper ordering
    plot_df = plot_df.sort_values(x_col).reset_index(drop=True)
    
    # Sample data based on granularity
    if granularity_seconds > 0 and len(plot_df) > 1:
        # Set x column as index for resampling
        plot_df = plot_df.set_index(x_col)
        
        # Resample based on granularity (mean aggregation for numeric values)
        granularity_str = f'{granularity_seconds}s'  # s = seconds (lowercase)
        sampled_df = plot_df.resample(granularity_str).mean()
        
        # Remove NaN values that might result from resampling
        sampled_df = sampled_df.dropna()
        
        # Reset index to get time column back
        sampled_df = sampled_df.reset_index()
        x_values = sampled_df[x_col]
        y_values = sampled_df[y_col]
    else:
        # No sampling, use original data
        x_values = plot_df[x_col]
        y_values = plot_df[y_col]
    
    # Create the plot
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot the data
    ax.plot(x_values, y_values, linewidth=1, marker='o', markersize=2, alpha=0.8)
    
    # Format x-axis for datetime
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Set labels and title
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} (Granularity: {granularity_seconds}s, Points: {len(y_values)})")
    
    # Add grid for better readability
    ax.grid(True, alpha=0.3)
    
    # Tight layout to prevent label cutoff
    plt.tight_layout()
    
    # Show the plot
    plt.show()
    
    return fig

def plot_multiple_series(df, x_col, y_cols, granularity_seconds=1, title="Multiple Time Series", 
                        xlabel="Time", ylabel="Value", figsize=(12, 8)):
    """
    Plot multiple time series on the same graph
    
    Args:
        df (pd.DataFrame): DataFrame containing data
        x_col (str): Column name for x-axis (datetime values)
        y_cols (list): List of column names for y-axis values
        granularity_seconds (int): Sampling granularity in seconds
        title (str): Plot title
        xlabel (str): X-axis label
        ylabel (str): Y-axis label
        figsize (tuple): Figure size (width, height)
    
    Returns:
        matplotlib.figure.Figure: The created figure
    """
    # Create a copy to avoid modifying original data
    plot_df = df.copy()
    
    # Ensure x column is datetime
    if not pd.api.types.is_datetime64_any_dtype(plot_df[x_col]):
        plot_df[x_col] = pd.to_datetime(plot_df[x_col], utc=True)
    
    # Sort by time
    plot_df = plot_df.sort_values(x_col).reset_index(drop=True)
    
    # Sample data if needed
    if granularity_seconds > 0 and len(plot_df) > 1:
        plot_df = plot_df.set_index(x_col)
        granularity_str = f'{granularity_seconds}s'
        sampled_df = plot_df.resample(granularity_str).mean().dropna()
        sampled_df = sampled_df.reset_index()
        x_values = sampled_df[x_col]
    else:
        sampled_df = plot_df
        x_values = plot_df[x_col]
    
    # Create the plot
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot each series
    for y_col in y_cols:
        if y_col in sampled_df.columns:
            y_values = sampled_df[y_col]
            ax.plot(x_values, y_values, linewidth=1, marker='o', markersize=2, 
                   alpha=0.8, label=y_col)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
    plt.xticks(rotation=45)
    
    # Labels and legend
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} (Granularity: {granularity_seconds}s)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Show the plot
    plt.show()
    
    return fig
