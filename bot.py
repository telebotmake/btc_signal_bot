import requests
import pandas as pd
import talib
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import time

# Define constants
API_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
API_TOKEN = "your_telegram_bot_token"  # Update with your bot token

# Function to fetch data from CoinGecko API
def fetch_data():
    params = {'vs_currency': 'usd', 'days': '100'}
    response = requests.get(API_URL, params=params)
    data = response.json()

    prices = data['prices']
    df = pd.DataFrame(prices, columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # Calculate indicators
    df['SMA_50'] = talib.SMA(df['price'], timeperiod=50)
    df['RSI'] = talib.RSI(df['price'], timeperiod=14)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(df['price'], fastperiod=12, slowperiod=26, signalperiod=9)
    df['Upper_Band'], df['Middle_Band'], df['Lower_Band'] = talib.BBANDS(df['price'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
    
    # Add candlestick pattern recognition
    df['Doji'] = talib.CDLDOJI(df['price'], df['price'], df['price'], df['price'])
    df['Hammer'] = talib.CDLHAMMER(df['price'], df['price'], df['price'], df['price'])
    
    return df

# Function to analyze signals and provide reasons based on indicators
def analyze_signal(df):
    current_price = df['price'].iloc[-1]
    sma_50 = df['SMA_50'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    macd = df['MACD'].iloc[-1]
    macd_signal = df['MACD_signal'].iloc[-1]
    upper_band = df['Upper_Band'].iloc[-1]
    lower_band = df['Lower_Band'].iloc[-1]
    doji = df['Doji'].iloc[-1]
    hammer = df['Hammer'].iloc[-1]

    # Define conditions for Buy, Sell, or Hold based on indicators
    signal = "HOLD"
    reason = "Conditions don't indicate a clear trend. No Buy or Sell signal based on the indicators."
    
    # Check for Buy conditions
    if current_price > sma_50 and rsi < 30 and macd > macd_signal and current_price < lower_band and hammer:
        signal = "BUY"
        reason = f"Price is above SMA50, RSI is low (<30), MACD crosses above signal, price at lower Bollinger Band, and a Hammer candlestick pattern detected. Strong Buy signal."

    # Check for Sell conditions
    elif current_price < sma_50 and rsi > 70 and macd < macd_signal and current_price > upper_band and doji:
        signal = "SELL"
        reason = f"Price is below SMA50, RSI is high (>70), MACD crosses below signal, price at upper Bollinger Band, and a Doji candlestick pattern detected. Strong Sell signal."

    # Now add the status of each indicator to the reason
    indicator_status = (
        f"Current Price: {current_price}\n"
        f"SMA 50: {sma_50}\n"
        f"RSI: {rsi} (Overbought: >70, Oversold: <30)\n"
        f"MACD: {macd} (Signal Line: {macd_signal})\n"
        f"Bollinger Bands: Lower: {lower_band}, Upper: {upper_band}\n"
        f"Doji Pattern: {doji}\n"
        f"Hammer Pattern: {hammer}\n"
    )

    return signal, reason, indicator_status, current_price

# Function to send signal to Telegram via /signal command
async def signal(update: Update, context: CallbackContext):
    df = fetch_data()
    signal, reason, indicator_status, current_price = analyze_signal(df)
    await update.message.reply_text(f"Signal: {signal}\nReason: {reason}\n\nIndicator Status:\n{indicator_status}\n\nCurrent Price: {current_price}")

# Function to send a welcome message
async def start(update: Update, context: CallbackContext):
    welcome_message = (
        "Welcome to the Bitcoin Signal Bot!\n\n"
        "I will provide you with buy/sell signals based on various technical indicators and candlestick patterns.\n\n"
        "Here's an overview of the indicators and candlestick patterns I use:\n\n"
        "1. **SMA (Simple Moving Average)**: Helps identify the trend. A price above the SMA usually means a bullish trend.\n"
        "2. **RSI (Relative Strength Index)**: Measures whether an asset is overbought or oversold. RSI > 70 indicates overbought (sell signal), and RSI < 30 indicates oversold (buy signal).\n"
        "3. **MACD (Moving Average Convergence Divergence)**: Used to identify price momentum. A crossover of the MACD line above the signal line indicates a buy, and vice versa.\n"
        "4. **Bollinger Bands**: Shows the volatility of the asset. Price touching the upper band could be a sell signal, while touching the lower band might be a buy signal.\n"
        "5. **Candlestick Patterns**: I also detect patterns like **Doji** (indicating indecision) and **Hammer** (indicating a potential reversal).\n\n"
        "Use the command `/signal` to get the latest buy/sell signal."
    )
    await update.message.reply_text(welcome_message)

# Main function to run the bot
def main():
    # Create the Application and pass in the bot's API token
    application = Application.builder().token(API_TOKEN).build()

    # Register the /start and /signal command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('signal', signal))

    # Start the Bot
    application.run_polling()

# Run the bot
if __name__ == '__main__':
    main()

