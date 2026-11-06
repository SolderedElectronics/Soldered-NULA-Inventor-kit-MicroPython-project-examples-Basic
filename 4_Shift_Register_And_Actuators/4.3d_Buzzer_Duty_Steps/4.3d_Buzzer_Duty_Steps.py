"""
@file       4.3d_Buzzer_Duty_Steps.py
@brief      Holds a passive buzzer at its resonant frequency and steps the duty cycle through 5, 10, 25 and 50 %.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM
import time

# IO48 drives the base of the transistor through a 10 kOhm resistor, as before.
DRIVE_PIN = 48

# The resonant frequency you measured in T17.
RESONANT_HZ = 2700

buzzer = PWM(Pin(DRIVE_PIN), freq=1000, duty_u16=0)

print()

# Frequency decides the pitch; duty decides how long the coil is energised each cycle, so roughly how hard
# the disc is pushed. It gets louder as the duty rises, and the transistor gets warmer with it.
buzzer.freq(RESONANT_HZ)

# MicroPython's PWM duty is 16-bit, so each percentage is scaled to 0-65535: 5 % is 3276, 10 % is 6553,
# 25 % is 16383 and 50 % is 32767.
while True:
    print("duty {} %".format(5))
    buzzer.duty_u16(3276)
    time.sleep_ms(1500)

    print("duty {} %".format(10))
    buzzer.duty_u16(6553)
    time.sleep_ms(1500)

    print("duty {} %".format(25))
    buzzer.duty_u16(16383)
    time.sleep_ms(1500)

    print("duty {} %".format(50))
    buzzer.duty_u16(32767)
    time.sleep_ms(1500)

    # Stop it with a duty of zero, not a level on the pin. A steady level is the silent case from the first
    # script, and it draws current through the coil until something gets warm.
    buzzer.duty_u16(0)
    time.sleep_ms(1500)
