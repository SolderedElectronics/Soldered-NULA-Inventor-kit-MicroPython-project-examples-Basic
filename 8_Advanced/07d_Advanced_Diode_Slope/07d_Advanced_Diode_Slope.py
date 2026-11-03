"""
@file       07d_Advanced_Diode_Slope.py
@brief      Remembers the lowest and highest current seen while you turn the pot, and works out the diode's
            slope in millivolts per tenfold change of current, and its ideality factor.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import math
import time

# Same wiring as T20: IO4 reads the anode, IO5 reads the cathode, and the cathode sits on top of the 330 ohm
# resistor.
ANODE_PIN = 4
CATHODE_PIN = 5
R_SENSE_OHMS = 330.0

# Readings the ADC cannot take, as in T20. Above the first the anode pin is pinned, and below the second the
# sense resistor drops too little voltage to measure well.
ADC_CLIP_MV = 3100.0
CURRENT_FLOOR_MA = 0.15

# The thermal voltage at room temperature is about 25.85 mV. It is a physical constant of the silicon, not a
# property of your diode.
THERMAL_VOLTAGE_MV = 25.85

anode = ADC(Pin(ANODE_PIN), atten=ADC.ATTN_11DB)
cathode = ADC(Pin(CATHODE_PIN), atten=ADC.ATTN_11DB)

# The two ends of the sweep so far. have_data stays False until the first good reading arrives.
have_data = False
low_ma = 0.0
low_mv = 0.0
high_ma = 0.0
high_mv = 0.0


def averaged(adc):
    # The mean of 64 readings, as in T20, because one reading is too noisy at the bottom of the sweep.
    total = 0
    for _ in range(64):
        total += adc.read_uv() // 1000
    return total / 64.0


print()
print("Turn the pot slowly from one end to the other.")

while True:
    v_anode_mv = averaged(anode)
    v_cathode_mv = averaged(cathode)

    v_forward_mv = v_anode_mv - v_cathode_mv
    current_ma = v_cathode_mv / R_SENSE_OHMS

    # Throw away the readings the ADC cannot take.
    if v_anode_mv >= ADC_CLIP_MV or current_ma < CURRENT_FLOOR_MA:
        time.sleep_ms(100)
        continue

    # Remember the lowest and the highest current seen so far, together with the forward voltage at each.
    if not have_data or current_ma < low_ma:
        low_ma = current_ma
        low_mv = v_forward_mv
    if not have_data or current_ma > high_ma:
        high_ma = current_ma
        high_mv = v_forward_mv
    have_data = True

    # The slope only means something once the two ends are well apart, so wait until the current has grown threefold.
    if high_ma > low_ma * 3.0:
        decades = math.log10(high_ma / low_ma)
        mv_per_decade = (high_mv - low_mv) / decades
        ideality_factor = mv_per_decade / (THERMAL_VOLTAGE_MV * math.log(10))

        print("from {:.3f} mA to {:.3f} mA: {:.0f} mV per tenfold, ideality factor {:.2f}".format(
            low_ma, high_ma, mv_per_decade, ideality_factor))

    time.sleep_ms(250)
