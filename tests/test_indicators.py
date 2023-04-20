import pandas as pd

from indicators import ta

ohlcv = pd.read_csv('tests/data/binance_doge-usdt.csv')
cols = ['open', 'high', 'low', 'close', 'volume']
ohlcv[cols] = ohlcv[cols].apply(pd.to_numeric, errors='coerce', axis=1)


def test_SMA():
    ma_14 = ta.SMA(ohlc=ohlcv, period=14)
    ma_20 = ta.SMA(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "SMA should be pandas.Series"
    assert round(ma_14.values[13], 8) == 0.17252143, "SMA calculation error"
    assert round(ma_20.values[20], 8) == 0.17199500, "SMA calculation error"


def test_SMM():
    ma_14 = ta.SMM(ohlc=ohlcv, period=14)
    ma_20 = ta.SMM(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "SMM should be pandas.Series"
    assert round(ma_14.values[13], 8) == 0.17235000, "SMM calculation error"
    assert round(ma_20.values[20], 8) == 0.17205000, "SMM calculation error"


def test_SSMA():
    ma_14 = ta.SSMA(ohlc=ohlcv, period=14)
    ma_20 = ta.SSMA(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "SSMA should be pandas.Series"
    assert round(ma_14.values[13], 8) == 0.17268587, "SSMA calculation error"
    assert round(ma_20.values[20], 8) == 0.17182031, "SSMA calculation error"


def test_EMA():
    ma_14 = ta.EMA(ohlc=ohlcv, period=14)
    ma_20 = ta.EMA(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "EMA should be pandas.Series"
    assert round(ma_14.values[13], 8) == 0.17278802, "EMA calculation error"
    assert round(ma_20.values[20], 8) == 0.17164941, "EMA calculation error"


def test_DEMA():
    ma_14 = ta.DEMA(ohlc=ohlcv, period=14)
    ma_20 = ta.DEMA(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "DEMA should be pandas.Series"
    assert round(ma_14.values[13], 8) == 0.17312933, "DEMA calculation error"
    assert round(ma_20.values[20], 8) == 0.17119445, "DEMA calculation error"


def test_TEMA():
    ma_14 = ta.TEMA(ohlc=ohlcv, period=14)
    ma_20 = ta.TEMA(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "TEMA should be pandas.Series"
    assert round(ma_14.values[13], 8) == 0.17301027, "TEMA calculation error"
    assert round(ma_20.values[20], 8) == 0.17070423, "TEMA calculation error"


def test_TRIMA():
    ma_14 = ta.TRIMA(ohlc=ohlcv, period=14)
    ma_20 = ta.TRIMA(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "TRIMA should be pandas.Series"
    assert round(ma_14.values[30], 8) == 0.17072245, "TRIMA calculation error"
    assert round(ma_20.values[50], 8) == 0.16092175, "TRIMA calculation error"


def test_TRIX():
    ma_14 = ta.TRIX(ohlc=ohlcv, period=14)
    ma_20 = ta.TRIX(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "TRIX should be pandas.Series"
    assert round(ma_14.values[13], 8) == 0.04877133, "TRIX calculation error"
    assert round(ma_20.values[20], 8) == 0.00249371, "TRIX calculation error"


def test_VAMA():
    ma_14 = ta.VAMA(ohlcv=ohlcv, period=14)
    ma_20 = ta.VAMA(ohlcv=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "VAMA should be pandas.Series"
    assert round(ma_14.values[50], 8) == 0.1525688, "VAMA calculation error"
    assert round(ma_20.values[100], 8) == 0.18401432, "VAMA calculation error"


def test_WMA():
    ma_14 = ta.WMA(ohlc=ohlcv, period=14)
    ma_20 = ta.WMA(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "WMA should be pandas.Series"
    assert round(ma_14.values[50], 8) == 0.15260381, "WMA calculation error"
    assert round(ma_20.values[100], 8) == 0.17641000, "WMA calculation error"


def test_SMMA():
    ma_14 = ta.SMMA(ohlc=ohlcv, period=14)
    ma_20 = ta.SMMA(ohlc=ohlcv, period=20)
    assert isinstance(ma_14, pd.Series), "SMMA should be pandas.Series"
    assert round(ma_14.values[50], 8) == 0.15663464, "SMMA calculation error"
    assert round(ma_20.values[100], 8) == 0.17270517, "SMMA calculation error"


def test_MACD():
    MACD, MACD_signal, MACD_difference = ta.MACD(ohlc=ohlcv)
    assert isinstance(MACD, pd.Series) and isinstance(MACD_signal, pd.Series) and isinstance(MACD_difference,
                                                                                             pd.Series), "MACD should be pandas.Series"
    assert round(MACD.values[50], 8) == -0.00328653
    assert round(MACD_signal.values[50], 8) == -0.00335803
    assert round(MACD_difference.values[50], 8) == 0.00007151


def test_MOM():
    mom = ta.MOM(ohlc=ohlcv, period=14)
    assert isinstance(mom, pd.Series)
    assert round(mom.values[20], 8) == -0.00110000


def test_ROC():
    roc = ta.ROC(ohlc=ohlcv, period=14)
    assert isinstance(roc, pd.Series)
    assert round(roc.values[20], 8) == -0.63694268


def test_RSI():
    rsi = ta.RSI(ohlc=ohlcv, period=14)
    assert isinstance(rsi, pd.Series)
    assert round(rsi.values[20], 8) == 49.68370591


def test_TR():
    tr = ta.TR(ohlc=ohlcv)
    assert isinstance(tr, pd.Series)
    assert round(tr.values[20], 8) == 0.00190000


def test_ATR():
    tr = ta.ATR(ohlc=ohlcv)
    assert isinstance(tr, pd.Series)
    assert round(tr.values[20], 8) == 0.00260000


def test_BBANDS():
    upper_bb, middle_band, lower_bb = ta.BBANDS(ohlc=ohlcv)
    assert isinstance(upper_bb, pd.Series) and isinstance(middle_band, pd.Series) and isinstance(lower_bb,
                                                                                                 pd.Series), "BBANDS should be pandas.Series"
    assert round(upper_bb.values[50], 8) == 0.15871484
    assert round(middle_band.values[50], 8) == 0.15332857
    assert round(lower_bb.values[50], 8) == 0.14794230


def test_KC():
    up, down = ta.KC(ohlc=ohlcv)
    assert isinstance(up, pd.Series) and isinstance(down, pd.Series), "BBANDS should be pandas.Series"
    assert round(up.values[50], 8) == 0.16304539
    assert round(down.values[50], 8) == 0.14724539

def test_STOCH():
    st = ta.STOCH(ohlc=ohlcv)
    assert isinstance(st, pd.Series)
    assert round(st.values[20], 8) == 47.19101124

def test_WILLIAMS():
    w = ta.WILLIAMS(ohlc=ohlcv)
    assert isinstance(w, pd.Series)
    assert round(w.values[20], 8) == -52.80898876
