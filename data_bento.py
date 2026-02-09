import pandas as pd
import os


class DataBento:
    
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
        df = pd.read_csv(csv_path, sep=',')
        
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
        df = pd.read_csv(csv_path, sep=',')
        symbols = df['symbol'].unique().tolist()
        
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
        df = pd.read_csv(csv_path, sep=',')
        
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
        
        print("=== Bento Data Info ===")
        print(f"Total records: {info['total_records']}")
        print(f"Symbols: {info['symbols']}")
        print(f"Record types: {info['record_types']}")
        print(f"Date range: {info['date_range']['start']} to {info['date_range']['end']}")
        print(f"Total columns: {len(info['columns'])}")
        
        return info
    
    def load_bento_mbp10_data(self, filename, timeframe='1T', symbol=None):
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
        df = pd.read_csv(filename, sep=',')
        
        # Filter by symbol if specified
        if symbol:
            df = df[df['symbol'] == symbol].copy()
            if len(df) == 0:
                raise ValueError(f"No data found for symbol: {symbol}")
        
        # Convert timestamp to datetime and set as index
        df['DateTime'] = pd.to_datetime(df['ts_recv'])
        df.set_index('DateTime', inplace=True)
        
        # Create price from bid/ask midpoint (or use specific price if available)
        if 'price' in df.columns and df['price'].notna().any():
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
        
        print(f"Loaded {len(ohlcv)} {timeframe} bars from {len(df)} ticks")
        print(f"Date range: {ohlcv.index[0]} to {ohlcv.index[-1]}")
        print(f"Available Bento columns: {len([col for col in ohlcv.columns if col.startswith('bento_')])}")
        
        return ohlcv


# Create DataBento instance
#data_bento = DataBento()
#csv_path = "C:\\Users\\fy37bby\\user\\dev\\misc\\backtest\\rsc\\XNAS-20260127-WTVN5DQMQ6\\xnas-itch-20260126.mbp-10.csv\\xnas-itch-20260126.mbp-10.csv"
# Filter by specific symbol
#filtered_file = data_bento.filter_by_symbol(csv_path, 'ONDS')