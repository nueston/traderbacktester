from backtesting import Strategy
import pandas as pd
from data.data_ohlc_bento import DataOhlcBento


class BentoStrategy(Strategy):
    """
    Strategy that utilizes Bento MBP-10 market data
    """
    def init(self):
        # Initialize DataOhlcBento manager
        self.data_manager = DataOhlcBento(self.data.df)
        self.iteration = 0
        
        # Initialize indicators history - maintains last 10 values for each indicator
        self.indicators_history = {
            'obi': [],
            'spread': [],
        }
        self.max_history_length = 10
        self.last_monitor_time = None
        
    def get_current_spread(self):
        """Get current bid-ask spread"""
        if hasattr(self.data, 'bento_spread'):
            return self.data.bento_spread[-1]
        return None
    
    def get_current_bid_ask(self):
        """Get current best bid and ask prices"""
        bid = self.data_manager.get_bento_column('bid_px_00')
        ask = self.data_manager.get_bento_column('ask_px_00')
        if bid is not None and ask is not None:
            return bid.iloc[-1] if len(bid) > 0 else None, ask.iloc[-1] if len(ask) > 0 else None
        return None, None
    
    def get_market_depth(self, level=0):
        """Get bid/ask size at specific depth level"""
        bid_size = self.data_manager.get_bento_column(f'bid_sz_{level:02d}')
        ask_size = self.data_manager.get_bento_column(f'ask_sz_{level:02d}')
        if bid_size is not None and ask_size is not None:
            return bid_size.iloc[-1] if len(bid_size) > 0 else 0, ask_size.iloc[-1] if len(ask_size) > 0 else 0
        return 0, 0
    
    def print_market_data(self):
        """Print current market data including Bento-specific information"""
        current_time = self.data.index[-1]
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        bid, ask = self.get_current_bid_ask()
        spread = self.get_current_spread()
        bid_size, ask_size = self.get_market_depth(0)
        
        print(f"Time: {current_time}")
        print(f"Price: {current_price:.4f} | Volume: {current_volume}")
        print(f"Bid: {bid:.4f} ({bid_size}) | Ask: {ask:.4f} ({ask_size}) | Spread: {spread:.4f}")
        print(f"Position: {self.position.size} | Cash: ${self._broker._cash:.2f}")
        print("-" * 50)
    
    def monitor_indicators(self, monitor_frequency=30.0, trailing_duration=30.0):
        """
        Monitor and update indicators history
        
        Args:
            monitor_frequency (float): How often to calculate indicators (in seconds)
            trailing_duration (float): Duration in seconds for trailing calculations
            
        Returns:
            dict: Current indicator values
        """
        # Get current timestamp
        current_time = self.data.index[-1]
        
        # Check if it's time to monitor (based on time frequency)
        if self.last_monitor_time is not None:
            time_diff = (current_time - self.last_monitor_time).total_seconds()
            if time_diff < monitor_frequency:
                return None
        
        self.last_monitor_time = current_time
        current_indicators = {}
        
        # Calculate OBI using trailing_obi method
        if hasattr(self.data, 'df'):
            obi_value = self.data_manager.trailing_obi(
                df=self.data.df, 
                current_index=self.iteration-1, 
                trailing_duration=trailing_duration, 
                depth=10
            )
            current_indicators['obi'] = obi_value
            
            # Update OBI history
            self.indicators_history['obi'].append(obi_value)
            if len(self.indicators_history['obi']) > self.max_history_length:
                self.indicators_history['obi'].pop(0)
        
        # Calculate spread
        spread_value = self.data_manager.get_current_spread()
        if spread_value is not None:
            current_indicators['spread'] = spread_value
            
            # Update spread history
            self.indicators_history['spread'].append(spread_value)
            if len(self.indicators_history['spread']) > self.max_history_length:
                self.indicators_history['spread'].pop(0)
        
        return current_indicators
    
    def next(self):
        # Skip first few bars for indicator warmup
        if len(self.data.Close) < 21:
            return
        
        # Update data manager current index
        self.data_manager.set_current_index(self.iteration)
        self.iteration += 1
        
        # Monitor indicators every 300 seconds with 300-second trailing duration
        current_indicators = self.monitor_indicators(monitor_frequency=300.0, trailing_duration=300.0)
        
        # Get market microstructure data using DataOhlcBento
        bid, ask = self.get_current_bid_ask()
        spread = self.data_manager.get_current_spread()
        
        # Strategy logic using market microstructure data
        if (spread is not None and spread < 0.05 and  # Low spread condition
            current_indicators and current_indicators.get('obi', 0) > 0.1 and  # Positive order book imbalance
            not self.position):
            self.buy()
            print("BUY SIGNAL")
            self.print_market_data()
            if current_indicators:
                print(f"Current OBI: {current_indicators.get('obi', 'N/A'):.4f}")
                print(f"OBI History: {[f'{x:.4f}' for x in self.indicators_history['obi'][-3:]]}")  # Last 3 values
            
        elif (current_indicators and current_indicators.get('obi', 0) < -0.1 and  # Negative order book imbalance
              self.position):
            self.position.close()
            print("SELL SIGNAL")
            self.print_market_data()
            if current_indicators:
                print(f"Current OBI: {current_indicators.get('obi', 'N/A'):.4f}")
                print(f"OBI History: {[f'{x:.4f}' for x in self.indicators_history['obi'][-3:]]}")  # Last 3 values