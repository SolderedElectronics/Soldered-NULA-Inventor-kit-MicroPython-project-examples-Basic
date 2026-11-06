"""
@file       3.2_Diode_Forward_Voltage.py
@brief      Logs a diode's forward voltage against the current through it while you turn a pot, so you can see
            that the drop is a curve rather than the 0.7 V everybody quotes.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

"""
IO4 reads the voltage on the diode's anode and IO5 the voltage on its cathode, so the difference between the two
readings is the forward voltage. The cathode also sits on top of the sense resistor, so that same reading divided
by the resistance is the current flowing through the diode. The pot varies that current.
"""
ANODE_PIN = 4
CATHODE_PIN = 5

# The sense resistor, in ohms.
R_SENSE_OHMS = 330.0

# ADC1 on this board reaches 4095 counts near 3140 mV, not 3300, so the anode pin runs out of range before the pot
# does. An anode reading this high is a pinned ADC, not a measurement.
ADC_CLIP_MV = 3100.0

# Below this the sense resistor drops less than 50 mV, and this ADC reads about 19 mV low down there.
CURRENT_FLOOR_MA = 0.15

anode = ADC(Pin(ANODE_PIN), atten=ADC.ATTN_11DB)
cathode = ADC(Pin(CATHODE_PIN), atten=ADC.ATTN_11DB)

print()
print("Turn the pot slowly from one end to the other.")
print("Lines starting with # are readings the ADC could not take, not data.")
print("mA,Vf_mV")

"""
Turn the pot from one end to the other over about twenty seconds. Measured on a 1N4148 the sweep runs from 0.154 mA
at 535 mV to 6.281 mA at 715 mV, about 100 mV per decade of current, so the 0.7 V everybody quotes is one point on
a slope at a current somebody else picked. Both ends of the sweep are limited by the ADC rather than the diode,
which is why readings are thrown away there instead of printed.
"""
while True:
    # A single reading carries a few counts of noise, which at the bottom of the sweep is a large slice of the
    # number, so every voltage here is the mean of 64 readings. Each block below adds up 64 readings and divides.

    # First anode reading.
    anode_total = 0
    for _ in range(64):
        anode_total += anode.read_uv() // 1000
    v_anode_first_mv = anode_total / 64.0

    # Cathode reading.
    cathode_total = 0
    for _ in range(64):
        cathode_total += cathode.read_uv() // 1000
    v_cathode_mv = cathode_total / 64.0

    # Second anode reading. The two pins are not read at the same instant and the pot is moving, so an anode reading
    # from either side of the cathode reading, averaged, cancels most of the skew. Without it a fast turn prints a
    # forward voltage that no diode has.
    anode_total_2 = 0
    for _ in range(64):
        anode_total_2 += anode.read_uv() // 1000
    v_anode_second_mv = anode_total_2 / 64.0

    v_anode_mv = (v_anode_first_mv + v_anode_second_mv) / 2.0

    v_forward_mv = v_anode_mv - v_cathode_mv
    current_ma = v_cathode_mv / R_SENSE_OHMS

    # Past this the anode sits above full scale, so the forward voltage silently reads low by however far past it is.
    if v_anode_mv >= ADC_CLIP_MV:
        print("# anode above ADC full scale, back the pot off")
        time.sleep_ms(100)
        continue

    if current_ma < CURRENT_FLOOR_MA:
        time.sleep_ms(100)
        continue

    print("{:.3f},{:.0f}".format(current_ma, v_forward_mv))

    time.sleep_ms(100)
