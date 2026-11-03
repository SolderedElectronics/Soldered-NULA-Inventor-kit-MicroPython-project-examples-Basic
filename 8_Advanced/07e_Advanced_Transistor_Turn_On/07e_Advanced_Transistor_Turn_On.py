"""
@file       07e_Advanced_Transistor_Turn_On.py
@brief      Reports the wiper voltage at which an NPN transistor starts to conduct and the wiper voltage at which
            it saturates, and prints the width of the linear region between them.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

# Same wiring as T21: IO48 feeds the pot, the wiper feeds the base through the 10 kOhm resistor, and four pins
# measure the result.
DRIVE_PIN = 48
SENSE_A_PIN = 4
SENSE_BASE_PIN = 5
SENSE_C_PIN = 6
SENSE_DRIVE_PIN = 7

R_BASE_OHMS = 10000.0

# As in T21: above 3100 mV the bottom of the load resistor is pinned at the ADC ceiling, which means nothing is
# conducting. Below 300 mV on the collector the transistor is saturated.
OFF_THRESHOLD_MV = 3100.0
SATURATED_COLLECTOR_MV = 300.0

drive = Pin(DRIVE_PIN, Pin.OUT)
drive.value(1)

sense_a = ADC(Pin(SENSE_A_PIN), atten=ADC.ATTN_11DB)
sense_base = ADC(Pin(SENSE_BASE_PIN), atten=ADC.ATTN_11DB)
sense_c = ADC(Pin(SENSE_C_PIN), atten=ADC.ATTN_11DB)
sense_drive = ADC(Pin(SENSE_DRIVE_PIN), atten=ADC.ATTN_11DB)

time.sleep_ms(50)

# What has been found in this sweep. Both are cleared when the pot goes back to the off end.
onset_found = False
saturation_found = False
onset_wiper_mv = 0.0


def averaged(adc):
    # The mean of 16 readings. This script only compares voltages, so fewer readings than in T21 are enough, and
    # the pot can be turned a little faster.
    total = 0
    for _ in range(16):
        total += adc.read_uv() // 1000
    return total / 16.0


print()
print("Turn the pot slowly up from the ground end.")

while True:
    v_wiper = averaged(sense_drive)
    v_base = averaged(sense_base)
    v_a = averaged(sense_a)
    v_c = averaged(sense_c)

    transistor_off = v_a > OFF_THRESHOLD_MV

    if transistor_off:
        # Back at the off end, so forget the last sweep and wait for the next one.
        if onset_found:
            print("Back to off. Turn the pot up again to repeat.")
        onset_found = False
        saturation_found = False
    else:
        # The first reading with the transistor no longer off is the moment it starts to conduct.
        if not onset_found:
            onset_found = True
            onset_wiper_mv = v_wiper
            print("Started to conduct at a wiper of {:.0f} mV, with the base at {:.0f} mV".format(v_wiper, v_base))

        # The first reading with the collector pulled low is the moment it saturates.
        if not saturation_found and v_c < SATURATED_COLLECTOR_MV:
            saturation_found = True
            base_ua = ((v_wiper - v_base) / R_BASE_OHMS) * 1000.0
            print("Saturated at a wiper of {:.0f} mV, with {:.1f} uA of base current".format(v_wiper, base_ua))
            print("The linear region was {:.0f} mV of wiper travel wide".format(v_wiper - onset_wiper_mv))

    time.sleep_ms(50)
