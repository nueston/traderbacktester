import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime
from data.data_bento import DataBento


class PlotOhlc:
    """
    Class to plot OHLC data with price and size visualization
    """
    
    def __init__(self, df):
        """
        Initialize the PlotOhlc class with data
        
        Args:
            df (pandas.DataFrame): DataFrame containing ts_event, price, and size columns
        """
        self.df = df.copy()
        self.prepare_data()
    
    @classmethod
    def from_csv(cls, csv_path):
        """
        Create PlotOhlc instance directly from CSV file
        
        Args:
            csv_path (str): Path to the CSV file containing ts_event, price, and size columns
            
        Returns:
            PlotOhlc: New instance with data loaded from CSV
        """
        data_bento = DataBento()
        df = data_bento.load_csv(csv_path)
        df = data_bento.resample_data(df, "1s")
        df = data_bento.filter_data(df, symbol=None, exclude_cancel=True, depth_level=0, exclude_morning_minutes=None, min_size=None) 
        return cls(df)
    
    def prepare_data(self):
        """
        Prepare data for plotting by converting timestamps and ensuring required columns exist
        """
        # Convert ts_event to datetime if it's not already
        if 'ts_event' in self.df.columns:
            self.df['datetime'] = pd.to_datetime(self.df['ts_event'])
        else:
            raise ValueError("ts_event column not found in DataFrame")
        
        # Check for required columns
        if 'price' not in self.df.columns:
            raise ValueError("price column not found in DataFrame")
        
        if 'size' not in self.df.columns:
            print("Warning: size column not found, setting default size of 1")
            self.df['size'] = 1
        
        # Sort by datetime for proper plotting
        self.df = self.df.sort_values('datetime').reset_index(drop=True)
    
    def plot(self, figsize=(12, 8), title="Price and Size Chart"):
        """
        Create the plot with price on top and size bars at bottom
        
        Args:
            figsize (tuple): Figure size (width, height)
            title (str): Plot title
        """
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, height_ratios=[3, 1], 
                                       sharex=True, gridspec_kw={'hspace': 0.05})
        
        # Plot price on top subplot
        ax1.plot(self.df['datetime'], self.df['price'], linewidth=1, color='blue', alpha=0.8)
        ax1.set_ylabel('Price', fontsize=12)
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='y', labelsize=10)
        
        # Add price statistics to the plot
        min_price = self.df['price'].min()
        max_price = self.df['price'].max()
        avg_price = self.df['price'].mean()
        
        # Add horizontal lines for min, max, average
        ax1.axhline(y=min_price, color='red', linestyle='--', alpha=0.5, label=f'Min: ${min_price:.4f}')
        ax1.axhline(y=max_price, color='green', linestyle='--', alpha=0.5, label=f'Max: ${max_price:.4f}')
        ax1.axhline(y=avg_price, color='orange', linestyle='--', alpha=0.5, label=f'Avg: ${avg_price:.4f}')
        ax1.legend(loc='upper right', fontsize=9)
        
        # Plot size as bars on bottom subplot
        bar_width = pd.Timedelta(minutes=1)  # Match the 1-minute resampling interval
        ax2.bar(self.df['datetime'], self.df['size'], width=bar_width, 
                color='steelblue', alpha=0.7, edgecolor='darkblue', linewidth=0.5)
        ax2.set_ylabel('Size', fontsize=12)
        ax2.set_xlabel('Time', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='both', labelsize=10)
        
        # Format x-axis for time display
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # Add summary statistics
        total_volume = self.df['size'].sum()
        avg_size = self.df['size'].mean()
        max_size = self.df['size'].max()
        
        stats_text = f'Total Volume: {total_volume:,.0f} | Avg Size: {avg_size:.1f} | Max Size: {max_size:,.0f}'
        fig.text(0.5, 0.02, stats_text, ha='center', fontsize=10, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.5))
        
        # Adjust layout
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)
        
        return fig, (ax1, ax2)
    
    def save_plot(self, filename, figsize=(12, 8), title="Price and Size Chart", dpi=300):
        """
        Save the plot to a file
        
        Args:
            filename (str): Output filename with extension (e.g., 'plot.png')
            figsize (tuple): Figure size (width, height)
            title (str): Plot title
            dpi (int): Resolution for saved image
        """
        fig, axes = self.plot(figsize=figsize, title=title)
        plt.savefig(filename, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        print(f"Plot saved as: {filename}")
    
    def show_plot(self, figsize=(12, 8), title="Price and Size Chart"):
        """
        Display the plot
        
        Args:
            figsize (tuple): Figure size (width, height)
            title (str): Plot title
        """
        fig, axes = self.plot(figsize=figsize, title=title)
        plt.show()
    
    def get_summary_stats(self):
        """
        Get summary statistics of the data
        
        Returns:
            dict: Dictionary containing summary statistics
        """
        stats = {
            'total_records': len(self.df),
            'time_range': {
                'start': self.df['datetime'].min(),
                'end': self.df['datetime'].max(),
                'duration': self.df['datetime'].max() - self.df['datetime'].min()
            },
            'price_stats': {
                'min': self.df['price'].min(),
                'max': self.df['price'].max(),
                'mean': self.df['price'].mean(),
                'std': self.df['price'].std(),
                'range': self.df['price'].max() - self.df['price'].min()
            },
            'size_stats': {
                'total_volume': self.df['size'].sum(),
                'avg_size': self.df['size'].mean(),
                'max_size': self.df['size'].max(),
                'min_size': self.df['size'].min()
            }
        }
        return stats


# Example usage
if __name__ == "__main__":
    # Load from CSV using class method
    csv_path = "C:\\Users\\fy37bby\\user\\dev\\misc\\backtest\\rsc\\XNAS-20260127-WTVN5DQMQ6\\xnas-itch-20260115.mbp-10_ONDS.csv"
    
    try:
        plotter_from_csv = PlotOhlc.from_csv(csv_path)
        plotter_from_csv.show_plot(title="ONDS Price and Size Data")
        
        # Print summary statistics
        stats = plotter_from_csv.get_summary_stats()
        print("\nSummary Statistics:")
        print(f"Total Records: {stats['total_records']}")
        print(f"Time Range: {stats['time_range']['start']} to {stats['time_range']['end']}")
        print(f"Price Range: ${stats['price_stats']['min']:.4f} - ${stats['price_stats']['max']:.4f}")
        print(f"Total Volume: {stats['size_stats']['total_volume']:,}")
    
    except Exception as e:
        print(f"Error loading or plotting CSV: {e}")
