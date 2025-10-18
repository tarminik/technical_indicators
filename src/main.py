from data.fetcher import MarketDataFetcher
from datetime import datetime

from data.funding import FundingFetcher
from indicators import ind_periods

if __name__ == '__main__':
    pair = input("input pair: ").upper()
    tf = input("input timeframe: ")
    start = input("input start: ")
    end = input("input end: ")

    # Normalize dates for Binance helpers:
    # - If start is empty, use the app's default earliest date
    # - If start is in dd.mm.yyyy format, convert to ISO (yyyy-mm-dd)
    # - If end is empty, pass None so the client uses current time
    def normalize_start(s: str) -> str:
        s = s.strip()
        if not s:
            return "1 Jan, 1900"
        try:
            dt = datetime.strptime(s, "%d.%m.%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return s

    def normalize_end(s: str):
        s = s.strip()
        if not s:
            return None
        try:
            dt = datetime.strptime(s, "%d.%m.%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return s

    start = normalize_start(start)
    end = normalize_end(end)

    def ask_market() -> str:
        while True:
            choice = input('Select market ("spot" or "futures") [spot]: ').strip().lower()
            if not choice or choice == "spot":
                return "spot"
            if choice in ("futures", "future", "f"):
                return "futures"
            print('Unsupported market. Please enter "spot" or "futures".')

    market = ask_market()

    indicators = []
    i = 0
    while i < 5:
        indicator_name = input('Input name of the indicator if you want to add one or press "Enter": ').lower()
        if not indicator_name:
            break
        if indicator_name not in ind_periods.keys():
            print("I don't know this indicator. Try again.")
            continue
        if ind_periods[indicator_name] == 0:
            indicators.append([indicator_name])
        elif ind_periods[indicator_name] == 1:
            period = int(input(f"Input {indicator_name.upper()} period: "))
            indicators.append([indicator_name, period])
        else:
            fast = int(input(f"Input {indicator_name.upper()} fast period: "))
            slow = int(input(f"Input {indicator_name.upper()} slow period: "))
            indicators.append([indicator_name, fast, slow])
        i += 1

    fetcher = MarketDataFetcher(
        pair=pair,
        timeframe=tf,
        start_date=start,
        end_date=end,
        indicators=indicators,
        market=market,
    )

    fetcher.fetch()

    if fetcher.ohlcv.empty:
        print("No market data was retrieved for the specified parameters.")
    else:
        print(f"Loaded {len(fetcher.ohlcv)} rows for {pair} ({market}).")

    save_answer = input('Save fetched data to CSV? [y/N]: ').strip().lower()
    if save_answer in ('y', 'yes'):
        directory = input('Enter folder for CSV or press "Enter" for default ("data"): ').strip()
        target_dir = directory or "data"
        try:
            csv_path = fetcher.save_to_csv(target_dir)
            print(f"Data saved to {csv_path}")
        except ValueError as exc:
            print(f"CSV export skipped: {exc}")

    # Optional: fetch futures funding rates
    if market == "futures":
        want_funding = input('Fetch futures funding rates as well? [y/N]: ').strip().lower()
        if want_funding in ('y', 'yes'):
            coin_margin = input('Coin-margined futures? [y/N]: ').strip().lower() in ('y', 'yes')
            try:
                ff = FundingFetcher(symbol=pair, start_date=start, end_date=end, coin_margined=coin_margin)
                funding_df = ff.fetch()
                if funding_df.empty:
                    print("No funding data received.")
                else:
                    out_dir = input('Folder for funding CSV (default "data"): ').strip() or 'data'
                    path = f"{out_dir}/funding_{pair}_{'COIN' if coin_margin else 'USDT'}.csv"
                    import os
                    os.makedirs(out_dir, exist_ok=True)
                    funding_df.to_csv(path, index=False)
                    print(f"Funding data saved to {path}")
            except Exception as exc:
                print(f"Funding fetch failed: {exc}")
