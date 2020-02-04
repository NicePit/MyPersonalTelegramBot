from flask import Flask, request, jsonify

from bot import TelegramBot
from config import TELEGRAM_INIT_WEBHOOK_URL
from ticket_bot import FareFinder
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
TelegramBot.init_webhook(TELEGRAM_INIT_WEBHOOK_URL)


@app.route('/tickets', methods=['GET'])
def search_tickets():
    finder = FareFinder()
    bot = TelegramBot()
    direct_tickets, all_tickets = finder.run(min_days=3, max_days=7, departure_months=[4], departure_days=[1])
    finder.close_driver()

#
# cron = BackgroundScheduler(daemon=True)
# cron.add_job(search_tickets, 'interval', minutes=1)
# cron.start()


@app.route('/', methods=['GET'])
def index():
    return jsonify(message="App is working")


@app.route('/webhook', methods=['POST'])
def telegram_post():
    print("New webhook request")
    pass
    # req = request.get_json()
    # bot = TelegramBot()
    # bot.parse_webhook_data(req)
    # success = bot.action()
    # return jsonify(success=success)
    return {"message": "Request from telegram is processed"}


if __name__ == '__main__':
    app.run(port=5000)
