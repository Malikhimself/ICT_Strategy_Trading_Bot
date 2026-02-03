import pandas as pd
import numpy as np

class SmartMoney:
    def __init__(self, data):
        self.df = data
        
    def find_fvg(self, threshold=0.0001):
        """
        Identifies Fair Value Gaps (Imbalances).
        Bullish FVG: Low of candle (i) > High of candle (i-2)
        Bearish FVG: High of candle (i) < Low of candle (i-2)
        Note: Indices depend on dataframe order. Assuming Ascending time (oldest at 0).
        """
        df = self.df.copy()
        df['fvg_bullish'] = False
        df['fvg_bearish'] = False
        df['fvg_top'] = np.nan
        df['fvg_bottom'] = np.nan
        
        # i is current candle. Gap is between i (Low) and i-2 (High) for Bullish
        # Pandas shifts: shift(1) is previous row. 
        # So using vectorization:
        # Bullish FVG at i-1 (the gap candle): Low[i] > High[i-2]
        
        # Shift logic:
        # We want to label the candle that *created* the FVG, which is usually the middle one in the 3-candle sequence.
        # Let's say we are looking at completed candles.
        # Candle A (i-2), Candle B (i-1), Candle C (i).
        # Bullish Gap: Low(C) > High(A). The FVG is the range [High(A), Low(C)].
        # We mark Candle B (i-1) as the FVG creator.
        
        prev_high = df['high'].shift(2)
        curr_low = df['low']
        
        # Bullish FVG
        bullish_cond = (curr_low > prev_high) & ((curr_low - prev_high) > threshold)
        # Mark the gap on the middle candle (shift(-1) of the condition logic relative to loop, 
        # but here we just find the indices where condition is true (at 'current' C) and map back)
        
        # Actually easier to just iterate for clarity in list of objects, but vector for column marking
        # Using shifts to align:
        # Condition at index i implies gap formed by i, i-1, i-2. 
        # The FVG exists "after" i-1. 
        
        df['is_bullish_fvg'] = (df['low'] > df['high'].shift(2))
        df['is_bearish_fvg'] = (df['high'] < df['low'].shift(2))
        
        return df

    def get_last_fvg(self, n=1):
        """
        Returns the last n FVGs found in the data.
        Returns list of dicts: {'type': 'BULLISH', 'top': float, 'bottom': float, 'time': datetime}
        """
        df = self.find_fvg() # This populates the columns
        
        fvgs = []
        
        # Bullish FVGs
        # Gap is between High(i-2) and Low(i)
        # Note: The "gap" exists on candle (i-1). 
        # So we look for rows where is_bullish_fvg is True (index i).
        # Properties: Top = Low(i), Bottom = High(i-2) given the definition of gap space?
        # Wait, if Bullish: 
        # Candle 1 (Low 100, High 110)
        # Candle 2 (Low 112, High 120) ... huge move up
        # Candle 3 (Low 115, High 125)
        # Gap is between High 1 (110) and Low 3 (115). 
        # So Bottom = High(i-2), Top = Low(i).
        
        # Iterate backwards to find recent ones
        for i in range(len(df)-1, 2, -1):
            if len(fvgs) >= n: break
            
            row = df.iloc[i]
            prev_row_2 = df.iloc[i-2]
            
            if row['is_bullish_fvg']:
                fvgs.append({
                    'type': 'BULLISH',
                    'top': row['low'],
                    'bottom': prev_row_2['high'],
                    'time': df.index[i] if isinstance(df.index, pd.DatetimeIndex) else row.get('time')
                })
            elif row['is_bearish_fvg']:
                # Bearish Gap: Low(i-2) - High(i)
                fvgs.append({
                    'type': 'BEARISH',
                    'top': prev_row_2['low'],
                    'bottom': row['high'],
                    'time': df.index[i] if isinstance(df.index, pd.DatetimeIndex) else row.get('time')
                })
                
        return fvgs

    def find_order_blocks(self):
        """
        Identify potential Order Blocks.
        Bullish OB: The last bearish candle before a strong bullish move that breaks structure (MSS/BMS).
        """
        pass
