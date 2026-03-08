import numpy as np
from datetime import datetime, UTC, timedelta

class TimeGrid:
    def __init__(self):
        pass

    def create_time_grid(self, end_time_hours: int, step_seconds: int) -> np.array:

        # Get current time UTC
        current_time = datetime.now(UTC)
            
        end_time = current_time + timedelta(hours=end_time_hours)
        step = timedelta(seconds=step_seconds)

        Timestamp = []
        current = current_time
        while current <= end_time:
            Timestamp.append(current)
            current += step
        
        timestamps_np = np.array(Timestamp, dtype=object)
        return timestamps_np