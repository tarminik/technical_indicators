from get_data import Data
from dash import Dash, html, dcc, callback, Output, Input

if __name__ == '__main__':
    pair = input("input pair: ").upper()
    tf = input("input timeframe: ")
    start = input("input start: ")
    end = input("input end: ")

    data = Data(pair=pair, timeframe=tf, start_date=start, end_date=end)

    for i in range(5):
        indicator_name = input('Input name of the indicator if you want to add one or press "Enter": ')
        if not indicator_name:
            break
        else:
            data.add_indicator(indicator_name)

    data.beauty_print_data()

    app = Dash(__name__)
    app.layout = html.Div([dcc.Graph(mathjax=True, figure=data.chart())])
    app.run_server(debug=True)
