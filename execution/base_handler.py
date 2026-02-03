from abc import ABC, abstractmethod
import pandas as pd

class ExecutionHandler(ABC):
    """
    Abstract Base Class for Execution Handlers (MT5, MetaApi, Deriv).
    Ensures all handlers return data in a unified format for the strategy.
    """

    @abstractmethod
    def initialize(self) -> bool:
        """Establishes connection to the broker/API."""
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        """Checks if connection is active."""
        pass

    @abstractmethod
    def shutdown(self):
        """Closes connection."""
        pass

    @abstractmethod
    def get_rates(self, symbol: str, timeframe: str, num_candles: int = 100) -> pd.DataFrame:
        """
        Returns a DataFrame with columns: ['time', 'open', 'high', 'low', 'close', 'tick_volume']
        Timeframe strings: "M1", "M5", "M15", "H1", "H4"
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> dict:
        """
        Returns a dict: {'ask': float, 'bid': float, 'time': datetime}
        """
        pass

    @abstractmethod
    def place_order(self, symbol: str, order_type: str, volume: float, price: float = None, sl: float = 0.0, tp: float = 0.0, comments: str = "") -> bool:
        """
        Places an order. 
        order_type: "BUY", "SELL", "BUY_LIMIT", "SELL_LIMIT"
        Returns True if successful.
        """
        pass

    @abstractmethod
    def get_positions(self, symbol: str = None) -> list:
        """
        Returns currently active positions.
        """
        pass
