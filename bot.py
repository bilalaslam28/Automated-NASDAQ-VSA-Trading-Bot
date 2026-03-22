import pytz
from datetime import datetime
from tradingview_screener import Query, Column
from alpaca.data.live import StockDataStream
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

query = (Query()
    .select('name', 'close', 'premarket_high', 'premarket_change', 'premarket_volume', 'market_cap_basic')
    .where(
        Column('exchange') == 'NASDAQ',
        Column('close') <= 15,
        Column('premarket_change') >= 22,
        Column('premarket_volume') >= 100000,
        Column('market_cap_basic').between(1, 2000000000) #This query selects the potential stocks to put into a monitoring list
    )
    .order_by('premarket_change', ascending=False)
)

count, df = query.get_scanner_data()
df['Pullback %'] = ((df['premarket_high'] - df['close']) / df['premarket_high']) * 100
df = df[df['Pullback %'] >= 21] #The bot will only monitor the stocks from a list where there is a pullback greater than 21%

if df.empty:
    print("Zero stocks meet criteria. Exiting.")
    exit()

tickers = df['name'].tolist()
pm_highs = df.set_index('name')['premarket_high'].to_dict()

API = 'YOUR_KEY' #Generate from Alpacca Dashboard
SEC = 'YOUR_KEY' #Generate from Alpacca Dashboard
stream = StockDataStream(API, SEC)
trade_client = TradingClient(API, SEC, paper=True)

history, vwap_data, active_signals = {}, {}, {}
daily_trades = 0

async def handle_bar(bar):
    global daily_trades
    uk_time = datetime.now(pytz.timezone('Europe/London'))
    
    if not (9 <= uk_time.hour <= 13 and (uk_time.hour < 13 or uk_time.minute <= 30)): return #When the script is run, the bot will be active only during 9am-1:30pm Uk time
    if daily_trades >= 3: return #After 3 trades the bot will stop

    sym = bar.symbol
    if sym not in vwap_data: vwap_data[sym] = {'v': 0, 'pv': 0}
    vwap_data[sym]['v'] += bar.volume
    vwap_data[sym]['pv'] += ((bar.high + bar.low + bar.close) / 3) * bar.volume
    vwap = vwap_data[sym]['pv'] / vwap_data[sym]['v']

    if sym not in history: history[sym] = []
    history[sym].append(bar)
    if len(history[sym]) > 3: history[sym].pop(0)

    if sym in active_signals:
        sig = active_signals[sym]
        if bar.close > sig['c'].high and bar.volume > history[sym][-2].volume:
            daily_trades += 1
            target = vwap if sig['type'] == 'deep' else bar.close * 1.06
            trade_client.submit_order(MarketOrderRequest(
                symbol=sym, qty=100, side=OrderSide.BUY, time_in_force=TimeInForce.DAY, order_class=OrderClass.BRACKET,
                take_profit=TakeProfitRequest(limit_price=round(target, 2)), stop_loss=StopLossRequest(stop_price=round(bar.close * 0.95, 2))
            ))
            del active_signals[sym]
        elif bar.low < sig['c'].low: del active_signals[sym]

    if len(history[sym]) == 3:
        p2, p1, c = history[sym]
        body = abs(c.close - c.open)
        if (min(c.open, c.close) - c.low) >= (2 * body) and (c.high - max(c.open, c.close)) < body and c.close >= c.open:
            vol_check = c.volume > p1.volume or (c.volume < p1.volume and c.volume < p2.volume)
            pm_high = pm_highs.get(sym, c.high)
            
            deep = ((pm_high - c.close) / pm_high >= 0.25) and ((vwap - c.close) / vwap >= 0.10)
            bounce = c.low <= vwap <= c.high
            
            if vol_check:
                if deep: active_signals[sym] = {'c': c, 'type': 'deep'}
                elif bounce: active_signals[sym] = {'c': c, 'type': 'bounce'}

print(f"Monitoring {len(tickers)} stocks.")
stream.subscribe_bars(handle_bar, *tickers)
stream.run()