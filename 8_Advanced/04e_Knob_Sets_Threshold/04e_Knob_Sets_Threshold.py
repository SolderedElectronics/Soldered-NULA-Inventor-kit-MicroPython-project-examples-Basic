"""
@file       04e_Knob_Sets_Threshold.py
@brief      Calibrates the light range for ten seconds, then switches an LED on the photoresistor with two
            thresholds, where the middle of the two is set by a potentiometer.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

LDR_PIN = 4
POT_PIN = 5
LED_PIN = 38

# How far above and below the knob's setting the light has to move before the LED changes.
HYSTERESIS_PCT = 8

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)
pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
led = Pin(LED_PIN, Pin.OUT)


# Rescales a raw reading from the range low to high onto 0 to 100, and keeps it inside that range.
def to_percent(raw, low, high):
    pct = (raw - low) * 100 // (high - low)
    return max(0, min(100, pct))


# Ten seconds of watching the photoresistor. Returns the lowest and highest readings seen, as a pair.
def calibrate():
    print()
    print("CALIBRATING for 10 seconds. Cover the sensor, then light it up.")

    low = 4095
    high = 0

    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < 10000:
        raw = ldr.read()
        if raw < low:
            low = raw
        if raw > high:
            high = raw
        time.sleep_ms(5)

    # A range of zero would make every later division fail.
    if high - low < 10:
        high = low + 10

    print("Range: {} to {}".format(low, high))
    print()
    return low, high


light_min, light_max = calibrate()
led_on = False

while True:
    # The light as a percentage of the calibrated range, and the knob as a percentage of its whole turn.
    light = to_percent(ldr.read(), light_min, light_max)
    threshold = to_percent(pot.read(), 0, 4095)

    # The same two-threshold rule as T15, centred on wherever the knob is set.
    if not led_on and light > threshold + HYSTERESIS_PCT:
        led_on = True
    elif led_on and light < threshold - HYSTERESIS_PCT:
        led_on = False

    led.value(1 if led_on else 0)

    # Three numbers per line for the plotter: the light, the knob's setting and the LED.
    print(light, threshold, 100 if led_on else 0)

    time.sleep_ms(50)
