"""
@file       04a_Calibration_Helper_Functions.py
@brief      Checks the chip's factory millivolt figure against a two-point calibration you perform: turn the pot to each
            end, then compare your millivolts with the chip's while you turn it across the travel.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import sys
import time

"""
Every analog pin in this kit is IO4 to IO10, and that is not a style choice. IO11 upwards are ADC2 pins, and ADC2
shares hardware with the radio: the moment Wi-Fi starts, a read on one stops returning anything useful.
Section 7 turns Wi-Fi on. IO8 and IO9 are ADC1 but carry the Qwiic bus, so the usable set is IO4-IO7 and IO10.
"""
POT_PIN = 4

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)


def averaged_read(samples=200):
    """Average a batch of readings, so one noisy sample cannot spoil a calibration point."""
    total = 0
    for _ in range(samples):
        total += pot.read()
    return total // samples


def wait_for_input():
    """Block until the reader sends a line in the console."""
    sys.stdin.readline()


# The chip ships with a factory calibration, which read_uv() uses. This measures your own to compare.
print()
print("CALIBRATION")
print("Turn the pot fully towards GND, then press Enter.")
wait_for_input()
cal_low = averaged_read()
print("  low point: {} counts, factory says {} mV".format(cal_low, pot.read_uv() // 1000))

print("Now turn it fully towards 3V3, then press Enter.")
wait_for_input()
cal_high = averaged_read()
print("  high point: {} counts, factory says {} mV".format(cal_high, pot.read_uv() // 1000))

# Some pots turn the other way. Without this swap a negative span maps the line backwards and inverts
# everything.
if cal_low > cal_high:
    cal_low, cal_high = cal_high, cal_low
    print("  (endpoints swapped: this pot turns the other way)")

print()
print("counts | your calibration | factory calibration")

while True:
    """
    Turn the knob slowly across the whole travel and watch the gap between the two columns. A two-point fit is a
    straight line through the ends and the ADC is not straight, so they agree at the bottom, bow about 70 mV
    apart near 2500 counts, close again near 3500, and the fit reads high from there. Two points pin down the
    ends and nothing else, which is why the factory calibration uses far more than two.

    The 3300 below is a statement about the pot, not the ADC. The wiper really does reach 3.3 V; the
    converter clips near 3140 mV and cannot see it.
    """
    raw = pot.read()
    factory_mv = pot.read_uv() // 1000

    # Guard against a division by zero if the calibration was run without turning the pot.
    span = cal_high - cal_low
    if span == 0:
        span = 1
    your_mv = (raw - cal_low) * 3300.0 / span

    print(raw, int(your_mv), factory_mv)

    time.sleep_ms(100)
