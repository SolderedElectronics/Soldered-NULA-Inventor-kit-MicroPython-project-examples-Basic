"""
@file       07g_Transistor_Curve_Tracer.py
@brief      Prints a line of comma-separated values ten times a second while you sweep the base drive of an NPN
            transistor with the potentiometer: the wiper, base and collector voltages, the base and collector
            currents, and the region the transistor is working in. Paste the lines into a spreadsheet to plot them.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

# Same wiring as T16: IO48 feeds the pot, the wiper feeds the base through the 10 kOhm resistor, and four pins
# measure the result.
DRIVE_PIN = 48
SENSE_A_PIN = 4
SENSE_BASE_PIN = 5
SENSE_C_PIN = 6
SENSE_DRIVE_PIN = 7

# The two resistors in the circuit, in ohms, and the supply the load branch hangs from, in millivolts.
R_BASE_OHMS = 10000.0
R_LOAD_OHMS = 330.0
VSUPPLY_MV = 3300.0

# As in T16: above 3100 mV the bottom of the load resistor is pinned at the ADC ceiling, which means nothing is
# conducting. Below 300 mV on the collector the transistor is saturated.
OFF_THRESHOLD_MV = 3100.0
SATURATED_COLLECTOR_MV = 300.0

# The pause between lines. The four averaged readings take a few milliseconds more, so a line comes out about
# every 100 ms.
SAMPLE_MS = 100

# Switch the pot's supply on, as in T16.
drive = Pin(DRIVE_PIN, Pin.OUT)
drive.value(1)

sense_a = ADC(Pin(SENSE_A_PIN), atten=ADC.ATTN_11DB)
sense_base = ADC(Pin(SENSE_BASE_PIN), atten=ADC.ATTN_11DB)
sense_c = ADC(Pin(SENSE_C_PIN), atten=ADC.ATTN_11DB)
sense_drive = ADC(Pin(SENSE_DRIVE_PIN), atten=ADC.ATTN_11DB)

time.sleep_ms(50)


def averaged(adc):
    """The mean of 16 readings of one pin, in millivolts. A single reading carries a few counts of noise."""
    total = 0
    for _ in range(16):
        total += adc.read_uv() // 1000
    return total / 16.0


def region_name(load_point_mv, collector_mv):
    """Say which region the transistor is in, from the two voltages that tell: the bottom of the load resistor and
    the collector. Cutoff means nothing flows, saturated means it is fully on, and active is the stretch in between."""
    if load_point_mv > OFF_THRESHOLD_MV:
        return "cutoff"
    if collector_mv < SATURATED_COLLECTOR_MV:
        return "saturated"
    return "active"


# The first line is the column names. A spreadsheet uses it as the titles of the columns.
print("wiper_mV,base_mV,collector_mV,base_uA,collector_mA,region")

while True:
    wiper_mv = averaged(sense_drive)
    base_mv = averaged(sense_base)
    load_point_mv = averaged(sense_a)
    collector_mv = averaged(sense_c)

    # The base current is the voltage across the 10 kOhm resistor divided by its resistance. Millivolts divided by
    # ohms is milliamps, so multiply by 1000 to get microamps.
    base_ua = 0.0
    if wiper_mv > base_mv:
        base_ua = ((wiper_mv - base_mv) / R_BASE_OHMS) * 1000.0

    # The collector current is the current through the 330 Ohm resistor and the LED, which are in series with it.
    # With nothing conducting the reading is stuck at the ADC ceiling, so the current is set to zero instead.
    collector_ma = 0.0
    if load_point_mv <= OFF_THRESHOLD_MV:
        collector_ma = (VSUPPLY_MV - load_point_mv) / R_LOAD_OHMS

    # One line of the table: the values separated by commas, with no spaces.
    print("{:.0f},{:.0f},{:.0f},{:.1f},{:.2f},{}".format(
        wiper_mv, base_mv, collector_mv, base_ua, collector_ma, region_name(load_point_mv, collector_mv)))

    time.sleep_ms(SAMPLE_MS)
