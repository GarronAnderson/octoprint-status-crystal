import math


class LED:
    """An easy, gamma-corrected way to have some nice looking pulsing LEDs.

    Attributes:
        led (PWMOut): A PWMOut object attached to the LED.
        period (float): The period of the LED in seconds.
        b_max (int): The maximum brightness of the LED, on a scale of 0 to 255.
        b_min (any): The minimum brightness of the LED, on a scale of 0 to 255.

    Methods:
        on(): Set the LED's mode to on. No update call is needed.
        off(): Set the LED's mode to off. No update call is needed.
        pulse(): Set the LED's mode to pulse. Calling `update` is needed to see any effect.
        update(): Uses the timestep given to calculate the new brightness of the LED and applies it.
    """

    MODE_ON = "ON"
    MODE_PULSE = "PULSE"

    def __init__(self, led, period=1.0, b_max=256, b_min=0):
        """Initialize the class.

        Pass a PWMOut object as the only required element. The other values can be set as needed.

        Args:
            led (PWMOut): your PWMOut object goes here
            period (float): Period of the pulsing, in seconds. (default: 1.0)
            b_max (int): Maximum brightness of the LED (also used for what to set the LED to during a call to `on()`.)(default: 256)
            b_min (int): Minimum brightness of the LED (default: 0)

        Returns:
            None.
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
        """Perform gamma correction.

        Get the internal gamma correction of a LED. The gamma correction is by default set to 2.2.

        Args:
            brightness (int): Brightness of the led (0-255).

        Returns:
            int: The gamma corrected brightness
        """
        gamma_brightness = (brightness**self.gamma) * (self.gamma_255)
        return gamma_brightness

    def on(self, brightness=None):
        """Set the LED to on.

        Set the LED to on, using the provided brightness. Defaults to `b_max` if none is given.

        Args:
            brightness (int): Brightness of the LED. (default: uses `b_max`)

        Returns:
            None.
        """
        if brightness is None:
            brightness = self.b_max

        print(f"set pin {self.led} on, brightness = {brightness}")

        self.mode = self.MODE_ON
        self.brightness = brightness
        self.led.duty_cycle = max(
            0, min(65535, round(256 * self._gamma(self.brightness)))
        )

    def off(self):
        """Turn the LED off.

        This function actually sets the LED to on with a brightness of 0.

        Args:
            None.

        Returns:
            None.
        """
        self.on(brightness=0)

    def pulse(self, period=None):
        """Set the LED to pulse.

        This sets the LED to pulse mode and updates the period.

        Args:
            period (float): Period of the pulse. (default: uses the last period)

        Returns:
            None.
        """
        if period is not None:
            self.period = period
        self.mode = self.MODE_PULSE

    def update(self, dt=1.0):
        """Perform an update step.

        Perform an update step given a dt, updating the LED's duty cycle.

        Args:
            dt (float): Dt of the update, in seconds. (default: 1.0)

        Returns:
            None.
        """
        self.time += dt

        if self.mode == self.MODE_PULSE:
            self.brightness = (
                (self.b_max - self.b_min)
                * ((0.5 * math.sin((2 * math.pi * self.time) / self.period)) + 0.5)
            ) + self.b_min

            self.led.duty_cycle = max(
                0, min(65535, round(256 * self._gamma(self.brightness)))
            )
