"""
@file       0.2_Reading_A_Potentiometer.py
@brief      Reads a potentiometer and prints it two ways at once, as raw ADC counts and as millivolts, so Thonny's
            plotter draws both as traces you can watch while you turn the knob.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

# The pin the potentiometer's wiper is on. Turning the knob moves it between 0 V and 3.3 V.
POT_PIN = 4

# How long to wait between readings, in milliseconds. 20 ms gives fifty readings a second.
DELAY_MS = 20

"""
ATTN_11DB is the widest attenuation setting and covers the whole 0 V to 3.3 V swing. On the narrower ones anything
above about 1 V reads full scale and the top of the knob's travel looks flat.
"""
pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)

while True:
    # Raw ADC counts, 0 to 4095. A count, not a voltage: nothing about it says what it was measuring.
    raw = pot.read()

    # The same measurement in microvolts, using calibration figures programmed into the chip at the factory.
    # Divide by 1000 to get millivolts.
    mv = pot.read_uv() // 1000

    # Two numbers on one line separated by a space gives Thonny's plotter two traces.
    print(raw, mv)

    # The plotter autoscales, so leave the pot alone and what fills the window is noise, magnified.
    # Example 2.2 is about that noise and what to do with it.
    time.sleep_ms(DELAY_MS)
