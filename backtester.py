import pandas as pd
import numpy as np

class BacktestingFramework:

    def __init__(self, forex_trading, initial_balance, risk_strategy):
        self.forex_trading = forex_trading
        self.initial_balance = initial_balance
        self.set_risk_strategy(risk_strategy)

    def set_risk_strategy(self, risk_strategy):
        risk_mapping = {
            'safe': 0.01,
            'moderate': 0.1,
            'risky': 0.2,
            'extreme': None
        }

        self.risk_factor = risk_mapping[risk_strategy]
        self.is_extreme = risk_strategy == 'extreme'

    def run_backtest(self, strategy_func, data):
        trades = strategy_func(data)
        trades['long_entry'] = trades['long_entry'].astype(int)
        trades['long_exit'] = trades['long_exit'].astype(int)

        balance = self.initial_balance
        position_size = 0
        prev_position = 0
        won_trades = 0
        total_trades = 0

        for idx, row in trades.iterrows():
            if row['long_entry'] and not prev_position:
                position_size = balance * self.risk_factor if not self.is_extreme else min(balance, 1000)
                balance -= position_size
                prev_position = 1
                total_trades += 1

            if row['long_exit'] and prev_position:
                pnl = position_size * (row['close'] / trades.loc[trades.index[idx - 1], 'close'] - 1)
                balance += position_size + pnl
                position_size = 0
                prev_position = 0

                if pnl > 0:
                    won_trades += 1

                    if self.is_extreme:
                        self.risk_factor = min(self.risk_factor * 2, 1000)

        profit = balance - self.initial_balance
        win_ratio = won_trades / total_trades

        return {
            'won_trades': won_trades,
            'total_trades': total_trades,
            'win_ratio': win_ratio,
            'final_balance': balance,
            'profit': profit,
        }

    def backtest_strategies(self):
        backtest_results = {}

        for pair, strategy_func in self.forex_trading.strategies.items():
            data = self.forex_trading.market_stages[pair]['data']
            results = self.run_backtest(strategy_func, data)
            backtest_results[pair] = results

        return backtest_results