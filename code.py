# Octoprint Status Lamp Controller
# Garron Anderson, 2025


import os
import random
import time

import adafruit_connection_manager
import adafruit_requests
import board
import pwmio
import wifi
from analogio import AnalogIn

from EzLED import LED

# === USER INPUT AND SETUP ===

POLL_FREQUENCY = 10  # seconds

BRIGHT_MAX = 255  # 0 to 255
BRIGHT_MIN = 100

DIM_MAX = 100
DIM_MIN = 40

BRIGHTNESS_THRESHOLD = 0.3  # from 0 (dark) to 1 (bright)

TEMP_TOLERANCE = 5  # deg C, if you're within this number, you're at temperature

ROOM_TEMP = 50  # deg C, if you're under this, you're done cooling

FINISHED_TIMER = 5  # minutes, how long to indicate finished for
ERROR_DURATION = 60  # seconds, if the print_time_left doesn't change for this long, assume we're stuck

OCTOPRINT_URL = "http://octoprint.local"

# === END USER INPUT ===

_time_print_finished = 0
_was_printing = False
_last_print_time_left = 0
_error_counter = 0


def get_status():
    """Get printer status.

    Gets the status of the printer from OctoPrint.

    Args:
        None.

    Returns:
        str: The status as a string (this avoids magic numbers).
    """
    global _time_print_finished, _was_printing, _last_print_time_left, _error_counter

    try:
        with requests.get(
            OCTOPRINT_URL + "/api/printer",
            headers={"X-Api-Key": os.getenv("OCTOPRINT_API_KEY")},
        ) as printer_request:
            status = printer_request.json()
            try:
                status_flags = status["state"]["flags"]
            except KeyError:  # this means we're in an error state
                return ERROR
    except Exception as e:
        if e.errno == -2:  # it's a gaierror, we can't find the printer
            return CONN_ERROR
        else:
            raise e  # go ahead and crash

    with requests.get(
        OCTOPRINT_URL + "/api/job",
        headers={"X-Api-Key": os.getenv("OCTOPRINT_API_KEY")},
    ) as job_request:
        job_status = job_request.json()

    if (
        status_flags.get("error")
        or status_flags.get("cancelling")
        or status_flags.get("closedOrError")
    ):
        return ERROR

    if status_flags.get("paused") or status_flags.get("pausing"):
        return PAUSED

    if status_flags.get("operational"):
        # okay, we're not in an error or paused
        # so check heat/cool
        temp_target = status["temperature"]["tool0"]["target"]
        temp_now = status["temperature"]["tool0"]["actual"]

        if (_was_printing and not status_flags.get("printing")) or (
            status_flags.get("finishing")
        ):
            # we were printing, and now we're not, so therefore set the finished timer
            _was_printing = False
            _time_print_finished = time.time()

        if _time_print_finished and (time.time() - _time_print_finished) < (
            FINISHED_TIMER * 60
        ):  # but first check the timer
            # just finished a print
            return FINISHED

        # cooling is a target of 0 and temperature greater than ROOM_TEMP
        if temp_target == 0 and temp_now > ROOM_TEMP:
            return COOLING
        # heating is printing status, but with an unmet temperature tolerance
        if (temp_target != 0 and temp_now > ROOM_TEMP) and abs(
            temp_now - temp_target
        ) > TEMP_TOLERANCE:
            return HEATING

        if (
            _time_print_finished
            and (time.time() - _time_print_finished) < FINISHED_TIMER
        ):
            # just finished a print
            return FINISHED

        if status_flags.get("printing"):
            # we aren't errored, heating, or cooling, so must be printing
            _was_printing = True
            # but if remaining print time didn't change for 30 secs, we're errored
            print_time_left = job_status["progress"]["printTimeLeft"]
            if _last_print_time_left == print_time_left:
                _error_counter = _error_counter + 1
                # so we bumped the error counter up, did we hit threshold?
                if _error_counter >= (ERROR_DURATION // POLL_FREQUENCY):
                    return ERROR  # we hit threshold, error
                else:  # we're still printing
                    return PRINTING
            else:  # the print time moved
                _error_counter = 0
                _last_print_time_left = print_time_left
                return PRINTING

        # nothing exciting happened
        return IDLE


# LED Setup

raw_red = pwmio.PWMOut(board.GP2)
raw_grn = pwmio.PWMOut(board.GP3)
raw_ylw = pwmio.PWMOut(board.GP4)
raw_wht = pwmio.PWMOut(board.GP5)
raw_blu = pwmio.PWMOut(board.GP6)

raw_LEDs = [raw_red, raw_grn, raw_ylw, raw_wht, raw_blu]

for led in raw_LEDs:
    led.duty_cycle = 0

red = LED(raw_red)
grn = LED(raw_grn)
ylw = LED(raw_ylw)
wht = LED(raw_wht)
blu = LED(raw_blu)

LEDs = [red, grn, wht, ylw, blu]

for led in LEDs:
    led.b_max = BRIGHT_MAX
    led.b_min = BRIGHT_MIN
    led.period = 5 + random.uniform(0, 0.4)

grn.b_max = 255
grn.b_min = 50

light_sensor = AnalogIn(board.A1)

# WiFi setup
try:
    wifi.radio.connect(
        ssid=os.getenv("CIRCUITPY_WIFI_SSID"),
        password=os.getenv("CIRCUITPY_WIFI_PASSWORD"),
    )

    pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
    requests = adafruit_requests.Session(pool)
except:
    for led in LEDs:
        led.off()
    red.pulse(period=0.5)
    blu.pulse(period=0.5)
    last_led = time.monotonic()
    while True:
        # update LED animations
        time_now = time.monotonic()
        dt = time_now - last_led
        for led in LEDs:
            led.update(dt)
        last_led = time_now

# Modes
BRIGHT = "BRIGHT"
DIM = "DIM"

IDLE = "IDLE"
ERROR = "ERROR"
CONN_ERROR = "CONN_ERROR"
PAUSED = "PAUSED"
PRINTING = "PRINTING"
HEATING = "HEATING"
COOLING = "COOLING"
FINISHED = "FINISHED"

last_poll = 0
last_led = time.monotonic()

# set initial status
brightness = BRIGHT
status = IDLE
new_status = IDLE

mode = 0

while True:
    if (time.monotonic() - last_poll) > POLL_FREQUENCY:  # poll octoprint
        last_poll = time.monotonic()
        new_status = get_status()

    # update LED animations
    time_now = time.monotonic()
    dt = time_now - last_led

    dt = min(
        dt, 0.05
    )  # without this, an OctoPrint check would cause a large dt, making the brightness jump. Bit hacky but works.

    for led in LEDs:
        led.update(dt)
    last_led = time_now

    # update LED brightness
    brightness_reading = light_sensor.value / 65536
    if brightness_reading > BRIGHTNESS_THRESHOLD:  # bright mode
        new_brightness = BRIGHT
    else:
        new_brightness = DIM

    if new_brightness != brightness:
        print(f"resetting brightness to {new_brightness}")
        for led in LEDs:
            if new_brightness == BRIGHT:
                led.b_max = BRIGHT_MAX
                led.b_min = BRIGHT_MIN
            else:
                led.b_max = DIM_MAX
                led.b_min = DIM_MIN
            # green gets an override
            grn.b_max = 255
            grn.b_min = 50

        brightness = new_brightness

    # update LED colors
    status_changed = status != new_status
    if status_changed:
        print(f"printer status changed to {new_status}")
        if new_status == IDLE:
            for led in LEDs:
                led.pulse(period=5 + random.uniform(0, 0.4))

        elif new_status == ERROR:
            for led in LEDs:
                led.off()
            red.pulse(period=2)

        elif new_status == CONN_ERROR:
            for led in LEDs:
                led.off()
            red.pulse(period=2)
            blu.pulse(period=1.9)

        elif new_status == PRINTING:
            for led in LEDs:
                led.off()
            grn.on()
            wht.pulse(period=3)

        elif new_status == HEATING:
            for led in LEDs:
                led.off()
            grn.on()
            ylw.pulse(period=3)

        elif new_status == COOLING:
            for led in LEDs:
                led.off()
            grn.on()
            blu.pulse(period=3)

        elif new_status == FINISHED:
            for led in LEDs:
                led.pulse(period=0.5 + random.uniform(0, 0.5))

        elif new_status == PAUSED:
            for led in LEDs:
                led.off()
            red.pulse(period=2)
            ylw.pulse(period=2)

        status = new_status
