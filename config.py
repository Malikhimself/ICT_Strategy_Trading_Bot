import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # MT5 Credentials
    MT5_LOGIN = int(os.getenv("MT5_LOGIN", 5044833358))
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "ScQo*mL7")
    MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
    MT5_PATH = os.getenv("MT5_PATH", "") # Optional: Path to terminal64.exe

    # Execution Mode: "WINDOWS_MT5", "METAAPI", "DERIV"
    EXECUTION_MODE = os.getenv("EXECUTION_MODE", "WINDOWS_MT5").upper()

    # MetaApi Credentials
    METAAPI_TOKEN = os.getenv("METAAPI_TOKEN", "")
    METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID", "")

    # Deriv Credentials
    DERIV_APP_ID = os.getenv("DERIV_APP_ID", "1089")
    DERIV_TOKEN = os.getenv("DERIV_TOKEN", "")

    # Telegram
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8509072175:AAFaNfIMYxjedyoENyN141yzumAMqd9L530")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7098215516")

    # Trading Settings
    SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "EURUSD,GBPUSD,USDJPY,XAUUSD").split(",")]
    TIMEFRAMES = {
        "structure": "H4",
        "trend": "H1",
        "confirm": "M15",
        "entry": "M5"
    }
    
    # Risk Management
    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.01)) # 1%
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", 0.03)) # 3%
    RR_RATIO = float(os.getenv("RR_RATIO", 2.0)) # Risk:Reward 1:2

    # Bot Settings
    # If "IS_DRY_RUN" is not set, default to False (Live Trading) as per user intent
    IS_DRY_RUN = str(os.getenv("IS_DRY_RUN", "False")).lower() == "true"
    LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", 60)) # Seconds (Check every minute)
    
    # Timezone
    TIMEZONE = "Etc/UTC" # Default to UTC, adjust as needed for broker server time
