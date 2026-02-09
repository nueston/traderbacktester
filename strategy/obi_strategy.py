from engine.backtesting import Strategy
from strategy.lib.indicators import run_trailing_indicators, monitor_indicators, update_indicators_history, get_default_indicator_rules
from strategy.lib.effective_price import calculate_effective_price
from strategy.lib.math import linear_regression
from data.lib.plot import plot_timeseries
import pandas as pd
import numpy as np

from data.data_bento import DataBento
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import analysis function
from strategy.lib.analysis import print_indicators_history
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
            'price': [],
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
    
    def monitor_indicators_wrapper(self, monitor_frequency=30.0, trailing_duration=30.0):
        """Wrapper method for the standalone monitor_indicators function
        
        Args:
            monitor_frequency (float): How often to calculate indicators (in seconds)
            trailing_duration (float): Duration in seconds for trailing calculations
            
        Returns:
            dict: Current indicator values
        """
        current_time = self.data.index[-1]
        fallback_close_price = self.data.Close[-1] if hasattr(self.data, 'Close') and len(self.data.Close) > 0 else None
        
        current_indicators, self.last_monitor_time = monitor_indicators(
            data_df=self.data.df if hasattr(self.data, 'df') else None,
            current_index=self.iteration,
            current_time=current_time,
            last_monitor_time=self.last_monitor_time,
            indicator_rules=get_default_indicator_rules(),
            monitor_frequency=monitor_frequency,
            trailing_duration=trailing_duration,
            fallback_close_price=fallback_close_price
        )
        
        # Update indicators history if we got new indicators
        if current_indicators is not None:
            self.indicators_history = update_indicators_history(
                self.indicators_history, 
                current_indicators, 
                self.max_history_length
            )
        
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
        current_indicators = self.monitor_indicators_wrapper(monitor_frequency=30.0, trailing_duration=3.0)
            
        if current_indicators:

            # Volume surge detection
            high_volume_warning=False
            if current_indicators['volume'] > np.mean(self.indicators_history['volume']) * 3:
                high_volume_warning=True
            # High spread warning detection
            high_spread_warning=False
            high_cancelation_warning=False
            spread_change = linear_regression(self.indicators_history['spread'])
            cancelations_change = linear_regression(self.indicators_history['cancelations'])
            price_change = linear_regression(self.indicators_history['price'])
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

            if price_change > 0.07 or price_change < -0.07:
                print_indicators_history(self.data.index[-1], self.indicators_history)
            
            # # STOP LOSS CONDITIONS
            # elif self.position:
            #     stop_loss_triggered = False
                
            #     # Stop loss 1: Strong downtrend detected
            #     if obi_trend_class == "strong_downtrend" and high_volume_warning: #and high_spread_warning and high_cancelation_warning:
            #         stop_loss_triggered = True
            #         print("STOP LOSS: Strong OBI downtrend detected")
            #         # Print indicators history when strong downtrend is detected
            #         print_indicators_history(self.data.index[-1], self.indicators_history)
                
            #     if stop_loss_triggered:
            #         current_idx = min(self.iteration - 1, len(self.data_manager['ts_event_dt']) - 1)
            #         current_close = self.data.Close[current_idx]
            #         bid, ask = self.data_bento.get_current_bid_ask(self.data_manager, current_idx, self.iteration)
            #         reference_price = bid if bid is not None else current_close
            #         effective_price = calculate_effective_price('close', abs(self.position.size), current_idx, self.data_manager, self.data, self.data_bento, self.iteration)
            #         execution_spread = abs(reference_price - effective_price) / reference_price

            #         self.position.close(spread=execution_spread)
            #         print(f"EXECUTION DETAILS:")
            #         print(f"  Reference Buy Price: ${reference_price}")
            #         print(f"  Effective Buy Price: ${effective_price:.4f}")
            #         print(f"  Execution Spread: {(execution_spread*100):.4f}%")
            #         return
            
            # # BUY CONDITIONS
            # if not self.position:
            #     buy_signal = False
            #     buy_reason = ""
                
            #     # Buy condition 2: Strong uptrend with positive OBI
            #     if obi_trend_class == "strong_uptrend" and current_obi > 0.2 and high_volume_warning:
            #         buy_signal = True
            #         buy_reason = "Strong OBI uptrend"
            #         # Print indicators history when strong uptrend is detected
            #         print_indicators_history(self.data.index[-1], self.indicators_history)
                
            #     if buy_signal:
            #         # Calculate effective buy price for a standard order size (e.g., $10000 worth)
            #         current_idx = min(self.iteration - 1, len(self.data_manager['ts_event_dt']) - 1)
            #         current_close = self.data.Close[current_idx]
            #         estimated_shares = 10000 / current_close  # $10000 worth of shares
            #         effective_price = calculate_effective_price('buy', int(estimated_shares), current_idx, self.data_manager, self.data, self.data_bento, self.iteration)
                    
            #         # Use current ask price as reference for spread calculation
            #         bid, ask = self.data_bento.get_current_bid_ask(self.data_manager, current_idx, self.iteration)
            #         reference_price = ask if ask is not None else current_close
            #         execution_spread = abs(reference_price - effective_price) / reference_price
                    
            #         self.buy(spread=execution_spread)
            #         print(f"BUY SIGNAL: {buy_reason}")
                    
            #         print(f"EXECUTION DETAILS:")
            #         print(f"  Reference Ask Price: ${reference_price:.4f}")
            #         print(f"  Effective Buy Price: ${effective_price:.4f}")
            #         print(f"  Execution Spread: {(execution_spread*100):.4f}%")