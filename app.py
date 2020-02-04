from flask import Flask, jsonify

from bot import TelegramBot
from config import TELEGRAM_INIT_WEBHOOK_URL
from ticket_bot import search_tickets
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
TelegramBot.init_webhook(TELEGRAM_INIT_WEBHOOK_URL)


@app.route('/', methods=['GET'])
def index():
    return jsonify(message="Server is running")


@app.route('/webhook', methods=['POST'])
def telegram_post():
    print("New webhook request")
    return {"message": "Request from telegram is processed"}


cron = BackgroundScheduler(daemon=True)
cron.add_job(search_tickets, 'interval', hours=12,
             kwargs={'min_days': 3, 'max_days': 7,
                     'departure_months': [4], 'departure_days': [1]})
cron.start()


if __name__ == '__main__':
    app.run(port=5000)
