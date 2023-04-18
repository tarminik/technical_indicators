import pandas as pd
import plotly.graph_objects as go
from binance.client import Client
from indicators import ta
from plotly.subplots import make_subplots
from tabulate import tabulate
import random

from api_key import KEY, SECRET


def random_color():
    return [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]


class Data:
    def __init__(self, pair='DOGEUSDT', timeframe=Client.KLINE_INTERVAL_1DAY, start_date="1 Jan, 1900", end_date='now'):
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
        try:
            self.client = Client(KEY, SECRET)
        except:
            raise ConnectionError

        self.fig = make_subplots(rows=2, cols=1, row_heights=[5, 1],
                                 specs=[[{"secondary_y": True}], [{"secondary_y": False}]])

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
                                          name='price',
                                          increasing_line_color='green',
                                          decreasing_line_color='red'),
                           row=1, col=1, secondary_y=True)

    def add_indicator(self, name):
        # Simple Moving Average 'SMA'
        if name.lower() == 'sma':
            sma_period = int(input('Input SMA period: '))
            self.ohlcv[f'sma_{sma_period}'] = ta.SMA(self.ohlcv, sma_period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'sma_{sma_period}'],
                                          name=f'SMA {sma_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Simple Moving Median 'SMM'
        elif name.lower() == 'smm':
            smm_period = int(input('Input SMM period: '))
            self.ohlcv[f'smm_{smm_period}'] = ta.SMM(self.ohlcv, smm_period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'smm_{smm_period}'],
                                          name=f'EMA {smm_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Smoothed Simple Moving Average 'SSMA'
        elif name.lower() == 'ssma':
            ssma_period = int(input('Input SSMA period: '))
            self.ohlcv[f'ssma_{ssma_period}'] = ta.SSMA(self.ohlcv, ssma_period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'ssma_{ssma_period}'],
                                          name=f'SSMA {ssma_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Exponential Moving Average 'EMA'
        elif name.lower() == 'ema':
            ema_period = int(input('Input EMA period: '))
            self.ohlcv[f'ema_{ema_period}'] = ta.EMA(self.ohlcv, ema_period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'ema_{ema_period}'],
                                          name=f'EMA {ema_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Double Exponential Moving Average 'DEMA'
        elif name.lower() == 'dema':
            dema_period = int(input('Input DEMA period: '))
            self.ohlcv[f'dema_{dema_period}'] = ta.DEMA(self.ohlcv, dema_period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'dema_{dema_period}'],
                                          name=f'DEMA {dema_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Triple Exponential Moving Average 'TEMA'
        elif name.lower() == 'tema':
            tema_period = int(input('Input TEMA period: '))
            self.ohlcv[f'tema_{tema_period}'] = ta.TEMA(self.ohlcv, tema_period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'tema_{tema_period}'],
                                          name=f'TEMA {tema_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Triangular Moving Average 'TRIMA'
        elif name.lower() == 'trima':
            trima_period = int(input('Input TRIMA period: '))
            self.ohlcv[f'trima_{trima_period}'] = ta.TRIMA(self.ohlcv, trima_period)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv[f'trima_{trima_period}'],
                                          name=f'TRIMA {trima_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Volume
        elif name.lower() == 'volume':
            self.fig.add_trace(go.Bar(x=self.ohlcv['time'], y=self.ohlcv['volume'],
                                      name='volume', marker=dict(color='#1E1E1E')),
                               row=1, col=1, secondary_y=False)
        else:
            print("This indicator is not available yet")
        # Awesome Oscillator 'AO'
        '''
        elif name.lower() == 'ao':
            self.ohlcv['ao'] = ta.AO(self.ohlcv)
            self.fig.add_trace(go.Scatter(x=self.ohlcv['time'], y=self.ohlcv['ao'],
                                          name='Awesome Oscillator',
                                          line=dict(width=2)),
                               row=2, col=1)
        '''

    def beauty_print_data(self):
        print(tabulate(self.ohlcv, headers='keys', tablefmt='psql'))
        print(self.ohlcv.shape)

    def print_data(self):
        print(self.ohlcv)

    def chart(self):
        self.fig.update_layout(title=f'{self.pair} {self.timeframe}')
        self.fig.update_layout(xaxis_rangeslider_visible=False)
        self.fig.show()
