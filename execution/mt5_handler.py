import MetaTrader5 as mt5
import time
import pandas as pd
from utils.logger import setup_logger
from config import Config
from execution.base_handler import ExecutionHandler
from datetime import datetime

logger = setup_logger("MT5_Handler")

class MT5Handler(ExecutionHandler):
    def __init__(self):
        self.connected = False
        self.login = Config.MT5_LOGIN
        self.password = Config.MT5_PASSWORD
        self.server = Config.MT5_SERVER
        self.path = Config.MT5_PATH

    def initialize(self):
        """
        Initializes connection to MT5 terminal.
        """
        logger.info("Initializing MT5...")
        
        init_args = {}
        if self.path:
            init_args['path'] = self.path
            
        if not mt5.initialize(**init_args):
            logger.error(f"MT5 initialization failed, error code = {mt5.last_error()}")
            self.connected = False
            return False

        # Login
        if self.login and self.password and self.server:
            authorized = mt5.login(self.login, password=self.password, server=self.server)
            if authorized:
                logger.info(f"Connected to account #{self.login} on {self.server}")
                self.connected = True
            else:
                logger.error(f"Failed to connect to account #{self.login}, error code: {mt5.last_error()}")
                self.connected = False
        else:
            logger.warning("No login credentials provided. Running in unauthenticated mode (some data might be limited).")
            self.connected = True
        
        return self.connected

    def shutdown(self):
        """
        Shuts down MT5 connection.
        """
        mt5.shutdown()
        self.connected = False
        logger.info("MT5 connection shutdown.")

    def get_rates(self, symbol, timeframe, num_candles=1000):
        """
        Fetches historical rates for a symbol.
        """
        if not self.connected:
            if not self.initialize():
                return None

        # Convert timeframe string to MT5 constant (simplified mapping)
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        
        mt5_tf = tf_map.get(timeframe)
        if not mt5_tf:
            logger.error(f"Invalid timeframe: {timeframe}")
            return None

        # Copy rates
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, num_candles)
        if rates is None:
            logger.error(f"Failed to get rates for {symbol} {timeframe}")
            return None
            
        # Convert to DataFrame and ensure standardized columns
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def check_connection(self):
        """
        Checks if connected, attempts reconnect if not.
        """
        if not mt5.terminal_info():
            logger.warning("Connection lost. Attempting reconnect...")
            return self.initialize()
        return True

    def get_current_price(self, symbol):
        """
        Returns a dict: {'ask': float, 'bid': float, 'time': datetime}
        """
        if not self.check_connection():
            return None
            
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
            
        return {
            'ask': tick.ask,
            'bid': tick.bid,
            'time': datetime.fromtimestamp(tick.time)
        }

    def place_order(self, symbol, order_type, volume, price=None, sl=0.0, tp=0.0, comments="ICT Bot"):
        """
        Places a trade order.
        order_type: "BUY", "SELL", "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"
        """
        self.check_connection()
        
        # Symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol {symbol} not found")
            return None
            
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Symbol {symbol} not visible")
                return None
        
        # Order type mapping
        type_dict = {
            "BUY": mt5.ORDER_TYPE_BUY,
            "SELL": mt5.ORDER_TYPE_SELL,
            "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
            "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
        }
        
        mt5_type = type_dict.get(order_type)
        if mt5_type is None:
            logger.error(f"Invalid order type: {order_type}")
            return None

        # Price handling
        if price is None:
            if order_type == "BUY":
                price = symbol_info.ask
            elif order_type == "SELL":
                price = symbol_info.bid
            else:
                logger.error("Price required for pending orders")
                return None
        
        # Determine correct filling mode
        filling_type = mt5.ORDER_FILLING_FOK
        # Check for IOC (2)
        if symbol_info.filling_mode & 2:
            filling_type = mt5.ORDER_FILLING_IOC
        # Check for FOK (1)
        elif symbol_info.filling_mode & 1:
            filling_type = mt5.ORDER_FILLING_FOK
        else:
            # Fallback for some brokers that don't specify flags correctly or support Return
            filling_type = mt5.ORDER_FILLING_RETURN

        request = {
            "action": mt5.TRADE_ACTION_DEAL if "LIMIT" not in order_type else mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": float(volume),
            "type": mt5_type,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 123456,
            "comment": comments,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.comment} (Code: {result.retcode})")
            return None
            
        logger.info(f"Order placed successfully: {result}")
        return result

    def get_positions(self, symbol=None):
        """
        Returns active positions.
        """
        self.check_connection()
        if symbol:
            return mt5.positions_get(symbol=symbol)
        return mt5.positions_get()

