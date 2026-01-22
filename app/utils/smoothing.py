class ExponentialMovingAverage:
    def __init__(self, alpha: float, initial_value: float = 0.0):
        self.alpha = alpha
        self.value = initial_value
        self.initialized = False

    def update(self, new_value: float) -> float:
        if not self.initialized:
            self.value = new_value
            self.initialized = True
        else:
            self.value = self.alpha * new_value + (1 - self.alpha) * self.value
        return self.value
