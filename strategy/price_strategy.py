from engine.backtesting import Strategy
from strategy.lib.indicators import run_trailing_indicators
from strategy.lib.math import linear_regression
from strategy.lib.analysis import print_indicators_history
from data.data_bento import DataBento
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from plot.plot import Plot

class PriceStrategy(Strategy):
    """
    Strategy that monitors price changes and prints indicator history
    when significant price movements are detected.
    """

    def init(self):
        self.data_manager = self.data.df
        self.iteration = 0

        self.indicators_history = {
            'price': [],
            'obi': [],
            'spread': [],
            'volume': [],
            'cancelations': [],
        }
        self.max_history_length = 10
        self.last_monitor_time = None

        self.data_bento = DataBento()

        # DataFrame to collect data for plotting
        self.plot_data = pd.DataFrame(columns=['time', 'price', 'obi', 'cancelations', 'volume'])

    def monitor_indicators(self, monitor_frequency=30.0, trailing_duration=30.0):
        """
        Monitor and update indicators history.

        Args:
            monitor_frequency (float): How often to calculate indicators (in seconds).
            trailing_duration (float): Duration in seconds for trailing calculations.

        Returns:
            dict or None: Current indicator values, or None if not yet time to monitor.
        """
        current_time = self.data.index[-1]

        if self.last_monitor_time is not None:
            time_diff = (current_time - self.last_monitor_time).total_seconds()
            if time_diff < monitor_frequency:
                return None

        self.last_monitor_time = current_time
        current_indicators = {}

        if hasattr(self.data, 'df'):
            data_bento = DataBento()
            trailing_df = data_bento.get_trailing_ticks(
                df=self.data.df,
                current_index=self.iteration - 1,
                trailing_duration=trailing_duration,
            )

            indicator_rules = [
                {'name': 'price', 'type': 'price'},
                {'name': 'obi', 'type': 'obi', 'depth': 10},
                {'name': 'volume', 'type': 'volume'},
                {'name': 'cancelations', 'type': 'cancelations', 'action_column': 'action', 'cancel_value': 'C'},
                {'name': 'spread', 'type': 'spread', 'bid_column': 'bid_px_00', 'ask_column': 'ask_px_00'},
            ]
            results = run_trailing_indicators(trailing_df, indicator_rules)

            for name in self.indicators_history:
                current_indicators[name] = results[name]
                self.indicators_history[name].append(results[name])
                if len(self.indicators_history[name]) > self.max_history_length:
                    self.indicators_history[name].pop(0)

        return current_indicators

    def next(self):
        if len(self.data.Close) < 21:
            return

        self.iteration += 1

        current_indicators = self.monitor_indicators(monitor_frequency=3.0, trailing_duration=3.0)

        if current_indicators:
            # Append current values to plot DataFrame
            new_row = pd.DataFrame([{
                'time': self.data.index[-1],
                'price': current_indicators['price'],
                'obi': current_indicators['obi'],
                'cancelations': current_indicators['cancelations'],
                'volume': current_indicators['volume'],
            }])
            self.plot_data = pd.concat([self.plot_data, new_row], ignore_index=True)

            price_change = linear_regression(self.indicators_history['price'])

            if price_change > 0.02 or price_change < -0.02:
                print_indicators_history(self.data.index[-1], price_change, self.indicators_history)

    def plot_results(self):
        """
        Plot collected indicator data: price & obi as lines, volume as bars.
        """
        if self.plot_data.empty:
            print("No data to plot.")
            return

        self.plot_data['time'] = pd.to_datetime(self.plot_data['time'])
        p = Plot(self.plot_data)
        p.show(
            x='time',
            y_lines=['price', 'obi'],
            bar_column='volume',
            title='Price & OBI with Volume',
        )
