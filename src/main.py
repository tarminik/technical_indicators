from get_data import Data

from indicators import ind_periods

if __name__ == '__main__':
    pair = input("input pair: ").upper()
    tf = input("input timeframe: ")
    start = input("input start: ")
    end = input("input end: ")

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

    data = Data(pair=pair, timeframe=tf, start_date=start, end_date=end, indicators=indicators)

    """while True:
        indicator_name = input('Input name of the indicator if you want to add one or press "Enter": ')
        if not indicator_name:
            break
        else:
            data.add_indicator(indicator_name)"""

    data.beauty_print_data()
    data.show_chart()
