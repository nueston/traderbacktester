from backtesting import Strategy
from data.data_ohlc_bento import DataOhlcBento


class LiquidityMonitorStrategy(Strategy):
    """
    Strategy that monitors market liquidity conditions and exits positions
    when liquidity deteriorates significantly
    """
    
    # Configurable parameters
    monitor_period = 20  # Number of iterations to monitor
    wait_period = 20     # Number of iterations to do nothing at start
    
    # Exit conditions (sell)
    bid_decrease_threshold = 0.6  # *100%
    spread_increase_threshold = 0.05  # 30% spread increase
    volume_increase_threshold = 5  # *100%
    exit_percentage = 0.40  # Close 40% of position
    
    # Entry conditions (buy)
    bid_increase_threshold = 4  # *100%
    spread_increase_buy_threshold = 0.30  # 30% spread increase for buy
    volume_increase_buy_threshold = 5  # 30% volume increase for buy
    buy_percentage = 0.40  # Buy amount as percentage of cash
    
    def init(self):
        # Buy at initialization
        self.buy()
        
        # Initialize DataOhlcBento manager
        self.data_manager = DataOhlcBento(self.data.df)
        
        # Initialize tracking arrays
        self.bid_liquidity_history = []
        self.spread_history = []
        self.volume_history = []
        self.iteration_count = 0
        
    def get_total_bid_liquidity(self):
        """Calculate total bid liquidity across all depth levels (0-9)"""
        return self.data_manager.get_total_bid_liquidity(level=10, iterations=1)
    
    def get_current_spread(self):
        """Get current bid-ask spread"""
        if hasattr(self.data, 'bento_spread'):
            return self.data.bento_spread[-1]
        return None
    
    def get_current_volume(self):
        """Get current volume"""
        return self.data_manager.get_volume(iteration=1)
    
    def check_liquidity_deterioration(self):
        """
        Check if liquidity has deteriorated significantly over the monitoring period
        Returns True if all conditions are met for position exit
        """
        if self.iteration_count < self.monitor_period:
            return False
        
        # Get liquidity trend using DataOhlcBento
        trend_data = self.data_manager.get_liquidity_trend(current_index=self.iteration_count-1, iterations=self.monitor_period)
        
        if not trend_data:
            return False
        
        # Extract trend percentages (negative values indicate decrease)
        bid_trend = trend_data['bid_trend']
        
        # Get spread and volume changes from recent history
        if len(self.spread_history) < self.monitor_period or len(self.volume_history) < self.monitor_period:
            return False
            
        recent_spreads = self.spread_history[-self.monitor_period:]
        recent_volumes = self.volume_history[-self.monitor_period:]
        
        spread_start = recent_spreads[0]
        spread_end = recent_spreads[-1]
        volume_start = recent_volumes[0]
        volume_end = recent_volumes[-1]
        
        # Avoid division by zero
        if spread_start == 0 or volume_start == 0:
            return False
        
        # Calculate percentage changes
        spread_change = ((spread_end - spread_start) / spread_start) * 100  # 
        volume_change = ((volume_end - volume_start) / volume_start) * 100  # 
        
        # Check all conditions (bid decrease, spread increase, volume increase)
        bid_condition = bid_trend <= -(self.bid_decrease_threshold * 100)  # 
        spread_condition = spread_change >= (self.spread_increase_threshold * 100)  # 
        volume_condition = volume_change >= (self.volume_increase_threshold * 100)  # 
        
        if bid_condition and volume_condition:
            print(f" bid : spread : volume : {bid_condition} : {spread_condition} : {volume_condition}")
        return bid_condition and spread_condition and volume_condition
    
    def check_liquidity_improvement(self):
        """
        Check if liquidity has improved significantly over the monitoring period
        Returns True if all conditions are met for position entry
        """
        if self.iteration_count < self.monitor_period:
            return False
        
        # Get liquidity trend using DataOhlcBento
        trend_data = self.data_manager.get_liquidity_trend(current_index=self.iteration_count-1, iterations=self.monitor_period)
        
        if not trend_data:
            return False
        
        # Extract trend percentages (positive values indicate increase)
        bid_trend = trend_data['bid_trend']
        
        # Get spread and volume changes from recent history
        if len(self.spread_history) < self.monitor_period or len(self.volume_history) < self.monitor_period:
            return False
            
        recent_spreads = self.spread_history[-self.monitor_period:]
        recent_volumes = self.volume_history[-self.monitor_period:]
        
        spread_start = recent_spreads[0]
        spread_end = recent_spreads[-1]
        volume_start = recent_volumes[0]
        volume_end = recent_volumes[-1]
        
        # Avoid division by zero
        if spread_start == 0 or volume_start == 0:
            return False
        
        # Calculate percentage changes
        spread_change = ((spread_end - spread_start) / spread_start) * 100  # Increase
        volume_change = ((volume_end - volume_start) / volume_start) * 100  # Increase
        
        # Check all conditions (bid increase, spread increase, volume increase)
        bid_condition = bid_trend >= (self.bid_increase_threshold * 100)  # 60% increase
        spread_condition = spread_change >= (self.spread_increase_buy_threshold * 100)  # 30% increase
        volume_condition = volume_change >= (self.volume_increase_buy_threshold * 100)  # 30% increase
        
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
        
        # Update data manager current index
        self.data_manager.set_current_index(self.iteration_count - 1)
        
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