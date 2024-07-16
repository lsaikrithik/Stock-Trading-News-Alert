import os
import requests
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)

# Environment Variables for API keys
ALPHA_VANTAGE_APIKEY = os.getenv("ALPHA_VANTAGE_APIKEY")
NEWS_APIKEY = os.getenv("NEWS_APIKEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STOCK_NAME = "TSLA"
STOCK_ENDPOINT = "https://www.alphavantage.co/query"
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"


def telegram_bot_send_text(bot_message):
    send_text = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&parse_mode=Markdown&text={bot_message}'
    try:
        bot_response = requests.get(send_text)
        bot_response.raise_for_status()
        return bot_response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending message to Telegram: {e}")
        return None


def get_change(current, previous):
    if current == previous:
        return 100.0
    try:
        performance = round(abs(current - previous) / previous, 5) * 100.0
        return performance
    except ZeroDivisionError:
        return 0


def get_stock_data():
    alpha_vantage_parameters = {
        "function": "TIME_SERIES_DAILY",
        "symbol": STOCK_NAME,
        "apikey": ALPHA_VANTAGE_APIKEY,
    }
    try:
        response = requests.get(STOCK_ENDPOINT, params=alpha_vantage_parameters)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching stock data: {e}")
        return None


def get_news_data():
    news_api_parameters = {
        "q": f"{STOCK_NAME} Market Update",
        "pageSize": 3,
        "apiKey": NEWS_APIKEY,
    }
    try:
        response = requests.get(NEWS_ENDPOINT, params=news_api_parameters)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching news data: {e}")
        return None


def process_data():
    stock_data = get_stock_data()
    news_data = get_news_data()

    if not stock_data or not news_data:
        logging.error("Failed to retrieve data.")
        return

    try:
        closing_prices = []
        for _, date in zip(range(3), stock_data['Time Series (Daily)']):
            closing_prices.append(float(stock_data['Time Series (Daily)'][date]['4. close']))

        yd_price = closing_prices[0]
        dyd_price = closing_prices[1]

        difference = yd_price - dyd_price
        up_down = "🔺" if difference > 0 else "🔻"

        change_percentage = get_change(yd_price, dyd_price)
        logging.info(f"{STOCK_NAME}: {up_down} {change_percentage}%")

        if change_percentage >= 5:
            messages = []
            for article in news_data['articles']:
                market_performance = f"{STOCK_NAME}: {up_down} {change_percentage}%"
                news_headline = f"Headline: {article['title']}"
                news_description = f"Description: {article['description']}"
                news_url = f"URL: {article['url']}"
                message = "\n".join([market_performance, news_headline, news_description, news_url])
                messages.append(message)
            
            for msg in messages:
                telegram_bot_send_text(msg)

        # Daily Summary
        summary = f"Stock Daily Summary for {STOCK_NAME}:\nYesterday's Closing Price: {yd_price}\nDay Before Yesterday's Closing Price: {dyd_price}\nChange: {difference} ({up_down} {change_percentage}%)"
        telegram_bot_send_text(summary)
    except KeyError as e:
        logging.error(f"Key error processing data: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    process_data()

