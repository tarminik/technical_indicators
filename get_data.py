import datetime

import pandas as pd
import plotly.graph_objects as go
from binance.client import Client
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

    def beauty_print_data(self):
        print(tabulate(self.df, headers='keys', tablefmt='psql'))
        print(self.df.shape)

    def print_data(self):
        print(self.df)

    def show_chart(self):
        fig = go.Figure(data=[go.Candlestick(x=self.df['time'],
                                             open=self.df['open'],
                                             high=self.df['high'],
                                             low=self.df['low'],
                                             close=self.df['close'])])
        fig.update_layout(title=f'{self._pair}')
        fig.show()


if __name__ == '__main__':
    # pair = input("input pair: ").upper()
    # tf = process_tf(input("input timeframe: "))
    # start = input("input start: ")
    # end = input("input end: ")

    a = Data('''pair=pair, timeframe=tf, start_date=start, end_date=end''')

    a.show_chart()
