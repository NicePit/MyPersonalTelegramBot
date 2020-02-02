from flask import Flask, request, jsonify

from bot import TelegramBot
from config import TELEGRAM_INIT_WEBHOOK_URL
from ticket_bot import TicketFinder
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
TelegramBot.init_webhook(TELEGRAM_INIT_WEBHOOK_URL)


@app.route('/tickets', methods=['GET'])
def search_tickets():
    finder = TicketFinder()
    bot = TelegramBot()
    finder.run(destination=None, min_days=3, max_days=7, target_month=4, departure_days=[1])
    finder.close_driver()
    direct_tickets = finder.direct_tickets.head(1)
    serialized_tickets = direct_tickets.to_dict()
    bot.send_ticket_options(serialized_tickets)

#
# cron = BackgroundScheduler(daemon=True)
# cron.add_job(search_tickets, 'interval', minutes=1)
# cron.start()


@app.route('/', methods=['GET'])
def index():
    return jsonify(success={"message": "App is working"})


@app.route('/webhook', methods=['POST'])
def telegram_post():
    print("New webhook request")
    pass
    # req = request.get_json()
    # bot = TelegramBot()
    # bot.parse_webhook_data(req)
    # success = bot.action()
    # return jsonify(success=success)


if __name__ == '__main__':
    app.run(port=5000)
