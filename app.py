
import pandas as pd
from trading_ig import IGService
from trading_ig.config import config
import talib
from backtester import BacktestingFramework
from tenacity import Retrying, wait_exponential, retry_if_exception_type
from trading_ig.rest import ApiExceededException
import configparser

class ForexTrading:
    def __init__(self, username, password, api_key, acc_type, currency_pairs, resolution='H', test=True):
        """
        Initialize the ForexTrading class.

        Parameters:
        - username (str): The user's IG trading account username.
        - password (str): The user's IG trading account password.
        - api_key (str): The user's IG trading API key.
        - acc_type (str): The user's IG trading account type.
        - currency_pairs (list): The list of currency pairs to trade.
        - resolution (str): The resolution of historical data ('H' for hourly, 'D' for daily, etc.).
        - test (bool): If True, use backtesting. If False, use live trading.
        """
        self.username = username
        self.password = password
        self.api_key = api_key
        self.acc_type = acc_type
        self.currency_pairs = currency_pairs
        retryer = Retrying(wait=wait_exponential(),
                       retry=retry_if_exception_type(ApiExceededException))
    
        self.ig_service = IGService(username, password, api_key, acc_type,
                                retryer=retryer, use_rate_limiter=True)
    
        self.ig_service.create_session()
        self.resolution = resolution
        self.strategies = {}
        self.market_stages = {}

    def determine_market_stage(self):
        """
        Determine the market stage for each currency pair.

        Returns:
        - market_stages (dict): A dictionary containing the market stage, volatility, and historical data for each currency pair.
        """
        for pair in self.currency_pairs:
            # Fetch historical data for the currency pair
            # Calculate the market stage and volatility
            stage, volatility, data = self._calculate_market_stage(pair)
            self.market_stages[pair] = {
                'stage': stage,
                'volatility': volatility, 
                'data': data
            }

        return self.market_stages

    def _calculate_market_stage(self, currency_pair):
        """
        Calculate the market stage for a given currency pair.

        Parameters:
        - currency_pair (str): The currency pair to calculate the market stage for.

        Returns:
        - stage (str): The market stage ('Bull', 'Bear', or 'Consolidation').
        - volatility (float): The volatility of the currency pair.
        - data (DataFrame): The historical data for the currency pair.
        """
        # Fetch historical data for the currency pair
        data = self._fetch_historical_data(currency_pair, resolution=self.resolution)
        df = pd.DataFrame(data)

        # Calculate moving averages
        short_ma = df['close'].rolling(window=50).mean()
        long_ma = df['close'].rolling(window=200).mean()

        # Determine market stage
        if short_ma.iloc[-1] > long_ma.iloc[-1]:
            stage = 'Bull'
        elif short_ma.iloc[-1] < long_ma.iloc[-1]:
            stage = 'Bear'
        else:
            stage = 'Consolidation'

        # Calculate volatility (e.g., using Average True Range)
        volatility = self._calculate_volatility(df)

        return stage, volatility, data

    def _fetch_historical_data(self, currency_pair, resolution='D', num_points=200):
        """
        Fetch historical data for a given currency pair.

        Parameters:
        - currency_pair (str): The currency pair to fetch historical data for.
        - resolution (str): The resolution of historical data ('H' for hourly, 'D' for daily, etc.).
        - num_points (int): The number of data points to fetch.

        Returns:
        - data (DataFrame): The historical data for the currency pair.
        """
        request = self.ig_service.fetch_historical_prices_by_epic_and_num_points(
            currency_pair, resolution, num_points)
        data = request['prices']

        # Reset the index
        data.reset_index(inplace=True)

        # Calculate mid-price columns
        data['mid_open'] = (data[('bid', 'Open')] + data[('ask', 'Open')]) / 2
        data['mid_high'] = (data[('bid', 'High')] + data[('ask', 'High')]) / 2
        data['mid_low'] = (data[('bid', 'Low')] + data[('ask', 'Low')]) / 2
        data['mid_close'] = (data[('bid', 'Close')] + data[('ask', 'Close')]) / 2

         # Drop unwanted columns
        data.drop([('bid', 'Open'), ('bid', 'High'), ('bid', 'Low'), ('bid', 'Close'),
                ('ask', 'Open'), ('ask', 'High'), ('ask', 'Low'), ('ask', 'Close'),
                ('last', 'Open'), ('last', 'High'), ('last', 'Low'), ('last', 'Close')],
                axis=1, inplace=True)

        # Rename the columns
        data.columns = ['timestamp', 'volume', 'open', 'high', 'low', 'close']

        return data

    def _calculate_volatility(self, df, period=14, low_factor=0.5, high_factor=1.5):
        """
        Calculate the volatility for a given DataFrame.

        Parameters:
        - df (DataFrame): The DataFrame to calculate the volatility for.
        - period (int): The period for the Average True Range calculation.
        - low_factor (float): The multiplier for the low volatility threshold.
        - high_factor (float): The multiplier for the high volatility threshold.

        Returns:
        - atr (float): The volatility of the DataFrame (e.g., Average True Range).
        """
        # Calculate True Range
        df['previous_close'] = df['close'].shift(1)
        df['high_low'] = df['high'] - df['low']
        df['high_prev_close'] = abs(df['high'] - df['previous_close'])
        df['low_prev_close'] = abs(df['low'] - df['previous_close'])
        df['true_range'] = df[['high_low', 'high_prev_close', 'low_prev_close']].max(axis=1)

        # Calculate Average True Range (ATR)
        atr = df['true_range'].rolling(window=period).mean().iloc[-1]

        # Calculate volatility thresholds
        volatility_thresholds = {
            'low': atr * low_factor,
            'high': atr * high_factor
        }

        # Drop temporary columns
        df.drop(columns=['previous_close', 'high_low', 'high_prev_close', 'low_prev_close', 'true_range'], inplace=True)

        return atr

    def calculate_support_resistance(self, high, low, close, window=14):
        """
        Calculate support and resistance levels for a given DataFrame.

        Parameters:
        - high (Series): High prices data.
        - low (Series): Low prices data.
        - close (Series): Close prices data.
        - window (int): The window size for the rolling mean calculation.

        Returns:
        - support (Series): The support levels.
        - resistance (Series): The resistance levels.
        """
        # Calculate the pivot point
        pivot_point = (high + low + close) / 3

        # Calculate the trading range
        trading_range = high - low

        # Calculate support and resistance levels
        support = pivot_point - trading_range
        resistance = pivot_point + trading_range

        # Calculate the rolling mean of support and resistance levels
        support = support.rolling(window=window).mean()
        resistance = resistance.rolling(window=window).mean()

        return support, resistance

    def bull_strategy(self, volatility, data):
        """
        Implement the strategy for Bull market stage.

        Parameters:
        - volatility (float): The volatility of the currency pair.
        - data (DataFrame): The historical data for the currency pair.

        Returns:
        - data (DataFrame): The DataFrame with strategy calculations.
        """
        # Calculate indicators
        data['SMA'] = talib.SMA(data['close'], timeperiod=20)
        data['EMA'] = talib.EMA(data['close'], timeperiod=20)
        data['RSI'] = talib.RSI(data['close'], timeperiod=14)
        data['upper_bb'], data['middle_bb'], data['lower_bb'] = talib.BBANDS(data['close'], timeperiod=20)
        data['slowk'], data['slowd'] = talib.STOCH(data['high'], data['low'], data['close'], fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)

        # Calculate support and resistance levels
        data['support'], data['resistance'] = self.calculate_support_resistance(data['high'], data['low'], data['close'])

        # Define the strategy's entry and exit rules
        data['long_entry'] = (data['close'] > data['SMA']) & \
                                (data['close'] > data['EMA']) & \
                                (data['RSI'] < 30) & \
                                (data['close'] > data['lower_bb']) & \
                                (data['slowk'] < 20) & \
                                (data['slowd'] < 20)

        data['long_exit'] = (data['close'] < data['SMA']) | \
                                (data['close'] < data['EMA']) | \
                                (data['RSI'] > 70) | \
                                (data['close'] > data['upper_bb']) | \
                                (data['slowk'] > 80) & \
                                (data['slowd'] > 80) | \
                                (data['close'] > data['resistance'])

        return data

    def bear_strategy(self):
        """
        Implement your strategy for Bear market stage.
        """
        pass

    def consolidation_strategy(self):
        """
        Implement your strategy for Consolidation market stage.
        """
        pass

    def backtest_strategies(self):
        """
        Implement your backtesting logic for each strategy.
        """
        pass

    def place_trade(self, trade_type, currency_pair, size, stop_distance, limit_distance):
        """
        Place a trade with the IG API.

        Parameters:
        - trade_type (str): The trade type ('BUY' or 'SELL').
        - currency_pair (str): The currency pair to trade.
        - size (float): The trade size.
        - stop_distance (float): The stop distance.
        - limit_distance (float): The limit distance.

        Returns:
        - response (dict): The response from the IG API.
        """
        trade = {
            'direction': trade_type,
            'epic': currency_pair,
            'orderType': 'MARKET',
            'size': size,
            'expiry': 'DFB',
            'guaranteedStop': False,
            'forceOpen': True,
            'currencyCode': 'USD',
            'stopDistance': stop_distance,
            'limitDistance': limit_distance,
        }

        response = self.ig_service.create_open_position(trade)
        return response

    def calc_strategy(self, market_stages):
        """
        Calculate the strategy for each market stage.

        Parameters:
        - market_stages (dict): A dictionary containing the market stage, volatility, and historical data for each currency pair.

        Returns:
        - strategies (dict): A dictionary containing the strategy function for each currency pair.
        """
        for pair, package in market_stages.items():
            print(pair)
            stage = package['stage']
            print(stage)
            data = package['data']
            volatility = package['volatility']
            if stage == 'Consolidation':
                self.strategies[pair] = self.consolidation_strategy(pair, volatility)
            elif stage == 'Bull':
                self.strategies[pair] = self.bull_strategy(volatility, data)
            elif stage == 'Bear':
                self.strategies[pair] = self.bear_strategy(pair, volatility)
        return self.strategies

    def run(self):
        """
        Run the ForexTrading class.
        """
        market_stages = self.determine_market_stage()
        strategies = self.calc_strategy(market_stages)
        print(strategies)
        if test:

            initial_balance = 1
            risk_strategy = 'extreme'  # or 'safe', 'risky', 'extreme'

            backtester = BacktestingFramework(self, initial_balance, risk_strategy)
            backtest_results = backtester.backtest_strategies()
            print(backtest_results)
        else:

            #TODO: Maybe use event based, instead of a while loop?
            #TODO: Add stoploss and position sizing based on risk aversion
            #TODO: How to spread this accross multiple currencies concurrently?
            while True:
                for pair, strategy_func in strategies.items():
                    # Fetch real-time data
                    realtime_data = self.fetch_realtime_data(pair)
                    
                    # Evaluate trading signals and calculate confidence
                    signals, confidence = self.evaluate_trading_signals(realtime_data, strategy_func)
                    
                    # Place trades based on the trading signals and confidence
                    # Customize this logic based on your requirements
                    if signals['long_entry'].iloc[-1] and confidence >= your_confidence_threshold:
                        trade_response = self.place_trade("BUY", pair, size, stop_distance, limit_distance)
                    elif signals['long_exit'].iloc[-1] and confidence >= your_confidence_threshold:
                        trade_response = self.place_trade("SELL", pair, size, stop_distance, limit_distance)
                    
                    # Sleep for some time before the next iteration (customize the sleep duration)
                    time.sleep(60)


if __name__ == "__main__":

    #Read configuration from file
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Get credentials from configuration
    username = config.get('Credentials', 'username')
    password = config.get('Credentials', 'password')
    api_key = config.get('API', 'ig_key')

    acc_type = "DEMO"  # Use "LIVE" for a live account
    test = True
    currency_pairs = ["CS.D.EURUSD.MINI.IP", "CS.D.GBPUSD.MINI.IP"]

    trader = ForexTrading(username, password, api_key, acc_type, currency_pairs, test=test)
    trader.run()
