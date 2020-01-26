import requests
from config import TELEGRAM_SEND_MESSAGE_URL
from ticket_bot import TicketFinder


class TelegramBot:

    def __init__(self):
        """"
        Initializes an instance of the TelegramBot class.
        Attributes:
            chat_id:str: Chat ID of Telegram chat, used to identify which conversation outgoing messages should be send to.
            text:str: Text of Telegram chat
            first_name:str: First name of the user who sent the message
            last_name:str: Last name of the user who sent the message
        """

        self.chat_id = None
        self.text = None
        self.first_name = None
        self.last_name = None

    def parse_webhook_data(self, data):
        """
        Parses Telegram JSON request from webhook and sets fields for conditional actions
        Args:
            data:str: JSON string of data
        """

        message = data['message']

        self.chat_id = message['chat']['id']
        self.incoming_message_text = message['text'].lower()
        self.first_name = message['from']['first_name']
        self.outgoing_message_text = ''

    def action(self):
        """
        Conditional actions based on set webhook data.
        Returns:
            bool: True if the action was completed successfully else false
        """

        success = None

        if self.incoming_message_text == '/hello':
            self.outgoing_message_text = "Hello {}!".format(self.first_name)
            success = self.send_message()

        if self.incoming_message_text == '/rad':
            self.outgoing_message_text = '🤙bee'
            success = self.send_message()

        if self.incoming_message_text == '/tickets':
            self.outgoing_message_text = '🤙Searching for tickets...It can take some time'
            success = self.send_message()
            cls = TicketFinder()
            cls.run(destination=None, min_days=3, max_days=7, target_month=4, departure_days=[1,2])

        return success

    def send_message(self):
        """
        Sends message to Telegram servers.
        """

        res = requests.get(TELEGRAM_SEND_MESSAGE_URL.format(self.chat_id, self.outgoing_message_text))

        return True if res.status_code == 200 else False

    @staticmethod
    def init_webhook(url):
        """
        Initializes the webhook
        Args:
            url:str: Provides the telegram server with a endpoint for webhook data
        """

        response = requests.get(url)
        if response.status_code == 200:
            print(url)
            print('Webhook is successufully set up')
        else:
            print('BAM!')