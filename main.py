import time
import signal
import sys
from config import Config
from utils.logger import setup_logger

from strategies.ict_combined import ICTStrategy

# Initialize Logger
logger = setup_logger("Main")

# Global handler for shutdown
mt5_handler = None

def signal_handler(sig, frame):
    logger.info("Shutdown signal received. Cleaning up...")
    if mt5_handler:
        mt5_handler.shutdown()
    sys.exit(0)

def main():
    global mt5_handler
    
    logger.info("Starting ICT Trading Bot...")
    logger.info(f"Mode: {'DRY RUN' if Config.IS_DRY_RUN else 'LIVE TRADING'}")
    logger.info(f"Symbols: {Config.SYMBOLS}")
    logger.info(f"Execution Mode: {Config.EXECUTION_MODE}")
    
    # Initialize Handler based on Config
    if Config.EXECUTION_MODE == "METAAPI":
        from execution.metaapi_handler import MetaApiHandler
        mt5_handler = MetaApiHandler()
    elif Config.EXECUTION_MODE == "DERIV":
        from execution.deriv_handler import DerivHandler
        mt5_handler = DerivHandler()
    else:
        # Default to Windows Native MT5
        from execution.mt5_handler import MT5Handler
        mt5_handler = MT5Handler()

    if not mt5_handler.initialize():
        logger.critical(f"Failed to initialize {Config.EXECUTION_MODE}. Exiting.")
        return

    # Signal handling for graceful shutdown (VPS friendly)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Bot initialized successfully. Starting main loop...")
    
    try:
        while True:
            # Check connection
            if not mt5_handler.check_connection():
                logger.error("Connection lost in main loop. Retrying in 10s...")
                time.sleep(10)
                continue

            logger.info("Heartbeat: Checking markets...")
            
            # Run Strategy Cycle
            strategy = ICTStrategy(mt5_handler)
            strategy.run_cycle()
            
            # Sleep based on loop interval
            time.sleep(Config.LOOP_INTERVAL)

    except Exception as e:
        logger.exception(f"Unhandled exception in main loop: {e}")
    finally:
        mt5_handler.shutdown()

if __name__ == "__main__":
    main()
