"""
@file       1.3_Night_Light.py
@brief      A night light that fades up as the room gets dark, combining the photoresistor divider from 2.3 with
            the gamma-corrected PWM from 1.2. No new components: everything here has been used before.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin, PWM, ADC
import time

"""
This is the first program in the kit that does a job rather than demonstrating an idea, and it is made entirely of
two you have already built.

  MODE_RAW     brightness straight from the light reading, so you can see why it is not good enough
  MODE_SMOOTH  the same, with the reading averaged and the brightness gamma corrected

The photoresistor divider is exactly the one from 2.3, and the PWM output is exactly the one from 1.2.
"""
MODE_RAW = 0
MODE_SMOOTH = 1

MODE = MODE_SMOOTH

# The divider junction, and the LED. Both are where they were in 2.3 and 1.2, so nothing needs rewiring.
LDR_PIN = 4
LED_PIN = 38

# 5 kHz is far above what the eye can follow. MicroPython's duty_u16 always takes 16 bits, so the 8-bit
# brightness values below are scaled up when they are written.
PWM_FREQ = 5000

# The exponential moving average from 2.2. One number, nudged towards each reading, so the light does not flicker
# when a cloud crosses or someone walks past.
EMA_ALPHA = 0.05
ema = 0.0
ema_started = False

# Calibration results, in raw ADC counts.
light_min = 4095
light_max = 0

# How long the calibration runs for, in milliseconds.
CALIBRATION_MS = 10000

# Vision is roughly logarithmic, so a linear duty ramp spends nearly all its visible change in the bottom twenty
# counts. Raising the input to the power of 2.2 undoes that. Same table as 1.2.
gamma8 = [int(pow(i / 255.0, 2.2) * 255.0 + 0.5) for i in range(256)]

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)
led = PWM(Pin(LED_PIN), freq=PWM_FREQ)


def write_brightness(level8):
    """Take a brightness from 0 to 255 and write it to the pin, which wants 0 to 65535."""
    led.duty_u16(level8 * 257)


def run_calibration():
    """Watch the light for ten seconds and record the darkest and brightest readings this room produces."""
    global light_min, light_max

    print("Calibrating for 10 seconds. Cover the sensor, then light it.")

    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < CALIBRATION_MS:
        raw = ldr.read()
        if raw < light_min:
            light_min = raw
        if raw > light_max:
            light_max = raw
        time.sleep_ms(20)

    print("Range: {} to {} counts.".format(light_min, light_max))

    # A percentage is only meaningful against a range, so refuse to guess from a range that is not there.
    if light_max - light_min < 100:
        print("Range is too narrow to use. Cover the sensor during the calibration, then light it.")


run_calibration()

if MODE == MODE_RAW:
    print("RAW mode: brightness straight from the reading. Watch it twitch.")
else:
    print("SMOOTH mode: reading averaged, brightness gamma corrected.")

while True:
    raw = ldr.read()

    if MODE == MODE_RAW:
        # Straight from the reading to the pin, with no smoothing and no gamma.
        span = max(1, light_max - light_min)
        brightness = int((light_max - raw) * 255 / span)
        brightness = min(255, max(0, brightness))
        write_brightness(brightness)

        print("raw {}  brightness {}".format(raw, brightness))
        time.sleep_ms(50)
        continue

    # The first reading seeds the average, or it would crawl up from zero for the first second.
    if not ema_started:
        ema = float(raw)
        ema_started = True
    ema = ema + EMA_ALPHA * (raw - ema)

    span = max(1, light_max - light_min)
    wanted = int((light_max - ema) * 255 / span)
    wanted = min(255, max(0, wanted))

    # The gamma table turns a number that climbs evenly into a brightness that looks like it climbs evenly.
    write_brightness(gamma8[wanted])

    print("raw {}  ema {:.0f}  wanted {}  written {}".format(raw, ema, wanted, gamma8[wanted]))
    time.sleep_ms(50)
