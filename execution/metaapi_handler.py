import asyncio
import os
from metaapi_cloud_sdk import MetaApi
from datetime import datetime
import pandas as pd
from execution.base_handler import ExecutionHandler
from config import Config
from utils.logger import setup_logger

logger = setup_logger("MetaApi_Handler")

class MetaApiHandler(ExecutionHandler):
    def __init__(self):
        self.token = os.getenv("METAAPI_TOKEN")
        self.account_id = os.getenv("METAAPI_ACCOUNT_ID")
        self.api = None
        self.account = None
        self.connection = None
        
        # Identify if we need to run our own loop or use existing
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def initialize(self):
        logger.info("Initializing MetaApi...")
        if not self.token or not self.account_id:
            logger.error("MetaApi Token or Account ID missing in .env")
            return False
            
        try:
            return self.loop.run_until_complete(self._async_init())
        except Exception as e:
            logger.error(f"MetaApi Init failed: {e}")
            return False

    async def _async_init(self):
        self.api = MetaApi(self.token)
        self.account = await self.api.metatrader_account_api.get_account(self.account_id)
        
        # Wait for deployment if not deployed
        if self.account.state != 'DEPLOYED':
            logger.info("Account not deployed. Deploying...")
            await self.account.deploy()
        
        logger.info("Waiting for API connection...")
        await self.account.wait_connected()
        self.connection = self.account.get_rpc_connection()
        await self.connection.connect()
        await self.connection.wait_synchronized()
        
        logger.info(f"Connected to MetaApi Account: {self.account.name}")
        return True

    def check_connection(self):
        """Checks if connected to MetaApi."""
        if self.account and self.account.connected:
            return True
        return False

    def shutdown(self):
        if self.connection:
            self.loop.run_until_complete(self.connection.close())
        logger.info("MetaApi Disconnected.")

    def get_rates(self, symbol, timeframe, num_candles=100):
        try:
            return self.loop.run_until_complete(self._get_rates_async(symbol, timeframe, num_candles))
        except Exception as e:
            logger.error(f"Error getting rates: {e}")
            return None

    async def _get_rates_async(self, symbol, timeframe, num_candles):
        # Map timeframe strings
        tf_map = {
            "M1": "1m", "M5": "5m", "M15": "15m", 
            "H1": "1h", "H4": "4h"
        }
        meta_tf = tf_map.get(timeframe, "1h")
        
        # MetaApi uses specific start time logic or 'latest'
        # Getting historical candles
        candles = await self.api.metatrader_account_api.get_historical_candles(
            self.account_id, symbol, meta_tf, limit=num_candles
        )
        
        if not candles:
            return None
            
        # Parse to DataFrame
        data = []
        for c in candles:
            data.append({
                'time': pd.to_datetime(c['time']),
                'open': c['open'],
                'high': c['high'],
                'low': c['low'],
                'close': c['close'],
                'tick_volume': c['tickVolume']
            })
            
        df = pd.DataFrame(data)
        return df

    def get_current_price(self, symbol):
        try:
            return self.loop.run_until_complete(self._get_price_async(symbol))
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            return None

    async def _get_price_async(self, symbol):
        # We can use get_symbol_specification or subscribe
        # For simple check:
        price = await self.connection.get_symbol_price(symbol)
        if price:
            return {
                'ask': price['ask'],
                'bid': price['bid'],
                'time': datetime.now()
            }
        return None

    def place_order(self, symbol, order_type, volume, price=None, sl=0.0, tp=0.0, comments="ICT Bot"):
        try:
            return self.loop.run_until_complete(
                self._place_order_async(symbol, order_type, volume, price, sl, tp, comments)
            )
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return False

    async def _place_order_async(self, symbol, order_type, volume, price, sl, tp, comments):
        # Map Order Types
        op_type = "ORDER_TYPE_BUY" if order_type == "BUY" else "ORDER_TYPE_SELL"
        if "LIMIT" in order_type:
             op_type = "ORDER_TYPE_BUY_LIMIT" if "BUY" in order_type else "ORDER_TYPE_SELL_LIMIT"
        
        trade_req = {
            'actionType': 'ORDER_TYPE_BUY' if order_type == "BUY" else 'ORDER_TYPE_SELL', # simplified for market
            'symbol': symbol,
            'volume': float(volume),
            'stopLoss': float(sl) if sl > 0 else None,
            'takeProfit': float(tp) if tp > 0 else None,
            'comment': comments
        }
        
        # Pending orders need price
        if "LIMIT" in order_type:
             trade_req['actionType'] = op_type
             trade_req['price'] = float(price)

        result = await self.connection.create_market_buy_order(symbol, volume, sl, tp) if order_type == "BUY" else \
                 await self.connection.create_market_sell_order(symbol, volume, sl, tp)

        if result['stringCode'] == 'TRADE_RETCODE_DONE':
            logger.info(f"MetaApi Order Done: {result['orderId']}")
            return True
        else:
            logger.error(f"MetaApi Order Failed: {result}")
            return False

    def get_positions(self, symbol=None):
        # Implementation skipped for brevity, similar async wrapper
        return []
