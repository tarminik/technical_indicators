import pandas as pd
import plotly.graph_objects as go
from binance.client import Client
from finta import TA
from plotly.subplots import make_subplots
from tabulate import tabulate

from api_key import KEY, SECRET


class Data:
    def __init__(self, pair='DOGEUSDT', timeframe=Client.KLINE_INTERVAL_1DAY, start_date="1 Jan, 1900", end_date='now'):
        """
        :param pair: str like 'DOGEUSDT', default -- DOGEUSDT
        :param timeframe: Client.KLINE_INTERVAL like Client.KLINE_INTERVAL_1DAY, default -- 1 day
        :param start_date: str like "1 Jan, 2000", default -- moment of listing of the chosen trading pair
        :param end_date: str like "1 Jan, 2000", default -- present
        """
        self.df = None
        self.pair = pair
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.client = Client(KEY, SECRET)
        self.fig = make_subplots(rows=2, cols=1, row_heights=[5, 1],
                                 specs=[[{"secondary_y": True}], [{"secondary_y": False}]])

        klines = self.client.get_historical_klines(symbol=self.pair,
                                                   interval=self.timeframe,
                                                   start_str=self.start_date,
                                                   end_str=self.end_date)

        self.df = pd.DataFrame(klines,
                               columns=['time', 'open', 'high', 'low', 'close', 'volume',
                                        'close_time', 'quote_asset_volume', 'number_of_trades',
                                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']).drop(
            columns=['close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
                     'taker_buy_quote_asset_volume', 'ignore'])
        # convert the timestamp column to datetime format
        self.df['time'] = pd.to_datetime(self.df['time'], unit='ms')
        cols = ['open', 'high', 'low', 'close', 'volume']
        self.df[cols] = self.df[cols].apply(pd.to_numeric, errors='coerce', axis=1)

        self.fig.add_trace(go.Candlestick(x=self.df['time'],
                                          open=self.df['open'],
                                          high=self.df['high'],
                                          low=self.df['low'],
                                          close=self.df['close'],
                                          name='price'),
                           row=1, col=1, secondary_y=True)

    def add_indicator(self, name):
        # Simple Moving Average 'SMA'
        if name.lower() == 'sma':
            sma_period = int(input('Input SMA period: '))
            self.df[f'sma_{sma_period}'] = TA.SMA(self.df, sma_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'sma_{sma_period}'],
                                          name=f'SMA {sma_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Simple Moving Median 'SMM'
        elif name.lower() == 'smm':
            smm_period = int(input('Input SMM period: '))
            self.df[f'smm_{smm_period}'] = TA.SMM(self.df, smm_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'smm_{smm_period}'],
                                          name=f'EMA {smm_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Smoothed Simple Moving Average 'SSMA'
        elif name.lower() == 'ssma':
            ssma_period = int(input('Input SSMA period: '))
            self.df[f'ssma_{ssma_period}'] = TA.SSMA(self.df, ssma_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'ssma_{ssma_period}'],
                                          name=f'SSMA {ssma_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Exponential Moving Average 'EMA'
        elif name.lower() == 'ema':
            ema_period = int(input('Input EMA period: '))
            self.df[f'ema_{ema_period}'] = TA.EMA(self.df, ema_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'ema_{ema_period}'],
                                          name=f'EMA {ema_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Double Exponential Moving Average 'DEMA'
        elif name.lower() == 'dema':
            dema_period = int(input('Input DEMA period: '))
            self.df[f'dema_{dema_period}'] = TA.DEMA(self.df, dema_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'dema_{dema_period}'],
                                          name=f'DEMA {dema_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Triple Exponential Moving Average 'TEMA'
        elif name.lower() == 'tema':
            tema_period = int(input('Input TEMA period: '))
            self.df[f'tema_{tema_period}'] = TA.TEMA(self.df, tema_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'tema_{tema_period}'],
                                          name=f'TEMA {tema_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Triangular Moving Average 'TRIMA'
        elif name.lower() == 'trima':
            trima_period = int(input('Input TRIMA period: '))
            self.df[f'trima_{trima_period}'] = TA.TRIMA(self.df, trima_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'trima_{trima_period}'],
                                          name=f'TRIMA {trima_period}',
                                          line=dict(width=2)), secondary_y=True)
        # Volume
        elif name.lower() == 'volume':
            self.fig.add_trace(go.Bar(x=self.df['time'], y=self.df['volume'],
                                      name='volume', marker=dict(color='#1E1E1E')),
                               row=1, col=1, secondary_y=False)
        # Awesome Oscillator 'AO'
        elif name.lower() == 'ao':
            self.df['ao'] = TA.AO(self.df)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df['ao'],
                                          name='Awesome Oscillator',
                                          line=dict(width=2)),
                               row=2, col=1)

        else:
            print("This indicator is not available yet")

    def beauty_print_data(self):
        print(tabulate(self.df, headers='keys', tablefmt='psql'))
        print(self.df.shape)

    def print_data(self):
        print(self.df)

    def show_chart(self):
        self.fig.update_layout(title=f'{self.pair} {self.timeframe}')
        self.fig.update_layout(xaxis_rangeslider_visible=False)
        self.fig.show()
