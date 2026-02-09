import pandas as pd


class CsvMgr:
    
    def load_and_resample_csv(self, filename, timeframe='1T'):
        """
        Load tick data and resample to OHLCV bars
        timeframe examples: '1T' (1 minute), '5T' (5 minutes), '1H' (1 hour)
        """
        # Read the CSV file
        df = pd.read_csv(filename, header=None, 
                         names=['Date', 'Time', 'Price1', 'Price2', 'Price3', 'Volume'])
        
        # Combine date and time
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        df.set_index('DateTime', inplace=True)
        
        # Use the middle price or most relevant price as the main price
        df['Price'] = df['Price1']  # Adjust this based on which price column you want to use
        
        # Resample to create OHLCV bars
        ohlcv = df['Price'].resample(timeframe).ohlc()
        ohlcv.columns = ['Open', 'High', 'Low', 'Close']
        
        # Add volume (sum volume over the timeframe)
        ohlcv['Volume'] = df['Volume'].resample(timeframe).sum()
        
        # Remove any NaN rows
        ohlcv = ohlcv.dropna()
        
        return ohlcv
    
    def cut_csv(self, filename, start_date, end_date=None, output_filename=None):
        """
        Extract entries from CSV file between start_date and end_date and save to new CSV
        
        Args:
            filename (str): Path to the input CSV file
            start_date (str): Start date in format 'MM/DD/YYYY' or 'YYYY-MM-DD'
            end_date (str, optional): End date in same format. If None, extract until end of file
            output_filename (str, optional): Output CSV filename. If None, generates automatically
            
        Returns:
            str: Path to the saved CSV file
        """
        # Read the CSV file
        df = pd.read_csv(filename, header=None, 
                         names=['Date', 'Time', 'Price1', 'Price2', 'Price3', 'Volume'])
        
        # Combine date and time
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        
        # Convert start_date to datetime
        start_dt = pd.to_datetime(start_date)
        
        # Filter from start_date
        if end_date is None:
            # Extract from start_date until end
            filtered_df = df[df['DateTime'] >= start_dt]
        else:
            # Extract from start_date to end_date
            end_dt = pd.to_datetime(end_date)
            filtered_df = df[(df['DateTime'] >= start_dt) & (df['DateTime'] <= end_dt)]
        
        # Reset index
        filtered_df = filtered_df.reset_index(drop=True)
        
        # Generate output filename if not provided
        if output_filename is None:
            import os
            base_name = os.path.splitext(os.path.basename(filename))[0]
            start_str = start_date.replace('/', '_').replace('-', '_')
            if end_date:
                end_str = end_date.replace('/', '_').replace('-', '_')
                output_filename = f"{base_name}_{start_str}_to_{end_str}.csv"
            else:
                output_filename = f"{base_name}_{start_str}_to_end.csv"
        
        # Save to CSV (only the original columns, not DateTime)
        filtered_df[['Date', 'Time', 'Price1', 'Price2', 'Price3', 'Volume']].to_csv(
            output_filename, header=False, index=False
        )
        
        print(f"Filtered CSV saved as: {output_filename}")
        print(f"Records saved: {len(filtered_df)}")
        
        return output_filename
    
    
    
# From start date to end (auto-generated filename)
csv_manager = CsvMgr()
output_file = csv_manager.cut_csv("c:\\Users\\fy37bby\\user\\dev\\misc\\backtest\\rsc\\WDC_tickbidask.csv", '09/03/2025')