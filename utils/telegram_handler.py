import requests
from utils.logger import setup_logger
from config import Config

logger = setup_logger("Telegram")

class TelegramHandler:
    def __init__(self):
        self.token = Config.TELEGRAM_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)
        
        if not self.enabled:
            logger.warning("Telegram credentials missing. Alerts disabled.")

    def send_message(self, message):
        """
        Sends a text message to the configured Telegram chat.
        """
        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to send Telegram message: {response.text}")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")

    def send_trade_alert(self, symbol, direction, entry, sl, tp, strategy_name="ICT Setup"):
        """
        Formats and sends a trade alert.
        """
        emoji = "🟢" if direction == "BUY" else "🔴"
        message = (
            f"{emoji} **NEW TRADE ALERT** {emoji}\n\n"
            f"**Symbol**: {symbol}\n"
            f"**Direction**: {direction}\n"
            f"**Strategy**: {strategy_name}\n\n"
            f"**Entry**: {entry:.5f}\n"
            f"**SL**: {sl:.5f}\n"
            f"**TP**: {tp:.5f}\n"
            f"**RR**: {Config.RR_RATIO}:1\n\n"
            f"⏳ *Pending Execution / Executed*"
        )
        self.send_message(message)
