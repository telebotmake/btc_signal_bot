# Logging settings
import requests
import pandas as pd
import talib
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import logging

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Constants
HISTORICAL_API_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
LIVE_PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price"
API_TOKEN = "your_telegram_api_token"

# Function to fetch historical data
def fetch_historical_data():
    params = {'vs_currency': 'usd', 'days': '100', 'interval': 'daily'}
    response = requests.get(HISTORICAL_API_URL, params=params)

    if response.status_code != 200:
        logging.error(f"API Error: {response.status_code}")
        raise Exception("Failed to fetch historical data from API.")

    data = response.json()
    prices = data['prices']

    df = pd.DataFrame(prices, columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # Calculate indicators
    df['SMA_50'] = talib.SMA(df['price'], timeperiod=50)
    df['RSI'] = talib.RSI(df['price'], timeperiod=14)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(
        df['price'], fastperiod=12, slowperiod=26, signalperiod=9
    )
    df['Upper_Band'], df['Middle_Band'], df['Lower_Band'] = talib.BBANDS(
        df['price'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
    )
    df['Doji'] = talib.CDLDOJI(df['price'], df['price'], df['price'], df['price'])
    df['Hammer'] = talib.CDLHAMMER(df['price'], df['price'], df['price'], df['price'])

    return df

# Function to fetch live price
def fetch_live_price():
    params = {'ids': 'bitcoin', 'vs_currencies': 'usd'}
    response = requests.get(LIVE_PRICE_API_URL, params=params)

    if response.status_code != 200:
        logging.error(f"API Error: {response.status_code}")
        raise Exception("Failed to fetch live price from API.")

    data = response.json()
    return data['bitcoin']['usd']

# Signal analysis
def analyze_signal(df, live_price):
    sma_50 = df['SMA_50'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    macd = df['MACD'].iloc[-1]
    macd_signal = df['MACD_signal'].iloc[-1]
    upper_band = df['Upper_Band'].iloc[-1]
    lower_band = df['Lower_Band'].iloc[-1]
    doji = df['Doji'].iloc[-1]
    hammer = df['Hammer'].iloc[-1]

    signal = "HOLD"
    reason = "Conditions don't indicate a clear trend."

    if live_price > sma_50 and rsi < 30 and macd > macd_signal and live_price < lower_band and hammer:
        signal = "BUY"
        reason = (
            "Price is above SMA50, RSI is low (<30), MACD crosses above signal, "
            "price near lower Bollinger Band, and Hammer pattern detected."
        )
    elif live_price < sma_50 and rsi > 70 and macd < macd_signal and live_price > upper_band and doji:
        signal = "SELL"
        reason = (
            "Price is below SMA50, RSI is high (>70), MACD crosses below signal, "
            "price near upper Bollinger Band, and Doji pattern detected."
        )

    indicator_status = (
        f"Live Price: {live_price}\n"
        f"SMA 50: {sma_50}\n"
        f"RSI: {rsi}\n"
        f"MACD: {macd}, Signal Line: {macd_signal}\n"
        f"Bollinger Bands: Lower: {lower_band}, Upper: {upper_band}\n"
        f"Doji Pattern: {doji}\n"
        f"Hammer Pattern: {hammer}\n"
    )

    return signal, reason, indicator_status

# /signal command
async def signal(update: Update, context: CallbackContext):
    try:
        df = fetch_historical_data()
        live_price = fetch_live_price()
        signal, reason, indicator_status = analyze_signal(df, live_price)
        await update.message.reply_text(
            f"Signal: {signal}\nReason: {reason}\n\nIndicator Status:\n{indicator_status}"
        )
    except Exception as e:
        logging.error(f"Error in /signal command: {e}")
        await update.message.reply_text("Error fetching or analyzing data.")

# /start command
async def start(update: Update, context: CallbackContext):
    welcome_message = (
        "Welcome to the Bitcoin Signal Bot!\n\n"
        "Use /signal to get the latest buy/sell signal based on indicators such as:\n"
        "- SMA, RSI, MACD\n"
        "- Bollinger Bands\n"
        "- Candlestick patterns (Doji, Hammer)"
    )
    await update.message.reply_text(welcome_message)

# Bot setup
def main():
    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('signal', signal))
    application.run_polling()

if __name__ == '__main__':
    main()
