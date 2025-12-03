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
