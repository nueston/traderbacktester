from engine.backtesting import Strategy
from strategy.lib.indicators import run_trailing_indicators
from strategy.lib.effective_price import calculate_effective_price
from strategy.lib.math import linear_regression
from data.lib.plot import plot_timeseries
import pandas as pd
import numpy as np

from data.data_bento import DataBento
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
class ObiStrategy(Strategy):
    """
    Strategy that utilizes Bento MBP-10 market data
    """
    def init(self):
        # Initialize DataOhlcBento manager
        self.data_manager = self.data.df
        self.iteration = 0
        
        # Initialize indicators history - maintains last 10 values for each indicator
        self.indicators_history = {
            'obi': [],
            'spread': [],
            'volume': [],
            'cancelations': [],
        }
        self.max_history_length = 10
        self.last_monitor_time = None
        
        # Price tracking for signal detection vs execution
        self.signal_detection_price = None
        self.last_execution_price = None
        
        self.position.close()
        
        # Initialize DataFrame to store iteration data for plotting
        self.iteration_data = pd.DataFrame(columns=['timestamp', 'obi_change'])
        
        # Initialize DataBento instance for market data methods
        self.data_bento = DataBento()
    
    def print_market_data(self):
        """Print current market data including Bento-specific information"""
        current_time = self.data.index[-1]
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        bid, ask = self.data_bento.get_current_bid_ask(self.data_manager, iteration=self.iteration)
        spread = self.data_bento.get_current_spread(self.data_manager, iteration=self.iteration)
        bid_size, ask_size = self.data_bento.get_market_depth(self.data_manager, 0, iteration=self.iteration)
        
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
            data_bento = DataBento()
            trailing_df = data_bento.get_trailing_ticks(df=self.data.df, current_index=self.iteration-1, trailing_duration=trailing_duration)
            
            indicator_rules = [
            {
                'name': 'obi',
                'type': 'obi',
                'depth': 10
            },
            {
                'name': 'volume',
                'type': 'volume',
            },
            {
                'name': 'cancelations',
                'type': 'cancelations',
                'action_column': 'action',
                'cancel_value': 'C'
            },
            {
                'name': 'spread',
                'type': 'spread',
                'bid_column': 'bid_px_00',
                'ask_column': 'ask_px_00'
            }
            ]
            results = run_trailing_indicators(trailing_df, indicator_rules)

            current_indicators['obi'] = results['obi']
            current_indicators['volume'] = results['volume']
            current_indicators['cancelations'] = results['cancelations']
            current_indicators['spread'] = results['spread']
            
            # Update OBI history
            self.indicators_history['obi'].append(results['obi'])
            if len(self.indicators_history['obi']) > self.max_history_length:
                self.indicators_history['obi'].pop(0)
            # Update volume history
            self.indicators_history['volume'].append(results['volume'])
            if len(self.indicators_history['volume']) > self.max_history_length:
                self.indicators_history['volume'].pop(0)
            # Update cancelations history
            self.indicators_history['cancelations'].append(results['cancelations'])
            if len(self.indicators_history['cancelations']) > self.max_history_length:
                self.indicators_history['cancelations'].pop(0)
            # Update cancelations history
            self.indicators_history['spread'].append(results['spread'])
            if len(self.indicators_history['spread']) > self.max_history_length:
                self.indicators_history['spread'].pop(0)
        
        return current_indicators
    
    def get_obi_trend_classification(self, obi_change):
        """Classify OBI trend into categories
        
        Args:
            obi_change (float): The OBI trend strength value from linear regression
            
        Returns:
            str: Trend classification category
        """
        if obi_change > 0.05:
            return "strong_uptrend"
        elif obi_change > 0.02:
            return "weak_uptrend"
        elif obi_change < -0.05:
            return "strong_downtrend"
        elif obi_change < -0.02:
            return "weak_downtrend"
        else:
            return "sideways"

    
    def plot_obi_change_history(self, granularity_seconds=30, save_path=None):
        """
        Plot the OBI change history over time with specified granularity
        
        Args:
            granularity_minutes (int): Granularity in seconds for sampling
            save_path (str): Optional path to save the plot
        
        Returns:
            matplotlib.figure.Figure: The created figure
        """
        if len(self.iteration_data) == 0:
            print("No iteration data available for plotting")
            return None
        
        # Create the plot
        fig = plot_timeseries(
            df=self.iteration_data,
            x_col='timestamp',
            y_col='obi_change',
            granularity_seconds=granularity_seconds,
            title="OBI Change Over Time",
            xlabel="Time",
            ylabel="OBI Change (Trend Strength)",
            figsize=(15, 8)
        )
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
            
        return fig

    def next(self):
        # Skip first few bars for indicator warmup
        if len(self.data.Close) < 21:
            return
        
        # Update data manager current index
        # TODO self.data_manager.set_current_index(self.iteration)
        self.iteration += 1
        
        # Monitor indicators every second with 1-second trailing duration
        current_indicators = self.monitor_indicators(monitor_frequency=3.0, trailing_duration=3.0)
            
        if current_indicators:
            spread = self.data_bento.get_current_spread(self.data_manager, iteration=self.iteration)
            # Volume surge detection
            high_volume_warning=False
            if current_indicators['volume'] > np.mean(self.indicators_history['volume']) * 3:
                high_volume_warning=True
            # High spread warning detection
            high_spread_warning=False
            high_cancelation_warning=False
            spread_change = linear_regression(self.indicators_history['spread'])
            cancelations_change = linear_regression(self.indicators_history['cancelations'])
            if spread_change > 0.2 :
                high_spread_warning=True
            if cancelations_change > 0.2:
                high_cancelation_warning=True
            # obi class detection
            current_obi = current_indicators.get('obi', 0)
            obi_change = linear_regression(self.indicators_history['obi'])
            obi_trend_class = self.get_obi_trend_classification(obi_change)
            
            # Store iteration data for plotting
            new_row = pd.DataFrame({
                'timestamp': [self.data.index[-1]], 
                'obi_change': [obi_change]
            })
            self.iteration_data = pd.concat([self.iteration_data, new_row], ignore_index=True)

            
            # STOP LOSS CONDITIONS
            if self.position:
                stop_loss_triggered = False
                
                # Stop loss 1: Strong downtrend detected
                if obi_trend_class == "strong_downtrend" and high_volume_warning: #and high_spread_warning and high_cancelation_warning:
                    stop_loss_triggered = True
                    print("STOP LOSS: Strong OBI downtrend detected")
                
                if stop_loss_triggered:
                    current_idx = min(self.iteration - 1, len(self.data_manager['ts_event_dt']) - 1)
                    current_close = self.data.Close[current_idx]
                    bid, ask = self.data_bento.get_current_bid_ask(self.data_manager, current_idx, self.iteration)
                    reference_price = bid if bid is not None else current_close
                    effective_price = calculate_effective_price('close', abs(self.position.size), current_idx, self.data_manager, self.data, self.data_bento, self.iteration)
                    execution_spread = abs(reference_price - effective_price) / reference_price

                    self.position.close(spread=execution_spread)
                    print(f"EXECUTION DETAILS:")
                    print(f"  Reference Buy Price: ${reference_price}")
                    print(f"  Effective Buy Price: ${effective_price:.4f}")
                    print(f"  Execution Spread: {(execution_spread*100):.4f}%")
                    return
            
            # BUY CONDITIONS
            if not self.position:
                buy_signal = False
                buy_reason = ""
                
                # Buy condition 2: Strong uptrend with positive OBI
                if obi_trend_class == "strong_uptrend" and current_obi > 0.2 and high_volume_warning:
                    buy_signal = True
                    buy_reason = "Strong OBI uptrend"
                
                if buy_signal:
                    # Calculate effective buy price for a standard order size (e.g., $10000 worth)
                    current_idx = min(self.iteration - 1, len(self.data_manager['ts_event_dt']) - 1)
                    current_close = self.data.Close[current_idx]
                    estimated_shares = 10000 / current_close  # $10000 worth of shares
                    effective_price = calculate_effective_price('buy', int(estimated_shares), current_idx, self.data_manager, self.data, self.data_bento, self.iteration)
                    
                    # Use current ask price as reference for spread calculation
                    bid, ask = self.data_bento.get_current_bid_ask(self.data_manager, current_idx, self.iteration)
                    reference_price = ask if ask is not None else current_close
                    execution_spread = abs(reference_price - effective_price) / reference_price
                    
                    self.buy(spread=execution_spread)
                    print(f"BUY SIGNAL: {buy_reason}")
                    
                    print(f"EXECUTION DETAILS:")
                    print(f"  Reference Ask Price: ${reference_price:.4f}")
                    print(f"  Effective Buy Price: ${effective_price:.4f}")
                    print(f"  Execution Spread: {(execution_spread*100):.4f}%")