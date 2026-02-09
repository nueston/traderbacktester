from backtesting import Strategy
from backtesting.test import SMA
from backtesting.lib import crossover
import pandas as pd


class StrFull(Strategy):
    def init(self):
        # Store the close price data
        #self.price = self.data.Close
        #print(self.price)
        self.previous_price = None
        self.buy()
    
    def is_avg_growth(self, growth = 0.1, days_nb = 5):
        if self.data.Close[-2] - self.data.Open[-days_nb] > self.data.Close[-2]*growth:
            return True
        else :
            return False

    def print_data(self):
        current_cash = self._broker._cash
        print(f"{self.data.index[-1]} : Price: {self.data.Close[-1]} : Volume: {self.data.Volume[-1]} : Shares: {self.position.size} : Cash: {self._broker._cash:.2f} : Equity: {(self._broker.equity):.2f}")
        
    def next(self):
         # Skip first 5 bars
        if len(self.data.Close) < 6:  # Need at least 6 bars (0-5 = first 6)
            return
    
        # Buy when current price < last price (falling)
        if self.data.Close[-1] < self.data.Close[-2]*0.95:
            print("bought")
            self.buy()
            self.print_data()
        # Sell when current price > last price (rising) and we have a position
        #elif self.data.Close[-1] > self.data.Close[-2]*1.1:
        elif self.is_avg_growth():
            print("sold")
            self.position.close(0.2) 
            self.print_data()

class BentoStrategy(Strategy):
    """
    Strategy that utilizes Bento MBP-10 market data
    """
    def init(self):
        # Standard technical indicators
        close = self.data.Close
        self.sma_fast = self.I(SMA, close, 5)
        self.sma_slow = self.I(SMA, close, 20)
        
    def get_bento_data(self, column_name):
        """Helper method to access Bento-specific columns"""
        full_column_name = f'bento_{column_name}'
        if hasattr(self.data, 'df') and full_column_name in self.data.df.columns:
            return self.data.df[full_column_name].iloc[:len(self.data.Close)]
        return None
    
    def get_current_spread(self):
        """Get current bid-ask spread"""
        if hasattr(self.data, 'bento_spread'):
            return self.data.bento_spread[-1]
        return None
    
    def get_current_bid_ask(self):
        """Get current best bid and ask prices"""
        bid = self.get_bento_data('bid_px_00')
        ask = self.get_bento_data('ask_px_00')
        if bid is not None and ask is not None:
            return bid.iloc[-1] if len(bid) > 0 else None, ask.iloc[-1] if len(ask) > 0 else None
        return None, None
    
    def get_market_depth(self, level=0):
        """Get bid/ask size at specific depth level"""
        bid_size = self.get_bento_data(f'bid_sz_{level:02d}')
        ask_size = self.get_bento_data(f'ask_sz_{level:02d}')
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
    
    def next(self):
        # Skip first few bars for indicator warmup
        if len(self.data.Close) < 21:
            return
        
        # Get market microstructure data
        bid, ask = self.get_current_bid_ask()
        spread = self.get_current_spread()
        
        # Strategy logic using both technical indicators and market microstructure
        if (crossover(self.sma_fast, self.sma_slow) and 
            spread is not None and spread < 0.05 and  # Low spread condition
            not self.position):
            self.buy()
            print("BUY SIGNAL")
            self.print_market_data()
            
        elif (crossover(self.sma_slow, self.sma_fast) and 
              self.position):
            self.position.close()
            print("SELL SIGNAL")
            self.print_market_data()


class LiquidityMonitorStrategy(Strategy):
    """
    Strategy that monitors market liquidity conditions and exits positions
    when liquidity deteriorates significantly
    """
    
    # Configurable parameters
    monitor_period = 10  # Number of iterations to monitor
    wait_period = 10     # Number of iterations to do nothing at start
    
    # Exit conditions (sell)
    bid_decrease_threshold = 0.60  # 60% decrease in bid liquidity
    spread_increase_threshold = 0.30  # 30% spread increase
    volume_increase_threshold = 0.30  # 30% volume increase
    exit_percentage = 0.40  # Close 40% of position
    
    # Entry conditions (buy)
    bid_increase_threshold = 0.60  # 60% increase in bid liquidity
    spread_increase_buy_threshold = 0.30  # 30% spread increase for buy
    volume_increase_buy_threshold = 0.30  # 30% volume increase for buy
    buy_percentage = 0.40  # Buy amount as percentage of cash
    
    def init(self):
        # Buy at initialization
        self.buy()
        
        # Initialize tracking arrays
        self.bid_liquidity_history = []
        self.spread_history = []
        self.volume_history = []
        self.iteration_count = 0
        
    def get_bento_data(self, column_name):
        """Helper method to access Bento-specific columns"""
        full_column_name = f'bento_{column_name}'
        if hasattr(self.data, 'df') and full_column_name in self.data.df.columns:
            return self.data.df[full_column_name].iloc[:len(self.data.Close)]
        return None
    
    def get_total_bid_liquidity(self):
        """Calculate total bid liquidity across all depth levels (0-9)"""
        total_bid_liquidity = 0
        for level in range(10):  # Levels 0-9
            bid_size = self.get_bento_data(f'bid_sz_{level:02d}')
            if bid_size is not None and len(bid_size) > 0:
                total_bid_liquidity += bid_size.iloc[-1] if not pd.isna(bid_size.iloc[-1]) else 0
        return total_bid_liquidity
    
    def get_current_spread(self):
        """Get current bid-ask spread"""
        if hasattr(self.data, 'bento_spread'):
            return self.data.bento_spread[-1]
        return None
    
    def get_current_volume(self):
        """Get current volume"""
        return self.data.Volume[-1]
    
    def check_liquidity_deterioration(self):
        """
        Check if liquidity has deteriorated significantly over the monitoring period
        Returns True if all conditions are met for position exit
        """
        if len(self.bid_liquidity_history) < self.monitor_period:
            return False
        
        # Get recent data (last monitor_period values)
        recent_bid_liquidity = self.bid_liquidity_history[-self.monitor_period:]
        recent_spreads = self.spread_history[-self.monitor_period:]
        recent_volumes = self.volume_history[-self.monitor_period:]
        
        # Calculate changes from start to end of monitoring period
        bid_start = recent_bid_liquidity[0]
        bid_end = recent_bid_liquidity[-1]
        spread_start = recent_spreads[0]
        spread_end = recent_spreads[-1]
        volume_start = recent_volumes[0]
        volume_end = recent_volumes[-1]
        
        # Avoid division by zero
        if bid_start == 0 or spread_start == 0 or volume_start == 0:
            return False
        
        # Calculate percentage changes
        bid_change = (bid_start - bid_end) / bid_start  # Decrease (positive value means decrease)
        spread_change = (spread_end - spread_start) / spread_start  # Increase
        volume_change = (volume_end - volume_start) / volume_start  # Increase
        
        # Check all conditions
        bid_condition = bid_change >= self.bid_decrease_threshold
        spread_condition = spread_change >= self.spread_increase_threshold
        volume_condition = volume_change >= self.volume_increase_threshold
        
        # Debug output
        if bid_condition or spread_condition or volume_condition:
            pass
            #print(f"Liquidity Check - Iteration {self.iteration_count}")
            #print(f"  Bid decrease: {bid_change:.2%} (threshold: {self.bid_decrease_threshold:.2%}) - {'✓' if bid_condition else '✗'}")
            #print(f"  Spread increase: {spread_change:.2%} (threshold: {self.spread_increase_threshold:.2%}) - {'✓' if spread_condition else '✗'}")
            #print(f"  Volume increase: {volume_change:.2%} (threshold: {self.volume_increase_threshold:.2%}) - {'✓' if volume_condition else '✗'}")
        
        return bid_condition and spread_condition and volume_condition
    
    def check_liquidity_improvement(self):
        """
        Check if liquidity has improved significantly over the monitoring period
        Returns True if all conditions are met for position entry
        """
        if len(self.bid_liquidity_history) < self.monitor_period:
            return False
        
        # Get recent data (last monitor_period values)
        recent_bid_liquidity = self.bid_liquidity_history[-self.monitor_period:]
        recent_spreads = self.spread_history[-self.monitor_period:]
        recent_volumes = self.volume_history[-self.monitor_period:]
        
        # Calculate changes from start to end of monitoring period
        bid_start = recent_bid_liquidity[0]
        bid_end = recent_bid_liquidity[-1]
        spread_start = recent_spreads[0]
        spread_end = recent_spreads[-1]
        volume_start = recent_volumes[0]
        volume_end = recent_volumes[-1]
        
        # Avoid division by zero
        if bid_start == 0 or spread_start == 0 or volume_start == 0:
            return False
        
        # Calculate percentage changes
        bid_change = (bid_end - bid_start) / bid_start  # Increase (positive value means increase)
        spread_change = (spread_end - spread_start) / spread_start  # Increase
        volume_change = (volume_end - volume_start) / volume_start  # Increase
        
        # Check all conditions
        bid_condition = bid_change >= self.bid_increase_threshold
        spread_condition = spread_change >= self.spread_increase_buy_threshold
        volume_condition = volume_change >= self.volume_increase_buy_threshold
        
        # Debug output
        if bid_condition or spread_condition or volume_condition:
            pass
            #print(f"Liquidity Improvement Check - Iteration {self.iteration_count}")
            #print(f"  Bid increase: {bid_change:.2%} (threshold: {self.bid_increase_threshold:.2%}) - {'✓' if bid_condition else '✗'}")
            #print(f"  Spread increase: {spread_change:.2%} (threshold: {self.spread_increase_buy_threshold:.2%}) - {'✓' if spread_condition else '✗'}")
            #print(f"  Volume increase: {volume_change:.2%} (threshold: {self.volume_increase_buy_threshold:.2%}) - {'✓' if volume_condition else '✗'}")
        
        return bid_condition and spread_condition and volume_condition
    
    def print_strategy_data(self):
        """Print current strategy-specific data"""
        current_time = self.data.index[-1]
        current_price = self.data.Close[-1]
        current_volume = self.get_current_volume()
        current_spread = self.get_current_spread()
        current_bid_liquidity = self.get_total_bid_liquidity()
        
        print(f"Time: {current_time}")
        print(f"Price: {current_price:.4f} | Volume: {current_volume}")
        print(f"Spread: {current_spread:.4f} | Total Bid Liquidity: {current_bid_liquidity}")
        print(f"Position: {self.position.size} | Cash: ${self._broker._cash:.2f}")
        print(f"Iteration: {self.iteration_count}")
        print("-" * 50)
    
    def next(self):
        self.iteration_count += 1
        
        # Do nothing for the first wait_period iterations
        if self.iteration_count <= self.wait_period:
            return
        
        # Collect current market data
        current_bid_liquidity = self.get_total_bid_liquidity()
        current_spread = self.get_current_spread()
        current_volume = self.get_current_volume()
        
        # Skip if we can't get the required data
        if current_spread is None or current_bid_liquidity == 0:
            return
        
        # Store historical data
        self.bid_liquidity_history.append(current_bid_liquidity)
        self.spread_history.append(current_spread)
        self.volume_history.append(current_volume)
        
        # Keep only the data we need for monitoring
        max_history_length = self.monitor_period * 2  # Keep extra for safety
        if len(self.bid_liquidity_history) > max_history_length:
            self.bid_liquidity_history = self.bid_liquidity_history[-max_history_length:]
            self.spread_history = self.spread_history[-max_history_length:]
            self.volume_history = self.volume_history[-max_history_length:]
        
        # Check for liquidity deterioration and exit if conditions are met
        if (self.position.size > 0 and  # We have a position
            len(self.bid_liquidity_history) >= self.monitor_period and  # We have enough data
            self.check_liquidity_deterioration()):  # Conditions are met
            
            print("LIQUIDITY DETERIORATION DETECTED - PARTIAL EXIT")
            self.print_strategy_data()
            
            # Close specified percentage of position
            self.position.close(self.exit_percentage)
            print(f"Closed {self.exit_percentage:.1%} of position")
            print("-" * 50)
        
        # Check for liquidity improvement and buy if conditions are met
        elif (self._broker._cash > 0 and  # We have cash available
              len(self.bid_liquidity_history) >= self.monitor_period and  # We have enough data
              self.check_liquidity_improvement()):  # Conditions are met
            
            print("LIQUIDITY IMPROVEMENT DETECTED - BUY SIGNAL")
            self.print_strategy_data()
            
            # Buy using fraction of equity instead of calculating exact shares
            self.buy(size=self.buy_percentage)
            print(f"Bought {self.buy_percentage:.1%} of current equity")
            print("-" * 50)