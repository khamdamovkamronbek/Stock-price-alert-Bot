# -*- coding: utf-8 -*-
"""
Created on Wed Dec  3 04:26:44 2025

@author: usernooo
"""

# -*- coding: utf-8 -*-
"""
SMASH BOT – FINAL PRODUCTION VERSION
Fixed Threading Error, Navigation, Hourly Charts, Consolidated Views, MA Analysis, Search & Crypto.
UPDATED: RSI Insight text changed.
UPDATED: STOCKS list reduced to TOP_20 for main view. All other stocks are searchable.
FIXED: Syntax Error due to non-printable characters in install() function.
FIXED: Undefined name error for alert_checker_thread by moving its definition.
NEW FEATURE: Allows up to 3 separate price alerts per ticker for each user.
"""

import subprocess, sys, time, threading
def install(p):
    # Fixed syntax by cleaning up string characters
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", p])

try: import telebot
except: install("pyTelegramBotAPI"); import telebot

try: import yfinance as yf
except: install("yfinance"); import yfinance as yf

try: import pandas as pd
except: install("pandas"); import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================
# CONFIG
# ============================
TOKEN = "8207664502:AAHXM21C6WU8y0yshaLB1AarkGKuJ9aMK50"
bot = telebot.TeleBot(TOKEN)

# Store alerts per user: {chat_id: {ticker: [price1, price2, ...]}}
# The list allows for up to 3 prices per ticker.
user_alerts = {}
# Store user states for multi-step interactions
user_states = {}

# Ticker lists
# For testing the 'View Stocks' button, we only use the top 20
TOP_20_STOCKS = [
    "AAPL","MSFT","AMZN","GOOGL","META","NVDA","TSLA","NFLX","BRK-B","JPM",
    "V","MA","HD","PG","XOM","CVX","BAC","KO","PEP","WMT"
]

# The STOCKS list used for the 'View Stocks' button and pagination logic
STOCKS = TOP_20_STOCKS # Only the Top 20 are visible via the button

# Fixed syntax by cleaning up string characters
COMMODITIES = ["GC=F", "SI=F", "CL=F"] 
COMMODITY_NAMES = {
    "GC=F": "Gold (GC=F)", 
    "SI=F": "Silver (SI=F)", 
    "CL=F": "Crude Oil (CL=F)"
}

CRYPTOS = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD"]
CRYPTO_NAMES = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "BNB-USD": "BNB",
    "SOL-USD": "Solana",
    "XRP-USD": "XRP"
}

# ============================
# ALERT CHECKER THREAD
# ============================
def alert_checker_thread():
    while True:
        try:
            if not user_alerts:
                time.sleep(60)
                continue
            
            all_tickers = set()
            for alerts in user_alerts.values():
                all_tickers.update(alerts.keys())
            
            if not all_tickers:
                time.sleep(60)
                continue
            
            # Fetch data for all unique tickers
            results = fetch_multiple_stocks(list(all_tickers), period="1d", max_workers=20)
            
            for chat_id, alerts in list(user_alerts.items()):
                for ticker, target_prices in list(alerts.items()): # target_prices is now a list
                    if ticker in results and results[ticker] is not None:
                        try:
                            hist = results[ticker]
                            if not hist.empty:
                                current_price = hist["Close"][-1]
                                
                                # Use a list comprehension to find triggered alerts (where current price >= target price)
                                triggered_prices = [p for p in target_prices if current_price >= p]
                                
                                if triggered_prices:
                                    # Send an alert message for each triggered price
                                    for triggered_price in triggered_prices:
                                        bot.send_message(
                                            chat_id,
                                            f"🚨 *ALERT TRIGGERED!* ({ticker})\n\n"
                                            f"Current Price: ${current_price:.2f}\n"
                                            f"Target Reached: ${triggered_price:.2f}",
                                            parse_mode="Markdown"
                                        )
                                        # Remove the specific triggered price from the list
                                        # Use a copy of the list for safe removal during iteration if needed, 
                                        # but here we remove it from the master list once it's triggered.
                                        user_alerts[chat_id][ticker].remove(triggered_price)
                                        
                                    # After removing triggered alerts, check if the list is now empty
                                    if not user_alerts[chat_id][ticker]:
                                        del user_alerts[chat_id][ticker]
                                        
                        except Exception as e:
                            print(f"Error processing alert for {ticker}: {e}")
                            pass
            
            time.sleep(60)
        except Exception as e:
            print(f"Alert checker error: {e}")
            time.sleep(60)


# ============================
# UTILITY FUNCTIONS
# ============================

def get_stock_page(page, size=10):
    start = page * size
    end = start + size
    return STOCKS[start:end], (end < len(STOCKS)), (page > 0)

def fetch_stock_data(ticker, period="6mo"):
    """Fetch data with timeout"""
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period=period)
        return ticker, hist
    except:
        return ticker, None

def fetch_multiple_stocks(tickers, period="6mo", max_workers=10):
    """Fetch multiple stocks in parallel"""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_stock_data, t, period): t for t in tickers}
        for future in as_completed(futures, timeout=45): 
            try:
                ticker, hist = future.result()
                results[ticker] = hist
            except Exception as e:
                results[ticker] = None
    return results

def get_forecast(ticker):
    """
    Predicts the next closing price using a basic Moving Average Crossover strategy.
    """
    try:
        df = yf.Ticker(ticker).history(period="60d")
        
        if len(df) < 50:
            return "N/A (Not enough data for MA forecast)"

        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean()
        
        last_close = df["Close"].iloc[-1]
        ma20_last = df["MA20"].iloc[-1]
        ma50_last = df["MA50"].iloc[-1]
        
        if ma20_last > ma50_last:
            forecast_price = last_close * 1.005
            signal = "🟢 Bullish"
        else:
            forecast_price = last_close * 0.995
            signal = "🔴 Bearish"
            
        return f"{signal} → ${forecast_price:.2f}"
        
    except Exception:
        return "N/A (Error during forecast calculation)"

# ============================
# CHART GENERATION
# ============================

def generate_rsi_chart(ticker, rsi_data):
    """Generates a separate RSI chart with 30/70 bands."""
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(rsi_data.index, rsi_data.values, label="RSI (14)", color="purple", linewidth=1.5)
    ax.axhline(70, color='red', linestyle='--', alpha=0.7, label='Overbought (70)')
    ax.axhline(30, color='green', linestyle='--', alpha=0.7, label='Oversold (30)')
    ax.axhline(50, color='gray', linestyle=':', alpha=0.5, label='Neutral (50)')
    ax.set_title(f"{ticker} Relative Strength Index (RSI)", fontsize=12, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.legend(loc='lower left', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf

def generate_stock_chart(ticker):
    """Generates 1-Month Hourly Price & MA Chart."""
    data = yf.Ticker(ticker).history(period="1mo", interval="1h") 
    if data.empty:
        return None

    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(data.index, data["Close"], label="Close Price", linewidth=2)
    ax.plot(data.index, data["MA20"], label="20-period MA", linestyle="--", alpha=0.7)
    ax.plot(data.index, data["MA50"], label="50-period MA", linestyle="--", alpha=0.7)

    ax.set_title(f"{ticker} – 1-Month Hourly Price & Moving Averages", fontsize=14, fontweight='bold')
    ax.set_xlabel("Date/Time")
    ax.set_ylabel("Price ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf

def send_chart_with_analysis(chat_id, ticker, analysis_text, back_callback="stocks_0"):
    """Sends the price chart with base analysis text as the caption."""
    try:
        chart = generate_stock_chart(ticker)
        if chart:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(InlineKeyboardButton("🧠 Tech Analysis", callback_data=f"analyze_{ticker}"))
            markup.add(InlineKeyboardButton("⏰ Set Alert", callback_data=f"alert_pick_{ticker}"))
            markup.add(InlineKeyboardButton("🔙 Back", callback_data=back_callback))
            markup.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            caption = (
                f"{analysis_text}\n"
                f"📈 {ticker} 1-Month Hourly Chart"
            )
            
            # COMBINED ANALYSIS TEXT AND CHART
            bot.send_photo(chat_id, chart, caption=caption, parse_mode="Markdown", reply_markup=markup) 
        else:
            bot.send_message(chat_id, f"❌ Could not generate chart or fetch data for {ticker}.")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Chart error: {str(e)}")

# ============================
# CORE ANALYSIS LOGIC
# ============================

def get_analysis(ticker):
    """Fetches base price data, MAs, and forecast."""
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="6mo") 

        if hist.empty:
            return f"❌ {ticker}: No data found."

        last = hist["Close"][-1]
        high = hist["High"].max()
        low = hist["Low"].min()
        
        prev = hist["Close"][-2] if len(hist) > 1 else last
        change = ((last - prev) / prev) * 100
        arrow = "🟢" if change >= 0 else "🔴"
        
        forecast_price = get_forecast(ticker)
        
        # Calculate MAs using 6 months of daily data
        hist["MA20"] = hist["Close"].rolling(20).mean()
        hist["MA50"] = hist["Close"].rolling(50).mean()
        ma20 = hist["MA20"].iloc[-1]
        ma50 = hist["MA50"].iloc[-1]

        return (
            f"📊 *{ticker} Analysis*\n\n"
            f"💰 Last Price: ${last:.2f}\n"
            f"{arrow} 24h Change: {change:+.2f}%\n"
            f"20-Day SMA: ${ma20:.2f}\n" 
            f"50-Day SMA: ${ma50:.2f}\n" 
            f"🔮 *Forecast (Tomorrow):* {forecast_price}\n" 
            f"🔼 6M High: ${high:.2f}\n"
            f"🔽 6M Low: ${low:.2f}\n"
        )
    except Exception as e:
        return f"❌ Error fetching data for {ticker}. ({e})"

def calculate_analytics(ticker, return_series=False):
    """Calculates RSI, Volatility, and MA comparison for the Tech Analysis report."""
    try:
        df = yf.Ticker(ticker).history(period="3mo")
        
        if df.empty or len(df) < 14: 
            error_msg = "Not enough data for 14-day calculation."
            return (error_msg, None) if return_series else error_msg

        # RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # Moving Averages
        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean()
        ma20 = df["MA20"].iloc[-1]
        ma50 = df["MA50"].iloc[-1]
        last_close = df["Close"].iloc[-1]
        
        # Volatility
        volatility = df['Close'].pct_change().rolling(window=14).std().iloc[-1] * 100

        # Signals
        if current_rsi > 70:
            signal = "🔥 OVERBOUGHT"
        elif current_rsi < 30:
            signal = "💎 OVERSOLD"
        else:
            signal = "⚖️ NEUTRAL"

        vol_msg = "High" if volatility > 2.0 else "Stable"
        ma_signal = "20-day > 50-day (Bullish)" if ma20 > ma50 else "50-day > 20-day (Bearish)"
        
        # >>>>>> MODIFIED INSIGHT AS REQUESTED <<<<<<
        insight = "An RSI over 70 suggests the stock is running too hot. Under 30 suggests it is undervalued."


        report = (
            f"🧠 *Tech Analysis for {ticker}*\n"
            f"--------------------------\n"
            f"📡 *RSI Signal:* {signal}\n"
            f"📊 *RSI Score:* {current_rsi:.1f}/100\n"
            f"🌊 *Volatility:* {volatility:.2f}% ({vol_msg})\n"
            f"--------------------------\n"
            f"💵 *Price vs. MAs:*\n"
            f"• Last Price: ${last_close:.2f}\n"
            f"• 20-Day SMA: ${ma20:.2f}\n"
            f"• 50-Day SMA: ${ma50:.2f}\n"
            f"• MA Signal: {ma_signal}\n" 
            f"--------------------------\n"
            f"💡 *Insight:* {insight}"
        )
        
        if return_series:
            return report, rsi.dropna()
        else:
            return report
            
    except Exception as e:
        error_msg = f"❌ Error calculating analytics: {e}"
        return (error_msg, None) if return_series else error_msg

# ============================
# HANDLERS - MENU & NAVIGATION
# ============================

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔎 Search Stock/Crypto", callback_data="start_search")) 
    markup.add(InlineKeyboardButton("📈 View Top 20 Stocks", callback_data="stocks_0"))
    markup.add(InlineKeyboardButton("💰 Commodities", callback_data="commodities"))
    markup.add(InlineKeyboardButton("💎 Cryptos", callback_data="cryptos"))
    markup.add(InlineKeyboardButton("📊 Market Heatmap", callback_data="heatmap"))
    markup.add(InlineKeyboardButton("⏰ Set Alert", callback_data="alert_menu"))
    markup.add(InlineKeyboardButton("📋 My Alerts", callback_data="view_alerts"))
    bot.send_message(message.chat.id, "Welcome to SMASH BOT ⚡\nChoose an option:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "main_menu")
def main_menu(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔎 Search Stock/Crypto", callback_data="start_search"))
    markup.add(InlineKeyboardButton("📈 View Top 20 Stocks", callback_data="stocks_0"))
    markup.add(InlineKeyboardButton("💰 Commodities", callback_data="commodities")) 
    markup.add(InlineKeyboardButton("💎 Cryptos", callback_data="cryptos"))
    markup.add(InlineKeyboardButton("📊 Market Heatmap", callback_data="heatmap"))
    markup.add(InlineKeyboardButton("⏰ Set Alert", callback_data="alert_menu"))
    markup.add(InlineKeyboardButton("📋 My Alerts", callback_data="view_alerts"))
    
    # FIX: Use try/except for edit_message_text to handle previous photo messages
    try:
        bot.edit_message_text(
            "Welcome to SMASH BOT ⚡\nChoose an option:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except telebot.apihelper.ApiTelegramException as e:
        if "there is no text in the message to edit" in str(e) or "message to edit not found" in str(e):
            # Delete the previous photo/non-editable message and send a new one
            try:
                # Add check to see if we are editing a photo message's caption, which is the root of the "no text" error.
                if call.message.caption:
                    bot.send_message(
                        call.message.chat.id,
                        "Welcome to SMASH BOT ⚡\nChoose an option:",
                        reply_markup=markup
                    )
                    return
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            bot.send_message(
                call.message.chat.id,
                "Welcome to SMASH BOT ⚡\nChoose an option:",
                reply_markup=markup
            )
        else:
             raise e

# Helper for handlers that display lists/text (Stocks, Commodities, Cryptos)
def handle_list_navigation(call, title, tickers, callback_prefix, back_callback):
    """Generalized handler for stock/commodity/crypto lists."""
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    # Check if we are handling a paginated stock list or fixed commodity/crypto list
    if callback_prefix == "stock_":
        page = int(call.data.split("_")[1])
        # Only the TOP 20 are listed here via STOCKS
        visible_tickers, has_next, has_prev = get_stock_page(page)
        list_title = f"📈 *Top 20 Stock List* (Page {page+1})" # Updated title
        
        for ticker in visible_tickers:
            markup.add(InlineKeyboardButton(ticker, callback_data=f"{callback_prefix}{ticker}"))
            
        nav_buttons = []
        if has_prev:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"stocks_{page-1}"))
        if has_next:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"stocks_{page+1}"))
        if nav_buttons:
            markup.row(*nav_buttons)
            
    else: # Commodities/Cryptos
        list_title = title
        name_map = CRYPTO_NAMES if callback_prefix == "crypto_" else COMMODITY_NAMES
        for ticker in tickers:
            name = name_map.get(ticker, ticker)
            markup.add(InlineKeyboardButton(name, callback_data=f"{callback_prefix}{ticker}"))
    
    markup.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
    
    # FIX: Use try/except for edit_message_text
    try:
        bot.edit_message_text(
            f"{list_title}\nSelect a ticker:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except telebot.apihelper.ApiTelegramException as e:
        if "there is no text in the message to edit" in str(e) or "message to edit not found" in str(e):
            # Delete and send new message
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            bot.send_message(
                call.message.chat.id,
                f"{list_title}\nSelect a ticker:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
             raise e
             
@bot.callback_query_handler(func=lambda c: c.data.startswith("stocks_"))
def show_stocks(call):
    handle_list_navigation(call, "📈 *Top 20 Stock List*", STOCKS, "stock_", "main_menu")

@bot.callback_query_handler(func=lambda c: c.data == "commodities")
def show_commodities(call):
    handle_list_navigation(call, "💰 *Commodity Prices*", COMMODITIES, "commodity_", "main_menu")

@bot.callback_query_handler(func=lambda c: c.data == "cryptos")
def show_cryptos(call):
    handle_list_navigation(call, "💎 *Top Cryptocurrencies*", CRYPTOS, "crypto_", "main_menu")
    
# ============================
# HANDLERS - PRICE VIEW
# ============================

def show_ticker_view(call, ticker, back_callback):
    """Unified handler for stock/commodity/crypto price view."""
    
    # We rely on send_chart_with_analysis sending a new photo message, 
    # so we preemptively delete the previous message if it's not a text edit.
    is_message_object = not isinstance(call, telebot.types.CallbackQuery) 
    
    if not is_message_object:
        bot.answer_callback_query(call.id, f"Loading {ticker}...")
        # Delete the previous list message (text/photo) to ensure clean display of photo
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
    
    analysis = get_analysis(ticker)
    # If the call object is actually a message object (from search), get the chat ID directly
    chat_id = call.chat.id if is_message_object else call.message.chat.id
    send_chart_with_analysis(chat_id, ticker, analysis, back_callback)
    
@bot.callback_query_handler(func=lambda c: c.data.startswith("stock_") and not c.data.startswith("stocks_"))
def show_stock(call):
    show_ticker_view(call, call.data.split("_")[1], back_callback="stocks_0")

@bot.callback_query_handler(func=lambda c: c.data.startswith("commodity_"))
def show_commodity(call):
    show_ticker_view(call, call.data.split("_")[1], back_callback="commodities")

@bot.callback_query_handler(func=lambda c: c.data.startswith("crypto_"))
def show_crypto(call):
    show_ticker_view(call, call.data.split("_")[1], back_callback="cryptos")

# ============================
# HANDLERS - ADVANCED ANALYTICS
# ============================
@bot.callback_query_handler(func=lambda c: c.data.startswith("analyze_"))
def run_analytics(call):
    ticker = call.data.split("_")[1]
    
    # Send loading message
    loading_msg = bot.send_message(call.message.chat.id, f"🧮 Crunching the numbers and generating chart for {ticker}...")
    
    report, rsi_series = calculate_analytics(ticker, return_series=True)
    
    # Determine the correct back button
    if ticker in COMMODITIES:
        back_callback_data = f"commodity_{ticker}"
    elif ticker in CRYPTOS:
        back_callback_data = f"crypto_{ticker}"
    else:
        # Default back to the price view. 
        back_callback_data = f"stock_{ticker}"
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Back to Price View", callback_data=back_callback_data)) 
    markup.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")) 
    
    if rsi_series is not None:
        chart_buffer = generate_rsi_chart(ticker, rsi_series)
        
        # Delete the previous loading message
        try:
             bot.delete_message(call.message.chat.id, loading_msg.message_id)
        except:
             pass
             
        # Send the report as the caption of the RSI chart (consolidated view)
        bot.send_photo(call.message.chat.id, chart_buffer, caption=f"{report}\n\n*RSI Visual for {ticker}*", parse_mode="Markdown", reply_markup=markup)
    else:
        # If no chart is generated, just send the report text with the buttons
        bot.send_message(call.message.chat.id, report, parse_mode="Markdown", reply_markup=markup)

# ============================
# HANDLERS - SEARCH
# ============================
@bot.callback_query_handler(func=lambda c: c.data == "start_search")
def start_search(call):
    user_states[call.message.chat.id] = {"action": "search"}
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    
    # FIX: Use try/except for edit_message_text
    try:
        bot.edit_message_text(
            "🔎 *Stock/Crypto Search*\n\nSend me the ticker symbol (e.g., `AAPL`, `BTC-USD`, `CL=F`) you want to analyze:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except telebot.apihelper.ApiTelegramException as e:
        if "message to edit not found" in str(e) or "there is no text in the message to edit" in str(e):
            try:
                # Add check to see if we are editing a photo message's caption, which is the root of the "no text" error.
                if call.message.caption:
                    bot.send_message(
                        call.message.chat.id, 
                        "🔎 *Stock/Crypto Search*\n\nSend me the ticker symbol (e.g., `AAPL`, `BTC-USD`, `CL=F`) you want to analyze:",
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
                    return
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            bot.send_message(
                call.message.chat.id, 
                "🔎 *Stock/Crypto Search*\n\nSend me the ticker symbol (e.g., `AAPL`, `BTC-USD`, `CL=F`) you want to analyze:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            raise e
            
    bot.register_next_step_handler(call.message, handle_search_query)

def handle_search_query(message):
    chat_id = message.chat.id
    if chat_id not in user_states or user_states[chat_id].get("action") != "search":
        bot.send_message(chat_id, "❌ Session expired. Use /start to begin.")
        return
    
    ticker = message.text.strip().upper()
    del user_states[chat_id]
    
    try:
        yf.Ticker(ticker).history(period="1d") # Quick check
        
        # Back button logic for search results is simplified: return to the main menu view (stock, commodity, or crypto)
        if ticker in COMMODITIES:
            back_data = "commodities"
        elif ticker in CRYPTOS:
            back_data = "cryptos"
        else:
            back_data = "stocks_0"
        
        # The first argument is a message object now, not a callback query
        show_ticker_view(message, ticker, back_data)
        
    except Exception as e:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔎 Try Again", callback_data="start_search"))
        markup.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        bot.send_message(chat_id, f"❌ Ticker *{ticker}* not found or is invalid. Please try again.", parse_mode="Markdown", reply_markup=markup)

# ============================
# HANDLERS - ALERTS
# ============================

@bot.callback_query_handler(func=lambda c: c.data == "alert_menu" or c.data.startswith("alert_pick_"))
def alert_menu(call):
    if call.data.startswith("alert_pick_"):
        ticker = call.data.split("_")[2]
        
        # Check current alert count before proceeding to price input
        current_alerts = user_alerts.get(call.message.chat.id, {}).get(ticker, [])
        if len(current_alerts) >= 3:
            bot.answer_callback_query(call.id, f"❌ Limit reached. You have 3 alerts for {ticker}.", show_alert=True)
            return

        user_states[call.message.chat.id] = {"action": "alert", "ticker": ticker}
        
        try:
            current = yf.Ticker(ticker).history(period="1d")["Close"][-1]
            price_text = f"\n💰 Current Price: ${current:.2f}"
        except:
            price_text = ""
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")) 
        
        # Ensure previous message is deleted if it was a photo
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
        bot.send_message(
            call.message.chat.id, 
            f"⏰ *Set Alert for {ticker}* ({len(current_alerts) + 1}/3 slots){price_text}\n\n"
            f"Step 2: Send me the target price\n"
            f"Example: Just type `150` if you want alert at $150",
            parse_mode="Markdown",
            reply_markup=markup
        )
        
        bot.register_next_step_handler(call.message, save_alert)
        return
        
    # Default 'alert_menu' logic
    markup = InlineKeyboardMarkup(row_width=5)
    popular = STOCKS[:15]
    for stock in popular:
        markup.add(InlineKeyboardButton(stock, callback_data=f"alert_pick_{stock}"))
    
    markup.add(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    
    try:
        bot.edit_message_text(
            "⏰ *Set Price Alert*\n\nStep 1: Choose a stock or use a ticker command (e.g. /alert aapl)",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except telebot.apihelper.ApiTelegramException as e:
        if "there is no text in the message to edit" in str(e) or "message to edit not found" in str(e):
             try:
                 # Add check to see if we are editing a photo message's caption, which is the root of the "no text" error.
                 if call.message.caption:
                    bot.send_message(
                        call.message.chat.id,
                        "⏰ *Set Price Alert*\n\nStep 1: Choose a stock or use a ticker command (e.g. /alert aapl)",
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
                    return
                 bot.delete_message(call.message.chat.id, call.message.message_id)
             except:
                 pass
             bot.send_message(
                 call.message.chat.id,
                 "⏰ *Set Price Alert*\n\nStep 1: Choose a stock or use a ticker command (e.g. /alert aapl)",
                 parse_mode="Markdown",
                 reply_markup=markup
             )
        else:
             raise e

def save_alert(message):
    chat_id = message.chat.id
    
    if chat_id not in user_states or user_states[chat_id].get("action") != "alert":
        bot.send_message(chat_id, "❌ Session expired. Use /start to begin.")
        return
    
    ticker = user_states[chat_id]["ticker"]
    
    try:
        price = float(message.text.strip())
        
        if chat_id not in user_alerts:
            user_alerts[chat_id] = {}
        
        # Initialize the list for the ticker if it doesn't exist
        if ticker not in user_alerts[chat_id]:
            user_alerts[chat_id][ticker] = []
            
        # Check if the limit of 3 alerts has been reached
        if len(user_alerts[chat_id][ticker]) >= 3:
            bot.send_message(
                chat_id,
                f"⚠️ *Alert Limit Reached*\n\nYou already have the maximum of 3 price alerts set for *{ticker}*.",
                parse_mode="Markdown"
            )
            del user_states[chat_id]
            return
            
        # Add the new price to the list
        user_alerts[chat_id][ticker].append(price)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📋 View My Alerts", callback_data="view_alerts"))
        markup.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        bot.send_message(
            chat_id,
            f"✅ Alert set! ({len(user_alerts[chat_id][ticker])}/3 slots)\n\n{ticker} → ${price:.2f}\n\nYou'll be notified when price reaches this level.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        
        del user_states[chat_id]
    except ValueError:
        bot.send_message(chat_id, "❌ Invalid price. Please send a number (e.g., 150.50)")


# ============================
# HANDLERS - MISC (View Alerts, Heatmap)
# ============================

@bot.callback_query_handler(func=lambda c: c.data == "view_alerts")
def view_alerts(call):
    chat_id = call.message.chat.id
    
    if chat_id not in user_alerts or not user_alerts[chat_id]:
        text = "📋 *Your Alerts*\n\nNo alerts set yet."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⏰ Set Alert", callback_data="alert_menu"))
        markup.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
    else:
        text = "📋 *Your Active Alerts*\n\n"
        markup = InlineKeyboardMarkup()
        for ticker, prices in user_alerts[chat_id].items(): # prices is now a list
            # Sort prices for display consistency
            for price in sorted(prices):
                text += f"• {ticker} → ${price:.2f}\n"
                # Encode the price in the callback data for unique removal
                # We use string formatting to ensure the price part is accurate
                markup.add(InlineKeyboardButton(f"❌ Remove {ticker} @ ${price:.2f}", callback_data=f"remove_alert_{ticker}_{price:.2f}"))
        markup.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
    
    try:
        bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "there is no text in the message to edit" in str(e) or "message to edit not found" in str(e):
            try:
                # Add check to see if we are editing a photo message's caption, which is the root of the "no text" error.
                if call.message.caption:
                    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
                    return
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
        else:
             raise e

@bot.callback_query_handler(func=lambda c: c.data.startswith("remove_alert_"))
def remove_alert(call):
    # Data is in the format: "remove_alert_TICKER_PRICE"
    parts = call.data.split("_")
    ticker = parts[2]
    # The price part might be floating point, so join the rest and try to parse it
    price_str = "_".join(parts[3:]) 
    
    try:
        price_to_remove = float(price_str)
    except ValueError:
        bot.answer_callback_query(call.id, "❌ Invalid alert identifier.")
        return
        
    chat_id = call.message.chat.id
    
    if chat_id in user_alerts and ticker in user_alerts[chat_id]:
        try:
            # Remove the specific price from the list
            user_alerts[chat_id][ticker].remove(price_to_remove)
            
            # If the list of alerts for the ticker is now empty, remove the ticker key
            if not user_alerts[chat_id][ticker]:
                del user_alerts[chat_id][ticker]
                
            bot.answer_callback_query(call.id, f"✅ Alert for {ticker} @ ${price_to_remove:.2f} removed")
            view_alerts(call)
        except ValueError:
            # This handles the unlikely case where the price was already removed
            bot.answer_callback_query(call.id, "❌ Alert not found.")
            view_alerts(call)

@bot.callback_query_handler(func=lambda c: c.data == "heatmap")
def heatmap(call):
    # Send temporary loading message, deleting the previous one if it was a photo.
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
        
    loading_msg = bot.send_message(call.message.chat.id, "📊 Generating heatmap... (top 20 movers)")
    
    results = fetch_multiple_stocks(STOCKS[:20], period="3d", max_workers=20)
    
    movers = []
    for ticker, hist in results.items():
        if hist is not None and len(hist) >= 2:
            try:
                diff = ((hist["Close"][-1] - hist["Close"][-2]) / hist["Close"][-2]) * 100
                movers.append((ticker, diff))
            except:
                pass
    
    movers.sort(key=lambda x: x[1], reverse=True)
    
    text = "🔥 *Top Movers (Latest Available Day)*\n\n"
    for ticker, chg in movers:
        arrow = "🟢" if chg >= 0 else "🔴"
        text += f"{arrow} {ticker}: {chg:+.2f}%\n"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    
    # Delete the loading message before sending the final result
    try:
        bot.delete_message(call.message.chat.id, loading_msg.message_id)
    except:
        pass
        
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


# ============================
# START EXECUTION
# ============================
print("✅ SMASH Bot is running (Final with 3x Alerts)...")
# The alert checker thread is now defined before this line.
threading.Thread(target=alert_checker_thread, daemon=True).start()
bot.infinity_polling()