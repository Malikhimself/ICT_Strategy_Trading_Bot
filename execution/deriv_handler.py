import asyncio
import json
import websockets
import pandas as pd
from datetime import datetime
from execution.base_handler import ExecutionHandler
from config import Config
from utils.logger import setup_logger

logger = setup_logger("Deriv_Handler")

class DerivHandler(ExecutionHandler):
    def __init__(self):
        self.app_id = Config.DERIV_APP_ID
        self.token = Config.DERIV_TOKEN
        self.ws_url = f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}"
        self.ws = None
        
        # Async interactions need a running loop managed by this class
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
        self.is_authorized = False

    def initialize(self):
        """Connects and Authenticates."""
        logger.info("Initializing Deriv Connection...")
        if not self.token:
            logger.error("Deriv Token missing in .env")
            return False
            
        return self.loop.run_until_complete(self._connect_and_auth())

    async def _connect_and_auth(self):
        try:
            self.ws = await websockets.connect(self.ws_url)
            
            # Authorize
            auth_req = {"authorize": self.token}
            await self.ws.send(json.dumps(auth_req))
            resp = json.loads(await self.ws.recv())
            
            if "error" in resp:
                logger.error(f"Deriv Auth Failed: {resp['error']['message']}")
                self.is_authorized = False
                return False
                
            logger.info(f"Deriv Connected & Authorized. Account: {resp['authorize']['loginid']}")
            self.is_authorized = True
            return True
        except Exception as e:
            logger.error(f"Deriv Connection Exception: {e}")
            return False

    def shutdown(self):
        if self.ws:
            self.loop.run_until_complete(self.ws.close())
        logger.info("Deriv Disconnected.")

    def check_connection(self):
        if self.ws and self.ws.open and self.is_authorized:
            return True
        return False

    def get_rates(self, symbol, timeframe, num_candles=100):
        try:
            return self.loop.run_until_complete(self._get_candles_async(symbol, timeframe, num_candles))
        except Exception as e:
            logger.error(f"Deriv get_rates error: {e}")
            return None

    async def _get_candles_async(self, symbol, timeframe, num_candles):
        # Map timeframes to seconds for granularity
        # M1=60, M5=300, M15=900, H1=3600, H4=14400 (Deriv supports these)
        tf_map = {
            "M1": 60, "M5": 300, "M15": 900, "H1": 3600, "H4": 14400, "D1": 86400
        }
        granularity = tf_map.get(timeframe, 3600)
        
        req = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": num_candles,
            "end": "latest",
            "start": 1,
            "style": "candles",
            "granularity": granularity
        }
        
        await self.ws.send(json.dumps(req))
        resp = json.loads(await self.ws.recv())
        
        if "error" in resp:
            logger.error(f"Error fetching candles: {resp['error']['message']}")
            return None
            
        candles = resp.get("candles", [])
        if not candles:
            return None
            
        # Parse to DataFrame
        data = []
        for c in candles:
            data.append({
                'time': pd.to_datetime(c['epoch'], unit='s'),
                'open': float(c['open']),
                'high': float(c['high']),
                'low': float(c['low']),
                'close': float(c['close']),
                'tick_volume': 0 # Deriv API doesn't always provide vol in generic candles
            })
            
        return pd.DataFrame(data)

    def get_current_price(self, symbol):
        try:
            return self.loop.run_until_complete(self._get_price_async(symbol))
        except Exception as e:
            logger.error(f"Deriv get_price error: {e}")
            return None

    async def _get_price_async(self, symbol):
        # We can use 'price_proposal' or just 'ticks' for latest
        req = {
            "ticks": symbol
        }
        # Note: This subscribes to a stream if we aren't careful, but we just want one tick.
        # However, Deriv 'ticks' without 'subscribe' is not standard request-response for one tick usually? 
        # Actually 'ticks_history' with count=1 is safer for snapshot.
        
        req = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": 1,
            "end": "latest",
            "style": "ticks"
        }
        
        await self.ws.send(json.dumps(req))
        resp = json.loads(await self.ws.recv())
        
        if "history" in resp and "prices" in resp["history"] and len(resp["history"]["prices"]) > 0:
            price = float(resp["history"]["prices"][-1])
            epoch = resp["history"]["times"][-1]
            return {
                'ask': price, # Deriv ticks often just singular, simplified here
                'bid': price,
                'time': datetime.fromtimestamp(epoch)
            }
        return None

    def place_order(self, symbol, order_type, volume, price=None, sl=0.0, tp=0.0, comments="ICT Bot"):
        """
        Placing orders on Deriv is tricky via API without specifying contract types (CALL/PUT/MULTIPLIER).
        Assuming 'Multiplier' implementation for FX-like trading (SL/TP support).
        """
        try:
            return self.loop.run_until_complete(self._place_trade_async(symbol, order_type, volume, sl, tp))
        except Exception as e:
            logger.error(f"Deriv Order Error: {e}")
            return False
            
    async def _place_trade_async(self, symbol, order_type, volume, sl, tp):
        # NOTE: This implementation assumes "Multipliers" logic for FX pairs on Deriv
        # Contract type: "MULTUP" (Buy/Long) or "MULTDOWN" (Sell/Short)
        
        contract_type = "MULTUP" if order_type == "BUY" else "MULTDOWN"
        
        # Proposal Request
        proposal_req = {
            "proposal": 1,
            "amount": float(volume), # Stake amount
            "basis": "stake",
            "contract_type": contract_type,
            "currency": "USD", # Assuming USD account
            "symbol": symbol,
            "multiplier": 100 # simplified multiplier, configurable?
        }
        
        # Add Limit Order params to proposal if supported, 
        # usually passed in 'buy' or proposal.
        # For simplicity, we get proposal then buy.
        
        await self.ws.send(json.dumps(proposal_req))
        res = json.loads(await self.ws.recv())
        
        if "error" in res:
             logger.error(f"Proposal Error: {res['error']['message']}")
             return False
             
        proposal_id = res['proposal']['id']
        
        # Execute Buy
        buy_req = {
            "buy": proposal_id,
            "price": res['proposal']['ask_price'],
        }
        
        # If SL/TP supported in buy request for Multipliers (limit_order parameter)
        if sl > 0 or tp > 0:
            buy_req["parameters"] = {
                "take_profit": {"amount": abs(tp - float(res['proposal']['ask_price']))} if tp > 0 else None,
                 # SL logic differs for multipliers (stop_loss amount, not price level usually)
                 # Simplified placeholder. Deriv specific logic required for precise price SL.
            }

        await self.ws.send(json.dumps(buy_req))
        buy_res = json.loads(await self.ws.recv())
        
        if "error" in buy_res:
            logger.error(f"Buy Error: {buy_res['error']['message']}")
            return False
            
        logger.info(f"Deriv Trade Executed: {buy_res['buy']['contract_id']}")
        return True

    def get_positions(self, symbol=None):
        return []
