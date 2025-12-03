# Stock-price-alert-Bot
Bot give live stock price, analysis and forecast 
# SMASH BOT – Stock Market Analytics & Smart Helper  
Telegram Financial Assistant Bot (Python + yFinance + Technical Analysis)

---

## 📖 Overview  
SMASH BOT is an advanced Telegram bot that provides real-time financial market insights, technical analysis, RSI indicators, moving averages, volatility, and smart price alerts.

It supports:
- 📈 **Top stocks**
- 💎 **Cryptocurrencies**
- 💰 **Commodities**
- 🔔 **Multi-Alert System** (up to 3 alerts per ticker per user)
- 🧠 **Technical Analysis**
- 🔮 **Forecasting via MA crossovers**
- 📊 **Beautiful Matplotlib charts**
- 🔎 **Search any stock or crypto symbol**

---

## 🚀 Features

### ✔ Stock & Crypto Search  
Enter any ticker (AAPL, TSLA, BTC-USD, etc.).

### ✔ Price Chart Generation  
• 1-Month Hourly Chart  
• Moving Average (MA20, MA50)

### ✔ Technical Analysis  
Provides:
- RSI (14)
- Overbought/Oversold signals
- Volatility%
- MA20 vs MA50 signal
- Trend Insight Text

### ✔ RSI Chart  
Shows RSI line with support lines at 30/50/70.

### ✔ Smart Alerts System  
- Each user may create **up to 3 alerts per ticker**.  
- Alerts trigger when price rises above target.  
- Alerts auto-delete after triggered.

### ✔ Parallel Data Fetching
Speeds up data collection using `ThreadPoolExecutor`.

---

## 🧩 Tech Stack

| Component        | Library / Tool          |
|------------------|--------------------------|
| Bot Framework    | PyTelegramBotAPI         |
| Market Data      | yFinance                 |
| Charting         | Matplotlib               |
| Data Handling    | Pandas                   |
| Threading        | ThreadPoolExecutor       |

---

## 📦 Installation

```bash
pip install pyTelegramBotAPI yfinance pandas matplotlib
python bot.py
Configuration

Edit your Telegram bot token:

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

📂 Project Structure
smashbot/
│
├── bot.py                 # Main bot script
├── README.md              # Documentation
└── charts/ (optional)     # Saved charts (if using)

🧠 How it Works
1. User selects a stock

Bot fetches market data → generates chart → returns analysis.

2. User sets an alert

Alert stored in dictionary:

user_alerts[chat_id][ticker] = [price1, price2, price3]

3. Background thread checks alerts

Every 60 seconds:

Download latest price

Compare against target

Send alert if triggered

4. Technical Analysis

Bot computes:

RSI(14)

MA20 & MA50 crossover

Volatility (std of returns)

Market signal (Bullish, Bearish, Neutral)

📝 License

MIT License — free for modification & commercial use.

👥 Authors

Developed by Team 5 – Final Production Version.
