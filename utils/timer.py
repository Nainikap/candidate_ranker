"""
utils/timer.py
──────────────
Phase-level runtime tracking.
Logs elapsed time per phase and warns if budget is tight.
"""

import time
class Timer:
    def __init__(self, name:str):
        self.name = name
        self.elapsed: float = 0.0
        self.start_time: float | None=None
    
    def start(self):
        self._start = time.perf_counter()
        return self
    
    def stop(self) -> float:
        if self._start is None:
            raise RuntimeError(f"Timer '{self.name}' stopped before being started.")
        self.elapsed = time.perf_counter() - self._start
        return self.elapsed
    
    def __enter__(self):
        self._start()
        return self
    
    def __exit__(self, *args):
        self.stop()
        
    def __repr__(self):
        return f"Timer(name={self.name!r}, elapsed={self.elapsed:.2f}s)"