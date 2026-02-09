import pandas as pd
import os

isLogging = False

class DataBento:
    
    def load_csv(self, csv_path):
        """
        Load CSV file and return DataFrame
        
        Args:
            csv_path (str): Path to the CSV file
            
        Returns:
            pandas.DataFrame: Loaded DataFrame
        """
        try:
            df = pd.read_csv(csv_path, sep=',')
            return df
        except Exception as e:
            raise ValueError(f"Error loading CSV file {csv_path}: {e}")
    
    def filter_by_symbol(self, csv_path, symbol, output_filename=None):
        """
        Filter Bento MBP-10 CSV data by symbol and save to new CSV
        
        Args:
            csv_path (str): Path to the input Bento CSV file
            symbol (str): Symbol to filter by (e.g., 'ONDS')
            output_filename (str, optional): Output CSV filename. If None, generates automatically
            
        Returns:
            str: Path to the saved filtered CSV file
        """
        # Read the CSV file with semicolon separator
        df = self.load_csv(csv_path)
        
        # Filter by symbol
        filtered_df = df[df['symbol'] == symbol].copy()
        
        if len(filtered_df) == 0:
            print(f"Warning: No records found for symbol '{symbol}'")
            return None
        
        # Generate output filename if not provided
        if output_filename is None:
            base_name = os.path.splitext(os.path.basename(csv_path))[0]
            output_filename = f"{base_name}_{symbol}_filtered.csv"
        
        # Save to CSV with semicolon separator to maintain format
        filtered_df.to_csv(output_filename, sep=',', index=False)
        
        print(f"Filtered CSV saved as: {output_filename}")
        print(f"Records saved: {len(filtered_df)} (filtered from {len(df)} total records)")
        print(f"Symbol: {symbol}")
        
        return output_filename
    
    def get_available_symbols(self, csv_path):
        """
        Get list of unique symbols in the CSV file
        
        Args:
            csv_path (str): Path to the input Bento CSV file
            
        Returns:
            list: List of unique symbols found in the file
        """
        df = self.load_csv(csv_path)
        symbols = df['symbol'].unique().tolist()
        
        if isLogging:
            print(f"Available symbols: {symbols}")
            print(f"Total symbols: {len(symbols)}")
        
        return symbols
    
    def get_data_info(self, csv_path):
        """
        Get basic information about the Bento CSV file
        
        Args:
            csv_path (str): Path to the input Bento CSV file
            
        Returns:
            dict: Dictionary with file information
        """
        df = self.load_csv(csv_path)
        
        info = {
            'total_records': len(df),
            'columns': df.columns.tolist(),
            'symbols': df['symbol'].unique().tolist(),
            'date_range': {
                'start': df['ts_recv'].iloc[0] if len(df) > 0 else None,
                'end': df['ts_recv'].iloc[-1] if len(df) > 0 else None
            },
            'record_types': df['rtype'].unique().tolist() if 'rtype' in df.columns else []
        }
        
        if isLogging:
            print("=== Bento Data Info ===")
            print(f"Total records: {info['total_records']}")
            print(f"Symbols: {info['symbols']}")
            print(f"Record types: {info['record_types']}")
            print(f"Date range: {info['date_range']['start']} to {info['date_range']['end']}")
            print(f"Total columns: {len(info['columns'])}")
        
        return info
    
    def get_price_range(self, csv_path, symbol=None):
        """
        Get max and min price from Bento CSV file and calculate divergence percentage
        
        Args:
            csv_path (str): Path to the input Bento CSV file
            symbol (str): Symbol to filter by (required)
            
        Returns:
            dict: Dictionary with 'min_price', 'max_price', 'price_range', 'divergence_percent'
        """
        df = self.load_csv(csv_path)
        
        # Apply all filters using the dedicated method
        df = self.filter_data(df, symbol=symbol, exclude_cancel=True, depth_level=0, exclude_morning_minutes=10, min_size=20)

        # Calculate micro price using the dedicated method
        price_series = self.get_micro_price(df)
        
        if len(price_series) == 0:
            raise ValueError("No valid price data found")
        
        min_price = float(price_series.min())
        max_price = float(price_series.max())
        price_range = max_price - min_price
        
        # Calculate divergence percentage
        if min_price > 0:
            divergence_percent = ((max_price - min_price) / min_price) * 100
        else:
            divergence_percent = 0.0
        
        result = {
            'min_price': min_price,
            'max_price': max_price,
            'price_range': price_range,
            'divergence_percent': divergence_percent
        }
        
        if isLogging:
            print(f"Price analysis for {symbol}:")
            print(f"Min price: ${min_price:.4f}")
            print(f"Max price: ${max_price:.4f}")
            print(f"Price range: ${price_range:.4f}")
            print(f"Divergence: {divergence_percent:.2f}%")
            print(f"Records analyzed: {len(price_series)}")
        
        return result
    
    def filter_data(self, df, symbol=None, exclude_cancel=True, depth_level=0, exclude_morning_minutes=10, min_size=20):
        """
        Apply various filters to the DataFrame
        
        Args:
            df (pandas.DataFrame): Input DataFrame
            symbol (str, optional): Symbol to filter by. If None, no symbol filter applied
            exclude_cancel (bool): Whether to exclude canceled orders. If None, no filter applied
            depth_level (int, optional): Depth level to filter by. If None, no depth filter applied
            exclude_morning_minutes (int, optional): Minutes to exclude from start of trading (9:00). If None, no time filter applied
            min_size (int, optional): Minimum size filter. If None, no size filter applied
            
        Returns:
            pandas.DataFrame: Filtered DataFrame
        """
        filtered_df = df.copy()
        
        # Filter by symbol if specified
        if symbol is not None:
            filtered_df = filtered_df[filtered_df['symbol'] == symbol].copy()
            if len(filtered_df) == 0:
                raise ValueError(f"No data found for symbol: {symbol}")
        
        # Filter canceled orders if specified
        if exclude_cancel is not None and exclude_cancel:
            filtered_df = filtered_df[filtered_df['action'] != "C"].copy()
            if len(filtered_df) == 0:
                raise ValueError(f"All actions are Cancel")
        
        # Filter by depth level if specified
        if depth_level is not None:
            filtered_df = filtered_df[filtered_df['depth'] == depth_level].copy()
            if len(filtered_df) == 0:
                raise ValueError(f"No orders at level {depth_level}")
        
        # Filter out first N minutes of trade using ts_event if specified
        if exclude_morning_minutes is not None and exclude_morning_minutes > 0 and 'ts_event' in filtered_df.columns:
            filtered_df['ts_event_dt'] = pd.to_datetime(filtered_df['ts_event'])
            filtered_df['trade_time'] = filtered_df['ts_event_dt'].dt.time
            
            # Filter out 9:00:00 to 9:0N:59 (first N minutes)
            morning_start = pd.Timestamp('09:00:00').time()
            morning_end = pd.Timestamp(f'09:{exclude_morning_minutes:02d}:00').time()
            
            # Keep only data outside the morning window
            filtered_df = filtered_df[(filtered_df['trade_time'] < morning_start) | (filtered_df['trade_time'] >= morning_end)].copy()
            
            if len(filtered_df) == 0:
                raise ValueError(f"No data found after filtering first {exclude_morning_minutes} minutes of trade")
        
        # Filter out records with size < min_size if specified
        if min_size is not None and 'size' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['size'] >= min_size].copy()
            
            if len(filtered_df) == 0:
                raise ValueError(f"No data found after applying size filter (>= {min_size})")
        
        return filtered_df
    
    def get_micro_price(self, df):
        """
        Calculate micro price (weighted median between bid and ask at level 0)
        
        Args:
            df (pandas.DataFrame): DataFrame with bid/ask price and size columns
            
        Returns:
            pandas.Series: Price series calculated as weighted median
        """
        # Determine price to use - weighted median between bid and ask at level 0
        if 'bid_px_00' in df.columns and 'ask_px_00' in df.columns and 'bid_sz_00' in df.columns and 'ask_sz_00' in df.columns:
            # Calculate weighted median: (bid_px_00 * ask_sz_00 + ask_px_00 * bid_sz_00) / (ask_sz_00 + bid_sz_00)
            df['weighted_price'] = (df['bid_px_00'] * df['ask_sz_00'] + df['ask_px_00'] * df['bid_sz_00']) / (df['ask_sz_00'] + df['bid_sz_00'])
            price_series = df['weighted_price'].dropna()
        else:
            raise ValueError("Required bid/ask price and size columns not found")
        
        return price_series
    
    def smooth_price_jumps(self, df, max_jump_percentage):
        """
        Smooth price jumps by replacing prices that jump more than the specified percentage
        with the previous value
        
        Args:
            df (pandas.DataFrame): Input DataFrame with price data
            max_jump_percentage (float): Maximum allowed percentage jump between consecutive prices
            
        Returns:
            pandas.DataFrame: DataFrame with smoothed prices
        """
        df_copy = df.copy()
        
        # Calculate micro price for the analysis
        try:
            price_series = self.get_micro_price(df_copy)
            df_copy['current_price'] = price_series
        except ValueError:
            # If micro price calculation fails, try to use existing price column
            if 'price' in df_copy.columns:
                df_copy['current_price'] = df_copy['price']
            else:
                raise ValueError("Cannot calculate or find price data for smoothing")
        
        # Calculate percentage change between consecutive prices
        df_copy['price_pct_change'] = df_copy['current_price'].pct_change() * 100
        
        # Identify jumps that exceed the threshold
        jump_mask = abs(df_copy['price_pct_change']) > max_jump_percentage
        
        # Replace excessive jumps with previous value
        if jump_mask.any():
            for idx in df_copy[jump_mask].index:
                if idx > 0:  # Skip first row as it has no previous value
                    prev_idx = df_copy.index[df_copy.index.get_loc(idx) - 1]
                    
                    # Update the weighted_price if it exists, or create it
                    if 'weighted_price' in df_copy.columns:
                        df_copy.loc[idx, 'weighted_price'] = df_copy.loc[prev_idx, 'current_price']
                    
                    # Also update current_price for consistency
                    df_copy.loc[idx, 'current_price'] = df_copy.loc[prev_idx, 'current_price']
            
            if isLogging:
                jump_count = jump_mask.sum()
                print(f"Smoothed {jump_count} price jumps exceeding {max_jump_percentage}%")
        
        # Clean up temporary columns
        df_copy.drop(['current_price', 'price_pct_change'], axis=1, inplace=True, errors='ignore')
        
        return df_copy
    
    def resample_data(self, df, sampling_time):
        """
        Resample tick data by keeping only the first entry within each time interval
        
        Args:
            df (pandas.DataFrame): Input DataFrame with ts_event column
            sampling_time (str): Sampling interval ('1s', '1m', '1h' for second, minute, hour)
            
        Returns:
            pandas.DataFrame: Resampled DataFrame with first entry per time interval
        """
        df_copy = df.copy()
        
        # Check if ts_event column exists
        if 'ts_event' not in df_copy.columns:
            raise ValueError("ts_event column not found in DataFrame")
        
        # Convert ts_event to datetime
        df_copy['ts_event_dt'] = pd.to_datetime(df_copy['ts_event'])
        
        # Parse sampling time parameter and convert to pandas frequency
        time_mapping = {
            's': 'S',    # seconds
            'm': 'T',    # minutes  
            'h': 'H'     # hours
        }
        
        # Extract number and unit from sampling_time (e.g., '1s' -> 1, 's')
        import re
        match = re.match(r'(\d+)([smh])', sampling_time.lower())
        if not match:
            raise ValueError("Invalid sampling_time format. Use format like '1s', '1m', '1h'")
        
        number, unit = match.groups()
        pandas_freq = f"{number}{time_mapping[unit]}"
        
        # Set ts_event_dt as index for resampling
        df_copy.set_index('ts_event_dt', inplace=True)
        
        # Resample and keep first entry in each interval
        resampled_df = df_copy.resample(pandas_freq).first()
        
        # Remove NaN rows (intervals with no data)
        resampled_df = resampled_df.dropna(how='all')
        
        # Reset index to get ts_event_dt back as a column
        resampled_df.reset_index(inplace=True)
        
        # Update original ts_event column with resampled timestamps
        resampled_df['ts_event'] = resampled_df['ts_event_dt'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        if isLogging:
            original_count = len(df)
            resampled_count = len(resampled_df)
            print(f"Resampled from {original_count} to {resampled_count} records using {sampling_time} intervals")
            print(f"Reduction: {((original_count - resampled_count) / original_count * 100):.1f}%")
        
        return resampled_df
    
    def split_csv_by_symbol(self, csv_path, output_dir=None):
        """
        Split a CSV file into multiple files, one per symbol
        
        Args:
            csv_path (str): Path to the input CSV file
            output_dir (str, optional): Output directory for split files. If None, uses same directory as input
            
        Returns:
            dict: Dictionary with symbol as key and output file path as value
        """
        df = self.load_csv(csv_path)
        
        # Get unique symbols
        symbols = df['symbol'].unique()
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(csv_path)
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # Get base filename without extension
        base_name = os.path.splitext(os.path.basename(csv_path))[0]
        
        output_files = {}
        
        for symbol in symbols:
            # Filter data for this symbol
            symbol_df = df[df['symbol'] == symbol].copy()
            
            # Generate output filename
            output_filename = f"{base_name}_{symbol}.csv"
            output_path = os.path.join(output_dir, output_filename)
            
            # Save filtered data
            symbol_df.to_csv(output_path, sep=',', index=False)
            output_files[symbol] = output_path
            
            if isLogging:
                print(f"Created {output_filename} with {len(symbol_df)} records for symbol {symbol}")
        
        if isLogging:
            print(f"Split {csv_path} into {len(output_files)} files by symbol")
            print(f"Symbols processed: {list(symbols)}")
            print(f"Output directory: {output_dir}")
        
        # Delete the original CSV file if split was successful
        if output_files:
            try:
                os.remove(csv_path)
                if isLogging:
                    print(f"Deleted original file: {csv_path}")
            except Exception as e:
                print(f"Warning: Could not delete original file {csv_path}: {e}")
        
        return output_files
    
    def load_bento_mbp10_data(self, filename, timeframe='1T', symbol=None, microprice=True):
        """
        Load Bento MBP-10 tick data and convert to OHLCV format for backtesting
        while preserving all original columns
        
        Args:
            filename (str): Path to Bento MBP-10 CSV file
            timeframe (str): Resampling timeframe ('1T', '5T', '1H', etc.)
            symbol (str, optional): Filter by specific symbol
        
        Returns:
            pandas.DataFrame: OHLCV data with all original Bento columns preserved
        """
        # Read Bento CSV with semicolon separator
        df = self.load_csv(filename)
        df = self.filter_data(df, symbol=symbol, exclude_cancel=False, depth_level=None, exclude_morning_minutes=10, min_size=20)   
        df = self.smooth_price_jumps(df, 0.5)

        # Filter by symbol if specified
        if symbol:
            df = df[df['symbol'] == symbol].copy()
            if len(df) == 0:
                raise ValueError(f"No data found for symbol: {symbol}")
        
        # Convert timestamp to datetime and set as index
        df['DateTime'] = pd.to_datetime(df['ts_recv'])
        df.set_index('DateTime', inplace=True)
        
        # Create price from bid/ask midpoint (or use specific price if available)
        if 'price' in df.columns and df['price'].notna().any() and not microprice:
            # Use price column if available and not NaN
            price_series = df['price'].fillna(method='ffill')
        else:
            # Calculate midpoint from best bid/ask
            df['mid_price'] = (df['bid_px_00'] + df['ask_px_00']) / 2
            price_series = df['mid_price'].fillna(method='ffill')
        
        # Resample to create OHLCV bars
        ohlcv = price_series.resample(timeframe).ohlc()
        ohlcv.columns = ['Open', 'High', 'Low', 'Close']
        
        # Add volume (sum of size column or use bid/ask sizes)
        if 'size' in df.columns:
            ohlcv['Volume'] = df['size'].resample(timeframe).sum()
        else:
            # Use sum of bid and ask sizes at level 0
            ohlcv['Volume'] = (df['bid_sz_00'] + df['ask_sz_00']).resample(timeframe).sum()
        
        # Add all original Bento columns as additional data (last value in each timeframe)
        bento_columns = [col for col in df.columns if col not in ['mid_price']]
        for col in bento_columns:
            if df[col].dtype in ['object', 'string']:
                # For string/object columns, take the last value
                ohlcv[f'bento_{col}'] = df[col].resample(timeframe).last()
            else:
                # For numeric columns, you can choose mean, last, etc.
                ohlcv[f'bento_{col}'] = df[col].resample(timeframe).last()
        
        # Add some useful derived columns
        ohlcv['bento_spread'] = (df['ask_px_00'] - df['bid_px_00']).resample(timeframe).mean()
        ohlcv['bento_tick_count'] = df.groupby(df.index.floor(timeframe)).size().reindex(ohlcv.index, fill_value=0)
        
        # Remove NaN rows
        ohlcv = ohlcv.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
        
        if isLogging:
            print(f"Loaded {len(ohlcv)} {timeframe} bars from {len(df)} ticks")
            print(f"Date range: {ohlcv.index[0]} to {ohlcv.index[-1]}")
            print(f"Available Bento columns: {len([col for col in ohlcv.columns if col.startswith('bento_')])}")
            
        return ohlcv

if __name__ == "__main__":
    # Create DataBento instance
    data_bento = DataBento()
    csv_folder_path = "C:\\Users\\fy37bby\\user\\dev\\misc\\backtest\\rsc\\XNAS-20260127-WTVN5DQMQ6\\xnas-itch-20260126.mbp-10.csv_"

    # Parse over csv_folder_path and check for 5% divergence with symbol ONDS
    import glob
    csv_files = glob.glob(os.path.join(csv_folder_path, "*.csv"))

    print(f"Checking {len(csv_files)} CSV files for ONDS with 5% divergence threshold...")

    for csv_file in csv_files:
        try:
            # Split CSV by symbol first
            #split_files = data_bento.split_csv_by_symbol(csv_file)
            
            # Get price range for ONDS symbol from the split file if it exists
            if 'ONDS' in csv_file:
                onds_file = csv_file
                result = data_bento.get_price_range(onds_file, symbol='ONDS')
                
                # Check if divergence is >= 5%
                if result['divergence_percent'] >= 5.0:
                    filename = os.path.basename(csv_file)
                    print(f"*** {filename} - Divergence: {result['divergence_percent']:.2f}% (Min: ${result['min_price']:.4f}, Max: ${result['max_price']:.4f})")
            else:
                # No ONDS symbol found in this file
                continue
                
        except Exception as e:
            # Skip files that have issues
            print(f"Error processing {os.path.basename(csv_file)}: {e}")
            continue

    #csv_path = "C:\\Users\\fy37bby\\user\\dev\\misc\\backtest\\rsc\\XNAS-20260127-WTVN5DQMQ6\\xnas-itch-20260126.mbp-10.csv\\xnas-itch-20260126.mbp-10.csv"
    # Filter by specific symbol
    #filtered_file = data_bento.filter_by_symbol(csv_path, 'ONDS')