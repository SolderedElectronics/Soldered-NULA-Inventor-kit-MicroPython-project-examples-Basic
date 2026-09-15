"""
@file       2.2_ADC_Noise_Averaging_And_Calibration.py
@brief      PLOT mode draws one pot three ways at once: raw, a 64-sample mean, and an exponential moving average.
            CALIBRATE mode checks the chip's factory millivolt figure against a two-point calibration you perform.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
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

MODE_PLOT = 0
MODE_CALIBRATE = 1

MODE = MODE_PLOT

MEAN_SAMPLES = 64

# The EMA keeps one number and nudges it towards each reading. Smaller alpha, heavier smoothing, slower response.
EMA_ALPHA = 0.05

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)

# Two-point calibration results, in raw counts, filled in by CALIBRATE mode.
cal_low = 0
cal_high = 4095


def averaged_read(samples=200):
    total = 0
    for _ in range(samples):
        total += pot.read()
    return total // samples


def wait_for_input():
    """Block until the reader sends a line in the console."""
    sys.stdin.readline()


def run_calibration():
    """The chip ships with a factory calibration, which read_uv() uses. This measures your own to compare."""
    global cal_low, cal_high

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


if MODE == MODE_CALIBRATE:
    run_calibration()

ema = 0.0
ema_started = False

while True:
    if MODE == MODE_PLOT:
        """
        Three traces on one graph. Open Thonny's plotter and leave the pot alone: the raw trace is not a line but a
        band about 13 counts wide, and both filtered traces hold to 3. The mean costs 64 reads per answer; the EMA
        gets the same steadiness from one.

        Then turn slowly up towards 3V3. All three traces hit 4095 and the jitter vanishes, which is not the filters
        working. At 11 dB this ADC reaches full scale near 3140 mV and the pot goes on to the rail, so the top slice
        of the travel is clipped and steady and wrong at once. Filters fix noise, not range.
        """
        raw = pot.read()

        total = 0
        for _ in range(MEAN_SAMPLES):
            total += pot.read()
        mean = total // MEAN_SAMPLES

        if not ema_started:
            ema = raw
            ema_started = True
        ema = ema + EMA_ALPHA * (raw - ema)

        print(raw, mean, int(ema))

        time.sleep_ms(20)

    else:
        """
        Turn the knob slowly across the whole travel and watch the gap between the two columns. A two-point fit is a
        straight line through the ends and the ADC is not straight, so they agree at the bottom, bow about 70 mV
        apart near 2500 counts, close again near 3500, and the fit reads high from there. Two points pin down the
        ends and nothing else, which is why the factory calibration uses far more than two.

        The 3300 below is a statement about the pot, not the ADC. The wiper really does reach the rail; the
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

# The ADC draws a little current while it samples, so a high-resistance source reads low and slow. A 10 kOhm pot is
# fine. Example 2.3's photoresistor reaches hundreds of kilohms in the dark, and there it is real.
