import pandas as pd
import numpy as np


class ta:
    @classmethod
    def SMA(cls, ohlc, period=10, column='close') -> pd.Series:
        """
        Simple moving average
        """
        return pd.Series(
            data=ohlc[column].rolling(window=period).mean(),
            dtype=float,
            name=f'{period} period SMA'
        )

    @classmethod
    def SMM(cls, ohlc, period=10, column='close') -> pd.Series:
        """
        Simple moving median, an alternative to moving average
        """
        return pd.Series(
            data=ohlc[column].rolling(window=period).median(),
            dtype=float,
            name=f'{period} period SMM'
        )

    @classmethod
    def SSMA(cls, ohlc, period=10, column='close', adjust=True) -> pd.Series:
        """
        Smoothed simple moving average
        """
        return pd.Series(
            ohlc[column].ewm(ignore_na=False, alpha=1.0 / period, min_periods=0, adjust=adjust).mean(),
            dtype=float,
            name=f'{period} period SSMA'
        )

    @classmethod
    def EMA(cls, ohlc, period=10, column='close', adjust=True) -> pd.Series:
        """
        Exponential Moving Average
        """
        return pd.Series(
            data=ohlc[column].ewm(span=period, adjust=adjust).mean(),
            dtype=float,
            name=f'{period} period EMA'
        )

    @classmethod
    def DEMA(cls, ohlc, period=10, column='close', adjust=True) -> pd.Series:
        """
        Double Exponential Moving Average
        """
        return pd.Series(
            data=2 * cls.EMA(ohlc, period, column) - cls.EMA(ohlc, period, column).ewm(span=period,
                                                                                       adjust=adjust).mean(),
            dtype=float,
            name=f'{period} period DEMA'
        )

    @classmethod
    def TEMA(cls, ohlc, period=10, column='close', adjust=True) -> pd.Series:
        """
        Triple exponential moving average
        """
        triple_ema = 3 * cls.EMA(ohlc, period, column)
        ema_ema_ema = (
            cls.EMA(ohlc, period, column).
            ewm(ignore_na=False, span=period, adjust=adjust).mean().
            ewm(ignore_na=False, span=period, adjust=adjust).mean()
        )
        return pd.Series(
            data=triple_ema - 3 * cls.EMA(ohlc, period, column).ewm(span=period, adjust=adjust).mean() + ema_ema_ema,
            dtype=float,
            name=f'{period} period TEMA'
        )

    @classmethod
    def TRIMA(cls, ohlc, period=10, column='close') -> pd.Series:
        """
        Triangular Moving Average
        """
        return pd.Series(
            data=cls.SMA(ohlc, period, column).rolling(window=period).sum() / period,
            dtype=float,
            name=f'{period} period TRIMA'
        )

    @classmethod
    def TRIX(cls, ohlc, period=10, column='close', adjust=True) -> pd.Series:
        """
        The TRIX indicator calculates the rate of change of a triple exponential moving average.
        The values oscillate around zero. Buy/sell signals are generated when the TRIX crosses above/below zero.
        """
        data = ohlc[column]

        def _ema(data, period, adjust):
            return pd.Series(data.ewm(span=period, adjust=adjust).mean())

        m = _ema(_ema(_ema(data, period, adjust), period, adjust), period, adjust)
        return pd.Series(
            data=100 * (m.diff() / m),
            dtype=float,
            name=f'{period} period TRIX'
        )

    @classmethod
    def VAMA(cls, ohlcv, period=10, column='close') -> pd.Series:
        """
        Volume Adjusted Moving Average
        """
        vp = ohlcv['volume'] * ohlcv[column]
        vol_sum = ohlcv['volume'].rolling(window=period).mean()
        vol_ratio = pd.Series(vp / vol_sum, name="VAMA")
        cum_sum = (vol_ratio * ohlcv[column]).rolling(window=period).sum()
        cum_div = vol_ratio.rolling(window=period).sum()

        return pd.Series(
            data=cum_sum / cum_div,
            dtype=float,
            name=f'{period} period VAMA'
        )

    @classmethod
    def WMA(cls, ohlc, period=10, column='close') -> pd.Series:
        """
        Weighted moving average
        """
        denominator = (period * (period + 1)) / 2
        weights = np.arange(1, period + 1)

        def linear(w):
            def _compute(x):
                return (w * x).sum() / denominator

            return _compute

        _close = ohlc[column].rolling(period, min_periods=period)
        return pd.Series(
            data=_close.apply(linear(weights), raw=True),
            dtype=float,
            name=f'{period} period WMA',
        )

    @classmethod
    def SMMA(cls, ohlc, period=10, column='close', adjust=True) -> pd.Series:
        """
        Smoothed Moving Average gives recent prices an equal weighting to historic prices.
        """
        return pd.Series(
            data=ohlc[column].ewm(alpha=1 / period, adjust=adjust).mean(),
            dtype=float,
            name=f'{period} period SMMA'
        )

    @classmethod
    def MACD(cls, ohlc, period_fast=12, period_slow=26, signal=9, column='close', adjust=True) \
            -> [pd.Series, pd.Series, pd.Series]:
        """
        MACD, MACD Signal and MACD difference
        """
        EMA_fast = pd.Series(
            ohlc[column].ewm(ignore_na=False, span=period_fast, adjust=adjust).mean(),
            dtype=float,
            name='EMA_fast'
        )
        EMA_slow = pd.Series(
            ohlc[column].ewm(ignore_na=False, span=period_slow, adjust=adjust).mean(),
            dtype=float,
            name='EMA_slow'
        )
        MACD = pd.Series(
            EMA_fast - EMA_slow,
            dtype=float,
            name='MACD'
        )
        MACD_signal = pd.Series(
            MACD.ewm(ignore_na=False, span=signal, adjust=adjust).mean(),
            dtype=float,
            name='SIGNAL'
        )
        MACD_difference = MACD - MACD_signal
        return [MACD, MACD_signal, MACD_difference]

    @classmethod
    def MOM(cls, ohlc, period=10, column='close') -> pd.Series:
        """
        Market momentum
        """
        return pd.Series(
            data=ohlc[column].diff(period),
            dtype=float,
            name=f'{period} period MOM'
        )

    @classmethod
    def ROC(cls, ohlc, period=10, column='close') -> pd.Series:
        """
        The Rate-of-Change indicator
        """
        return pd.Series(
            data=(ohlc[column].diff(period) / ohlc[column].shift(period)) * 100,
            dtype=float,
            name='ROC'
        )

    @classmethod
    def RSI(cls, ohlc, period=10, column='close', adjust=True) -> pd.Series:
        """
        Relative Strength Index
        """
        delta = ohlc[column].diff()
        up, down = delta.copy(), delta.copy()
        up[up < 0] = 0
        down[down > 0] = 0

        # EMAs of ups and downs
        _gain = up.ewm(alpha=1.0 / period, adjust=adjust).mean()
        _loss = down.abs().ewm(alpha=1.0 / period, adjust=adjust).mean()
        RS = _gain / _loss
        return pd.Series(
            data=100 - (100 / (1 + RS)),
            dtype=float,
            name=f'{period} period RSI'
        )

    @classmethod
    def TR(cls, ohlc) -> pd.Series:
        """
        True Range is the maximum of three price ranges.
        Most recent period's high minus the most recent period's low.
        Absolute value of the most recent period's high minus the previous close.
        Absolute value of the most recent period's low minus the previous close.
        """
        TR1 = pd.Series(ohlc['high'] - ohlc['low']).abs()
        TR2 = pd.Series(ohlc['high'] - ohlc['close'].shift()).abs()
        TR3 = pd.Series(ohlc['close'].shift() - ohlc['low']).abs()
        _TR = pd.concat([TR1, TR2, TR3], axis=1)
        _TR['TR'] = _TR.max(axis=1)
        return pd.Series(
            data=_TR['TR'],
            dtype=float,
            name='TR'
        )

    @classmethod
    def ATR(cls, ohlc, period=10) -> pd.Series:
        """
        Average True Range is moving average of True Range.
        """
        TR = cls.TR(ohlc)
        return pd.Series(
            data=TR.rolling(center=False, window=period).mean(),
            dtype=float,
            name=f'{period} period ATR'
        )

    @classmethod
    def BBANDS(cls, ohlc) -> [pd.Series, pd.Series]:
        """
         Bollinger Bands
         """
        raise NotImplementedError

    @classmethod
    def KC(cls, ohlc) -> [pd.Series, pd.Series]:
        """
        Keltner Channels
        """
        raise NotImplementedError

    @classmethod
    def STOCH(cls, ohlc, period=14) -> pd.Series:
        """
        Stochastic oscillator %K
        """
        raise NotImplementedError

    @classmethod
    def WILLIAMS(cls, ohlc, period=10) -> pd.Series:
        """
        Williams %R, or just %R
        """
        raise NotImplementedError
