"""Retry helper with exponential backoff and full jitter."""

import random
import time


def retry_with_backoff(fn, attempts=5, base_delay=0.2, max_delay=10.0):
    for attempt in range(attempts):
        try:
            return fn()
        except Exception:
            if attempt == attempts - 1:
                raise
            delay = min(max_delay, base_delay * 2**attempt)
            time.sleep(random.uniform(0, delay))
