import sys
import os

# Add the parent directory to the path to import data modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_ohlc_bento import DataOhlcBento
from data.data_bento import DataBento

def test_trailing_obi():
    """Test trailing_obi method with ONDS data"""
    csv_path = "C:\\Users\\fy37bby\\user\\dev\\misc\\backtest\\rsc\\XNAS-20260127-WTVN5DQMQ6\\xnas-itch-20260115.mbp-10_ONDS.csv"
    
    print("Testing trailing_obi method...")
    print(f"Loading CSV: {csv_path}")
    
    try:
        # Load the CSV data using DataBento
        data_bento = DataBento()
        df = data_bento.load_csv(csv_path)
        
        print(f"Loaded {len(df)} records")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Date range: {df['ts_event'].iloc[0]} to {df['ts_event'].iloc[-1]}")
        
        # Create DataOhlcBento instance (we don't need OHLCV data for this test)
        data_ohlc = DataOhlcBento(None)
        
        # Test trailing_obi at different points in the data
        test_indices = [100, 500, 1000, len(df)//2, len(df)-100]
        test_durations = [1.0, 5.0, 10.0] 
        
        print("\n=== Testing trailing_obi at different indices and durations ===")
        
        for current_index in test_indices:
            if current_index >= len(df):
                continue
                
            print(f"\nTesting at index {current_index} (timestamp: {df['ts_event'].iloc[current_index]})")
            
            for duration in test_durations:
                try:
                    obi = data_ohlc.trailing_obi(df, current_index, duration, depth=10)
                    print(f"  Duration {duration}s: OBI = {obi:.6f}")
                except Exception as e:
                    print(f"  Duration {duration}s: Error = {e}")
        
        # Test with different depth levels
        print("\n=== Testing different depth levels (10s duration, index 1000) ===")
        test_index = 1000
        if test_index < len(df):
            for depth in [1, 3, 5, 10]:
                try:
                    obi = data_ohlc.trailing_obi(df, test_index, 10.0, depth=depth)
                    print(f"  Depth {depth}: OBI = {obi:.6f}")
                except Exception as e:
                    print(f"  Depth {depth}: Error = {e}")
        
        # Show some sample bid/ask data
        print("\n=== Sample bid/ask size data (first 5 records) ===")
        for i in range(min(5, len(df))):
            bid_sz_00 = df['bid_sz_00'].iloc[i] if 'bid_sz_00' in df.columns else 'N/A'
            ask_sz_00 = df['ask_sz_00'].iloc[i] if 'ask_sz_00' in df.columns else 'N/A'
            print(f"  Record {i}: bid_sz_00={bid_sz_00}, ask_sz_00={ask_sz_00}")
        
        print("\nTrailing OBI test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_trailing_obi()