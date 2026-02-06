from config import Config
from execution.base_handler import ExecutionHandler
from analysis.market_structure import MarketStructure

from analysis.smart_money import SmartMoney
from analysis.sessions import SessionManager
from utils.logger import setup_logger
from utils.telegram_handler import TelegramHandler
import pandas as pd
from datetime import datetime

logger = setup_logger("ICT_Strategy")

class ICTStrategy:
    def __init__(self, execution_handler: ExecutionHandler):
        self.mt5 = execution_handler
        self.session_manager = SessionManager(timezone=Config.TIMEZONE)
        self.telegram = TelegramHandler()
        self.symbols = Config.SYMBOLS
        
        # State tracking per symbol
        self.state = {symbol: {"bias": "NEUTRAL", "key_levels": []} for symbol in self.symbols}

    def run_cycle(self):
        """
        Main execution cycle called by the loop.
        """
        for symbol in self.symbols:
            try:
                self.analyze_symbol(symbol)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")

    def analyze_symbol(self, symbol):
        """
        Performs multi-timeframe analysis for a single symbol.
        Step 1: H4 Structure (Bias)
        Step 2: H1 Key Levels
        Step 3: M15 Confirmation
        Step 4: M5 Entry
        """
        # --- Step 1: H4 Structure ---
        h4_rates = self.mt5.get_rates(symbol, "H4", num_candles=200)
        if h4_rates is None: return

        df_h4 = pd.DataFrame(h4_rates)
        ms_h4 = MarketStructure(df_h4)
        ms_h4.identify_swings()
        bias = ms_h4.determine_trend()
        
        self.state[symbol]["bias"] = bias
        logger.debug(f"{symbol} H4 Bias: {bias}")
        
        if bias == "NEUTRAL":
            return # No clear trend, skip

        # --- Step 2: H1 Key Levels & Sessions ---
        # Check if in session
        current_dt = datetime.now().astimezone()
        session_status = self.session_manager.is_in_killzone(current_dt)
        if not session_status:
            logger.info(f"{symbol} not in killzone. Skipping.")
            return

        # --- Step 3: M15 Confirmation (MSS) ---
        m15_rates = self.mt5.get_rates(symbol, "M15", num_candles=100)
        if m15_rates is None: return
        
        df_m15 = pd.DataFrame(m15_rates)
        ms_m15 = MarketStructure(df_m15)
        # Check recent swings to see if structure aligns with Bias
        # Simplified: If H4 Bullish, M15 should ideally be Bullish OR shifting Bullish
        
        # --- Step 4: M5 Entry ---
        # Look for FVG on M5 if direction aligns
        m5_rates = self.mt5.get_rates(symbol, "M5", num_candles=100)
        if m5_rates is None: return
        
        df_m5 = pd.DataFrame(m5_rates)
        sm_m5 = SmartMoney(df_m5)
        recent_fvgs = sm_m5.get_last_fvg(n=1)
        
        if not recent_fvgs: return
        
        fvg = recent_fvgs[0]
        
        # Entry Logic
        # Use real-time tick for execution price instead of M1 candle close
        tick_info = self.mt5.get_current_price(symbol)
        if tick_info is None: return
        
        current_price = tick_info['ask'] if bias == "BULLISH" else tick_info['bid']
        
        if bias == "BULLISH" and fvg['type'] == 'BULLISH':
            # Check if price is near/in FVG
            # Limit entry at Top of FVG, or Market if inside
            if fvg['bottom'] <= current_price <= fvg['top'] * 1.0005: 
                # Slightly above top is ok for immediate rebalance
                logger.info(f"FOUND BUY SETUP: {symbol} in {session_status}. FVG: {fvg}")
                self.execute_trade(symbol, "BUY", stop_loss=fvg['bottom'])
                
        elif bias == "BEARISH" and fvg['type'] == 'BEARISH':
            if fvg['bottom'] * 0.9995 <= current_price <= fvg['top']:
                logger.info(f"FOUND SELL SETUP: {symbol} in {session_status}. FVG: {fvg}")
                self.execute_trade(symbol, "SELL", stop_loss=fvg['top'])

    def execute_trade(self, symbol, direction, stop_loss):
        """
        Executes trade with risk management calculations.
        """
        # Check existing positions first
        positions = self.mt5.get_positions(symbol=symbol)
        if positions and len(positions) > 0:
            return # Already in a trade
            
        # Calculate Volume based on Risk
        # Simplified: Fixed 0.01 or derive from config
        volume = 0.01 # Placeholder for simple risk calc
        
        # Get Current Price via Handler
        tick = self.mt5.get_current_price(symbol)
        if tick is None:
            logger.error(f"Could not get tick for {symbol}")
            return

        current_price = tick['ask'] if direction == "BUY" else tick['bid']
        
        # Calc TP (1:2 RR)
        dist = abs(current_price - stop_loss)
        if dist == 0: return
        
        tp = current_price + (dist * 2) if direction == "BUY" else current_price - (dist * 2)
        
        logger.info(f"Placing {direction} on {symbol} @ {current_price}, SL: {stop_loss}, TP: {tp}")
        
        if not Config.IS_DRY_RUN:
            result = self.mt5.place_order(symbol, direction, volume, sl=stop_loss, tp=tp)
            # Result bool check depends on handler
            if result:
                self.telegram.send_trade_alert(symbol, direction, current_price, stop_loss, tp)
        else:
            logger.info("DRY RUN: Order NOT sent to broker.")
            # Send alert for Dry Run too, but mark as Dry Run?
            # User wants signals, so maybe yes.
            self.telegram.send_trade_alert(symbol, direction, current_price, stop_loss, tp, strategy_name="ICT Setup (Dry Run)")

