import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA, GOOG
from data.data_bento import DataBento
from strategy.strategy import BentoStrategy, LiquidityMonitorStrategy
import numpy as np
import pandas as pd

# Example usage:
if __name__ == "__main__":
    
    # For Bento MBP-10 data
    bento_file = "C:\\Users\\fy37bby\\user\\dev\misc\\backtest\\rsc\\XNAS-20260127-WTVN5DQMQ6\\xnas-itch-20260115.mbp-10_ONDS.csv"
    bento_loader = DataBento()
    data = bento_loader.load_bento_mbp10_data(bento_file, timeframe='1T')
    bt = Backtest(data, BentoStrategy, cash=10000, commission=.002, exclusive_orders=True, finalize_trades=True)
    
    # For legacy tick data
    #data = load_and_resample_csv("c:\\Users\\fy37bby\\user\\dev\\misc\\backtest\\rsc\\WDC_tickbidask.csv")
    #bt = Backtest(data, StrFull, cash=10000, commission=.002,
    #              exclusive_orders=True, finalize_trades=True, trade_on_close=True)

    stats = bt.run()
    bt.plot()