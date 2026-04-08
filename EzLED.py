import math


class LED:

    MODE_ON = "ON"
    MODE_PULSE = "PULSE"

    def __init__(self, led, period=1, b_max=256, b_min=0):
        """
        Pass a PWMOut object as led.

        pulse_freq is in seconds (default 1 second for pulse)
        """
        self.led = led

        self.period = period
        self.b_max = b_max
        self.b_min = b_min

        self.brightness = self.b_min
        self.led.duty_cycle = max(0, min(65535, round(256 * self.brightness)))

        self.time = 0

        self.mode = self.MODE_PULSE

        self.gamma = 2.2
        self.gamma_255 = 255 ** (1 - self.gamma)

    def _gamma(self, brightness):
        gamma_brightness = (brightness**self.gamma) * (self.gamma_255)
        return gamma_brightness

    def on(self, brightness=None):
        if brightness is None:
            brightness = self.b_max

        print(f"set pin {self.led} on, brightness = {brightness}")

        self.mode = self.MODE_ON
        self.brightness = brightness
        self.led.duty_cycle = max(
            0, min(65535, round(256 * self._gamma(self.brightness)))
        )

    def off(self):
        self.on(brightness=0)

    def pulse(self, period=None):
        print("set pin {self.led} to pulse")
        if period is not None:
            self.period = period
        self.mode = self.MODE_PULSE

    def update(self, dt=1.0):
        self.time += dt

        if self.mode == self.MODE_PULSE:
            self.brightness = (
                (self.b_max - self.b_min)
                * ((0.5 * math.sin((2 * math.pi * self.time) / self.period)) + 0.5)
            ) + self.b_min

            self.led.duty_cycle = max(
                0, min(65535, round(256 * self._gamma(self.brightness)))
            )
