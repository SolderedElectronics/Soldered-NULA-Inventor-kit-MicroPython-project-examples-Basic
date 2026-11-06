"""
@file       4.3c_Buzzer_Held_Steady.py
@brief      Drives the pin of a passive buzzer's transistor steadily high, to show that a steady voltage makes no sound.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

# IO48 drives the base of the transistor through a 10 kOhm resistor, as before.
DRIVE_PIN = 48

print()

# A passive buzzer is a coil and a metal disc with no oscillator inside, so it needs an alternating signal. A
# steady high pushes the disc once and holds it: a faint click, then silence, with current flowing throughout.
drive = Pin(DRIVE_PIN, Pin.OUT)
drive.value(1)
print("LEVEL: a steady HIGH. Silence, and current flowing. Do not leave this running.")

while True:
    time.sleep_ms(1000)
