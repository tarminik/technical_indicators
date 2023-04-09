import datetime

import pandas as pd
import plotly.graph_objects as go
from binance.client import Client
from finta import TA
from tabulate import tabulate

from api_key import KEY, SECRET


def process_tf(tf):
    if tf in ['1m', '1 m'] or tf.lower() in ['1min', '1 min', '1minute', '1 minute']:
        return Client.KLINE_INTERVAL_1MINUTE
    elif tf in ['3m', '3 m'] or tf.lower() in ['3min', '3 min', '3minute', '3 minute']:
        return Client.KLINE_INTERVAL_3MINUTE
    elif tf in ['5m', '5 m'] or tf.lower() in ['5min', '5 min', '5minute', '5 minute']:
        return Client.KLINE_INTERVAL_5MINUTE
    elif tf in ['15m', '15 m'] or tf.lower() in ['15min', '15 min', '15minute', '15 minute']:
        return Client.KLINE_INTERVAL_15MINUTE
    elif tf in ['30m', '30 m'] or tf.lower() in ['30min', '30 min', '30minute', '30 minute']:
        return Client.KLINE_INTERVAL_30MINUTE
    elif tf.lower() in ['1h', '1 h', '1hour', '1 hour']:
        return Client.KLINE_INTERVAL_1HOUR
    elif tf.lower() in ['2h', '2 h', '2hour', '2 hour']:
        return Client.KLINE_INTERVAL_2HOUR
    elif tf.lower() in ['4h', '4 h', '4hour', '4 hour']:
        return Client.KLINE_INTERVAL_4HOUR
    elif tf.lower() in ['6h', '6 h', '6hour', '6 hour']:
        return Client.KLINE_INTERVAL_6HOUR
    elif tf.lower() in ['8h', '8 h', '8hour', '8 hour']:
        return Client.KLINE_INTERVAL_8HOUR
    elif tf.lower() in ['12h', '12 h', '12hour', '12 hour']:
        return Client.KLINE_INTERVAL_12HOUR
    elif tf.lower() in ['1d', '1 d', '1day', '1 day']:
        return Client.KLINE_INTERVAL_1DAY
    elif tf.lower() in ['3d', '3 d', '3day', '3 day']:
        return Client.KLINE_INTERVAL_3DAY
    elif tf.lower() in ['1w', '1 w', '1week', '1 week']:
        return Client.KLINE_INTERVAL_1WEEK
    elif tf in ['1M', '1 M'] or tf.lower() in ['1month', '1 month']:
        return Client.KLINE_INTERVAL_1MONTH


class Data:
    def __init__(self, pair='DOGEUSDT', timeframe=Client.KLINE_INTERVAL_1DAY, start_date="1 Jan, 1900",
                 end_date=str(datetime.date.today() + datetime.timedelta(days=1))):
        """
        :param pair: str like 'BTCUSDT', default -- DOGEUSDT
        :param timeframe: Client.KLINE_INTERVAL like Client.KLINE_INTERVAL_1DAY, default -- 1 day
        :param start_date: str like "1 Jan, 2000", default -- moment of listing of the chosen trading pair
        :param end_date: str like "1 Jan, 2000", default -- present
        """
        self.df = None
        self._pair = pair
        self._timeframe = timeframe
        self._start_date = start_date
        self._end_date = end_date
        self.client = Client(KEY, SECRET)
        self.fig = None

        klines = self.client.get_historical_klines(symbol=self._pair,
                                                   interval=self._timeframe,
                                                   start_str=self._start_date,
                                                   end_str=self._end_date)

        self.df = pd.DataFrame(klines,
                               columns=['time', 'open', 'high', 'low', 'close', 'volume',
                                        'close_time', 'quote_asset_volume', 'number_of_trades',
                                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']).drop(
            columns=['close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
                     'taker_buy_quote_asset_volume', 'ignore'])
        # convert the timestamp column to datetime format
        self.df['time'] = pd.to_datetime(self.df['time'], unit='ms')

        self.fig = go.Figure(data=[go.Candlestick(x=self.df['time'],
                                                  open=self.df['open'],
                                                  high=self.df['high'],
                                                  low=self.df['low'],
                                                  close=self.df['close'],
                                                  name='price')])

    def add_indicator(self, name):
        # Simple Moving Average 'SMA'
        if name.lower() == 'sma':
            sma_period = int(input('Input SMA period: '))
            self.df[f'sma_{sma_period}'] = TA.SMA(self.df, sma_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'sma_{sma_period}'],
                                          name=f'SMA {sma_period}',
                                          line=dict(width=2)))
        # Simple Moving Median 'SMM'
        elif name.lower() == 'smm':
            smm_period = int(input('Input SMM period: '))
            self.df[f'smm_{smm_period}'] = TA.SMM(self.df, smm_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'smm_{smm_period}'],
                                          name=f'EMA {smm_period}',
                                          line=dict(width=2)))
        # Smoothed Simple Moving Average 'SSMA'
        elif name.lower() == 'ssma':
            ssma_period = int(input('Input SSMA period: '))
            self.df[f'ssma_{ssma_period}'] = TA.SSMA(self.df, ssma_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'ssma_{ssma_period}'],
                                          name=f'SSMA {ssma_period}',
                                          line=dict(width=2)))
        # Exponential Moving Average 'EMA'
        elif name.lower() == 'ema':
            ema_period = int(input('Input EMA period: '))
            self.df[f'ema_{ema_period}'] = TA.EMA(self.df, ema_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'ema_{ema_period}'],
                                          name=f'EMA {ema_period}',
                                          line=dict(width=2)))
        # Double Exponential Moving Average 'DEMA'
        elif name.lower() == 'dema':
            dema_period = int(input('Input DEMA period: '))
            self.df[f'dema_{dema_period}'] = TA.DEMA(self.df, dema_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'dema_{dema_period}'],
                                          name=f'DEMA {dema_period}',
                                          line=dict(width=2)))
        # Triple Exponential Moving Average 'TEMA'
        elif name.lower() == 'tema':
            tema_period = int(input('Input TEMA period: '))
            self.df[f'tema_{tema_period}'] = TA.TEMA(self.df, tema_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'tema_{tema_period}'],
                                          name=f'TEMA {tema_period}',
                                          line=dict(width=2)))
        # Triangular Moving Average 'TRIMA'
        elif name.lower() == 'trima':
            trima_period = int(input('Input TRIMA period: '))
            self.df[f'trima_{trima_period}'] = TA.TRIMA(self.df, trima_period)
            self.fig.add_trace(go.Scatter(x=self.df['time'], y=self.df[f'trima_{trima_period}'],
                                          name=f'TRIMA {trima_period}',
                                          line=dict(width=2)))
        else:
            print("This indicator is not available yet")

    def beauty_print_data(self):
        print(tabulate(self.df, headers='keys', tablefmt='psql'))
        print(self.df.shape)

    def print_data(self):
        print(self.df)

    def show_chart(self):
        self.fig.update_layout(title=f'{self._pair} {self._timeframe}')
        self.fig.update_layout(xaxis_rangeslider_visible=False)
        self.fig.show()


if __name__ == '__main__':
    pair = input("input pair: ").upper()
    tf = process_tf(input("input timeframe: "))
    start = input("input start: ")
    end = input("input end: ")

    a = Data(pair=pair, timeframe=tf, start_date=start, end_date=end)

    while True:
        indicator_name = input('Input name of the indicator if you want to add one or press "Enter": ')
        if len(indicator_name) == 0:
            break
        else:
            a.add_indicator(indicator_name)

    # a.beauty_print_data()

    a.show_chart()
