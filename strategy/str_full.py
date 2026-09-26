from backtesting import Strategy


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