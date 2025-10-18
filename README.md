# technical_indicators

### Установка
```bash
git clone https://github.com/tarminik1223/technical_indicators.git
cd technical_indicators
pip install requirements.txt
```

### Получение данных
Запускаем интерактивный мастер:
```bash
python3 src/main.py
```

Вводим данные. Например:
```
input pair: DOGEUSDT
input timeframe: 4h
input start: 4-5-2022
input end: 4-10-2022
Select market ("spot" or "futures") [spot]:
Input name of the indicator if you want to add one or press "Enter": volume
Input name of the indicator if you want to add one or press "Enter": sma
Input SMA period: 10
Input name of the indicator if you want to add one or press "Enter": 
Loading data: 100% (37/37)
Loaded 37 rows for DOGEUSDT (spot).
Save fetched data to CSV? [y/N]: y
Enter folder for CSV or press "Enter" for default ("data"):
Data saved to data/DOGEUSDT-2022-04-05T00-00-00-2022-04-10T23-55-00-4h.csv
```

CSV-файл можно использовать для бэктестинга или дальнейшей обработки.

Чтобы получить фьючерсные котировки, на шаге выбора рынка укажите `futures`. После загрузки OHLCV CLI предложит (опционально) скачать историю ставок фандинга и сохранить её в CSV вида `data/funding_{SYMBOL}_{USDT|COIN}.csv`.

### Бэктестинг стратегий
Сохранённые датасеты можно прогонять через встроенный модуль анализа:
```bash
python3 src/backtest.py
```

Скрипт предложит выбрать CSV из каталога `data/`, затем стратегию. Для трендовых и mean-reversion моделей есть режим автоматического подбора параметров: ответьте `y` на запрос об оптимизации, и утилита переберёт пресеты и покажет топ комбинаций вместе с графиком equity.

Доступные стратегии:
- `Buy & Hold` — базовая модель удержания длинной позиции;
- `Moving Average Crossover` — пересечение двух скользящих средних (периоды можно задать вручную);
- `MTF Trend Breakout` — мульти-таймфрейм стратегия с фильтром тренда на H1, входами по пробою Donchian на M15, VWAP-фильтром, ATR-стопами, частичными фиксациями и трейлингом (используйте датасеты с M15 шагом).
- `VWAP Z-Score Mean Reversion` — минутная mean-reversion стратегия с лестничными входами по z-score относительно дневного VWAP, выходом у VWAP/тайм-стопом и фильтром по funding (требуются `1m` датасет и `data/funding_BTCUSDT_USDT.csv`).
- `EMA Ribbon Pullback` — работа по тренду: фильтр по H1/H4, стек EMA (8–55) на M15, вход после отката в «ленту», стоп/таргет через ATR, трейлинг и лимит сделок в день (используйте `15m` датасет).
- `Daily Trend Breakout` — долгосрочный Turtle-style подход: вход при пробое 40–60 дневного максимума, выход по минимуму 10–30 дней и ATR-сайзинг (используйте `1d` датасет).
- `DCA Strategy` — простой доллар-кост-эвериджинг: раз в месяц покупаем фиксированную сумму (по умолчанию 1000 $), комиссия учитывается как maker.

После запуска вы получите основные метрики: итоговая доходность, сравнение с buy&hold, годовая доходность, максимумальная просадка, коэффициент Шарпа и количество совершённых сделок.

Комиссии по умолчанию: Maker — 0.0180%, Taker — 0.0450%. Они учитываются при каждом изменении позиции (переворот, открытие, закрытие). Параметры можно менять в `src/config.py`. Стратегии могут занимать как длинные, так и короткие позиции — это удобно для торговли на фьючерсах.

### Структура кода
- `src/data/fetcher.py` — загрузка данных с Binance (spot и USDT-фьючерсы) + индикаторы и сохранение CSV.
- `src/data/funding.py` — загрузка истории ставок фандинга для USDT‑ и COIN‑маржинальных фьючерсов.
- `src/strategies/` — база стратегий: абстрактный класс `Strategy`, примеры `BuyAndHoldStrategy`, `MovingAverageCrossStrategy`, `MTFTrendBreakoutStrategy`, `VWAPZScoreStrategy`, `EMARibbonStrategy`, `DailyTrendBreakoutStrategy`, `DCAStrategy`.
- `src/backtesting/engine.py` — функции для запуска бэктестов, расчёта метрик и анализа нескольких датасетов (поддерживает как простые сигнальные, так и исполнение-зависимые стратегии).
- `src/backtest.py` — CLI-интерфейс для выбора датасета и стратегии.

Добавляйте собственные стратегии в `src/strategies/` и подключайте их через CLI либо напрямую в коде анализа. Для тонкой настройки бэктестинга (комиссии, тип ордеров) редактируйте `src/config.py`.
