from collections import deque
from statistics import mean


class TimeWindow:
    def __init__(self, max_length: int):
        self.values = deque(maxlen=max_length)

    def push(self, value: float) -> None:
        self.values.append(value)

    def is_ready(self) -> bool:
        return len(self.values) == self.values.maxlen

    def average(self) -> float:
        if not self.values:
            return 0.0
        return mean(self.values)

    def latest(self) -> float:
        if not self.values:
            return 0.0
        return self.values[-1]

