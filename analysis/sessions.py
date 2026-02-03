from datetime import datetime, time
import pytz

class SessionManager:
    def __init__(self, timezone="Etc/UTC"):
        self.timezone = pytz.timezone(timezone)
        
        # Killzones in NY Time (EST/EDT)
        # We need to handle UTC conversion dynamically
        # Standard ICT times (NY Local):
        self.london_open_start = time(2, 0) # 2:00 AM NY
        self.london_open_end = time(5, 0)   # 5:00 AM NY
        
        self.ny_open_start = time(7, 0)     # 7:00 AM NY
        self.ny_open_end = time(10, 0)      # 10:00 AM NY
        
        self.silver_bullet_am_start = time(10, 0)
        self.silver_bullet_am_end = time(11, 0)

    def is_in_killzone(self, current_dt):
        """
        Checks if current time is within any Killzone.
        current_dt: datetime object (must be timezone aware or match config tz)
        """
        # Convert current_dt to NY time for checking
        ny_tz = pytz.timezone('America/New_York')
        ny_time = current_dt.astimezone(ny_tz).time()
        
        if self.london_open_start <= ny_time <= self.london_open_end:
            return "LONDON_OPEN"
        if self.ny_open_start <= ny_time <= self.ny_open_end:
            return "NY_OPEN"
        if self.silver_bullet_am_start <= ny_time <= self.silver_bullet_am_end:
            return "SILVER_BULLET_AM"
            
        return None
