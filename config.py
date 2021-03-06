import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ['TELEGRAM_SECRET_TOKEN']
APP_ENDPOINT = os.environ['APP_ENDPOINT']
BASE_TELEGRAM_URL = 'https://api.telegram.org/bot{}'.format(TOKEN)
TELEGRAM_WEBHOOK_ENDPOINT = '{}/webhook'.format(APP_ENDPOINT)
TELEGRAM_INIT_WEBHOOK_URL = '{}/setWebhook?url={}'.format(BASE_TELEGRAM_URL, TELEGRAM_WEBHOOK_ENDPOINT)
TELEGRAM_SEND_MESSAGE_URL = BASE_TELEGRAM_URL + '/sendMessage?chat_id={}&text={}'
