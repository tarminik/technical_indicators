import random

import pandas as pd
import plotly.graph_objects as go
from binance.client import Client
from plotly.subplots import make_subplots
from tabulate import tabulate
import sys
from indicators import ta, sep_window_ind


def random_color():
    return f'#{random.randint(0, 0xFFFFFF):06x}'


def calc_wind_num(indicators):
    wind_num = 1
    for indicator in indicators:
        if indicator[0] in sep_window_ind:
            wind_num += 1
    return wind_num


def calc_row_heights(wind_num):
    row_heights = [3]
    for i in range(wind_num - 1):
        row_heights.append(1)
    return row_heights


def calc_specs(wind_num):
    specs = [[{"secondary_y": True}]]
    for i in range(wind_num - 1):
        specs.append([{"secondary_y": False}])
    return specs


class Data:
    def __init__(self, pair='DOGEUSDT', timeframe=Client.KLINE_INTERVAL_1DAY, start_date="1 Jan, 1900", end_date='now',
                 indicators=[]):
        """
        :param pair: str like 'DOGEUSDT', default -- DOGEUSDT
        :param timeframe: Client.KLINE_INTERVAL like Client.KLINE_INTERVAL_1DAY, default -- 1 day
        :param start_date: str like "1 Jan, 2000", default -- moment of listing of the chosen trading pair
        :param end_date: str like "1 Jan, 2000", default -- present
        """
        self.pair = pair
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.used_rows = 1
        try:
            self.client = Client('_', '_')
        except:
            print("\nCan not get data. Check your network connection.")
            sys.exit()

        wind_num = calc_wind_num(indicators)
        self.fig = make_subplots(rows=wind_num, cols=1, row_heights=calc_row_heights(wind_num),
                                 specs=calc_specs(wind_num))

        klines = self.client.get_historical_klines(symbol=self.pair,
                                                   interval=self.timeframe,
                                                   start_str=self.start_date,
                                                   end_str=self.end_date)

        self.ohlcv = pd.DataFrame(klines,
                                  columns=['time', 'open', 'high', 'low', 'close', 'volume',
                                           'close_time', 'quote_asset_volume', 'number_of_trades',
                                           'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                                           'ignore']).drop(
            columns=['close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
                     'taker_buy_quote_asset_volume', 'ignore'])

        # convert the timestamp column to datetime format
        self.ohlcv['time'] = pd.to_datetime(self.ohlcv['time'], unit='ms')
        cols = ['open', 'high', 'low', 'close', 'volume']
        self.ohlcv[cols] = self.ohlcv[cols].apply(pd.to_numeric, errors='coerce', axis=1)

        self.fig.add_trace(go.Candlestick(x=self.ohlcv['time'],
                                          open=self.ohlcv['open'],
                                          high=self.ohlcv['high'],
                                          low=self.ohlcv['low'],
                                          close=self.ohlcv['close'],
                                          name='price'),
                           row=1, col=1, secondary_y=True)
        print(indicators)
        for indicator in indicators:
            self.add_indicator(indicator)

    def add_indicator(self, info):
        # Simple Moving Average 'SMA'
        if info[0] == 'sma':
            period = info[1]
            self.ohlcv[f'sma_{period}'] = ta.SMA(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'sma_{period}'],
                                          name=f'SMA {period}',
                                          line=dict(width=2)), row=1, col=1, secondary_y=True)
        # Simple Moving Median 'SMM'
        elif info[0] == 'smm':
            period = info[1]
            self.ohlcv[f'smm_{period}'] = ta.SMM(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'smm_{period}'],
                                          name=f'EMA {period}',
                                          line=dict(width=2)), row=1, col=1, secondary_y=True)
        # Smoothed Simple Moving Average 'SSMA'
        elif info[0] == 'ssma':
            period = info[1]
            self.ohlcv[f'ssma_{period}'] = ta.SSMA(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'ssma_{period}'],
                                          name=f'SSMA {period}',
                                          line=dict(width=2)), row=1, col=1, secondary_y=True)
        # Exponential Moving Average 'EMA'
        elif info[0] == 'ema':
            period = info[1]
            self.ohlcv[f'ema_{period}'] = ta.EMA(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'ema_{period}'],
                                          name=f'EMA {period}',
                                          line=dict(width=2)), row=1, col=1, secondary_y=True)
        # Double Exponential Moving Average 'DEMA'
        elif info[0] == 'dema':
            period = info[1]
            self.ohlcv[f'dema_{period}'] = ta.DEMA(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'dema_{period}'],
                                          name=f'DEMA {period}',
                                          line=dict(width=2)), row=1, col=1, secondary_y=True)
        # Triple Exponential Moving Average 'TEMA'
        elif info[0] == 'tema':
            period = info[1]
            self.ohlcv[f'tema_{period}'] = ta.TEMA(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'tema_{period}'],
                                          name=f'TEMA {period}',
                                          line=dict(width=2)), row=1, col=1, secondary_y=True)
        # Triangular Moving Average 'TRIMA'
        elif info[0] == 'trima':
            period = info[1]
            self.ohlcv[f'trima_{period}'] = ta.TRIMA(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'trima_{period}'],
                                          name=f'TRIMA {period}',
                                          line=dict(width=2)), row=1, col=1, secondary_y=True)
        elif info[0] == 'vama':
            period = info[1]
            self.ohlcv[f'vama_{period}'] = ta.VAMA(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'vama_{period}'],
                                          name=f'VAMA {period}',
                                          line=dict(width=2)), row=1, col=1, secondary_y=True)
        elif info[0] == 'wma':
            period = info[1]
            self.ohlcv[f'wma_{period}'] = ta.WMA(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'wma_{period}'],
                                          name=f'WMA {period}',
                                          line=dict(width=2)), row=1, col=1, secondary_y=True)
        elif info[0] == 'smma':
            period = info[1]
            self.ohlcv[f'smma_{period}'] = ta.SMMA(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'smma_{period}'],
                                          name=f'SMMA {period}',
                                          line=dict(width=2)),
                               row=1, col=1, secondary_y=True)
        elif info[0] == 'bbands':
            period = info[1]
            self.ohlcv[f'upper_bb_{period}'], self.ohlcv[f'middle_bb_{period}'], self.ohlcv[f'lower_bb_{period}'] = \
                ta.BBANDS(self.ohlcv, period)
            color = random_color()
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'upper_bb_{period}'],
                                          name=f'Upper BB {period}',
                                          line=dict(width=2, color=color)),
                               row=1, col=1, secondary_y=True)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'middle_bb_{period}'],
                                          name=f'Middle BB {period}',
                                          line=dict(width=2, color=color)),
                               row=1, col=1, secondary_y=True)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'lower_bb_{period}'],
                                          name=f'Lower BB {period}',
                                          line=dict(width=2, color=color)),
                               row=1, col=1, secondary_y=True)

        elif info[0] == 'macd':
            fast = info[1]
            slow = info[2]
            self.ohlcv[f'macd_{fast}_{slow}'], self.ohlcv[f'macd_signal_{fast}_{slow}'], \
                self.ohlcv[f'macd_difference_{fast}_{slow}'] = ta.MACD(self.ohlcv, period_fast=fast, period_slow=slow)

            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'macd_{fast}_{slow}'],
                                          name=f'MACD {fast} {slow}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'macd_signal_{fast}_{slow}'],
                                          name=f'MACD Signal {fast} {slow}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'macd_difference_{fast}_{slow}'],
                                          name=f'MACD Difference {fast} {slow}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.used_rows += 1

        elif info[0] == 'mom':
            period = info[1]
            self.ohlcv[f'mom_{period}'] = ta.MOM(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'mom_{period}'],
                                          name=f'MOM {period}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.used_rows += 1

        elif info[0] == 'roc':
            period = info[1]
            self.ohlcv[f'roc_{period}'] = ta.ROC(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'roc_{period}'],
                                          name=f'ROC {period}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.used_rows += 1

        elif info[0] == 'rsi':
            period = info[1]
            self.ohlcv[f'rsi_{period}'] = ta.RSI(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'rsi_{period}'],
                                          name=f'RSI {period}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.used_rows += 1

        elif info[0] == 'tr':
            period = info[1]
            self.ohlcv[f'tr_{period}'] = ta.TR(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'tr_{period}'],
                                          name=f'TR {period}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.used_rows += 1

        elif info[0] == 'atr':
            period = info[1]
            self.ohlcv[f'atr_{period}'] = ta.ATR(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'atr_{period}'],
                                          name=f'ATR {period}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.used_rows += 1

        # Volume
        elif info[0] == 'volume':
            self.fig.add_trace(go.Bar(x=self.ohlcv['time'], y=self.ohlcv['volume'],
                                      name='volume', marker=dict(color='grey')),
                               row=1, col=1, secondary_y=False)

        elif info[0] == 'KC':
            period = info[1]
            self.ohlcv[f'kc_up_{period}'], self.ohlcv[f'kc_down_{period}'] = ta.KC(self.ohlcv, period)
            color = random_color()
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'kc_up_{period}'],
                                          name=f'Upper KC {period}',
                                          line=dict(width=2, color=color)),
                               row=1, col=1, secondary_y=True)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'kc_down_{period}'],
                                          name=f'Lower KC {period}',
                                          line=dict(width=2, color=color)),
                               row=1, col=1, secondary_y=True)

        elif info[0] == 'stoch':
            period = info[1]
            self.ohlcv[f'stoch_{period}'] = ta.STOCH(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'stoch_{period}'],
                                          name=f'STOCH {period}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.used_rows += 1

        elif info[0] == 'williams':
            period = info[1]
            self.ohlcv[f'williams_{period}'] = ta.WILLIAMS(self.ohlcv, period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'williams_{period}'],
                                          name=f'Williams %R {period}',
                                          line=dict(width=2)),
                               row=self.used_rows + 1, col=1)
            self.used_rows += 1
        else:
            print("This indicator is not available yet")

    def beauty_print_data(self):
        print(tabulate(self.ohlcv, headers='keys', tablefmt='psql'))
        print(self.ohlcv.shape)

    def print_data(self):
        print(self.ohlcv)

    def show_chart(self):
        self.fig.update_layout(title=f'{self.pair} {self.timeframe}')
        self.fig.update_layout(xaxis_rangeslider_visible=False)
        self.fig.show()
