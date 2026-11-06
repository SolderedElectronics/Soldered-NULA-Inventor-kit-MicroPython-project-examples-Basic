"""
@file       4.3_Driving_A_Buzzer_Through_A_Transistor.py
@brief      Drives a passive buzzer through an NPN transistor from the + row, with a flyback diode.
            Sweeps 500 Hz to 5 kHz so you can hear where its resonance is.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM
import time

"""
IO48 drives the base of the transistor through a 10 kOhm resistor, and the transistor switches the buzzer against
VCC.

The transistor is here because the pin cannot do this job: it gives a few tens of milliamps, while the coil is a
low resistance that will take as much current as it can get.

The band on the 1N4148 marks the cathode and belongs on the positive side. Fitted the other way round it conducts
all the time and shorts the buzzer out.
"""
DRIVE_PIN = 48

buzzer = PWM(Pin(DRIVE_PIN), freq=1000, duty_u16=0)

print()

"""
Listen rather than watch. Somewhere in the range the buzzer gets dramatically louder over a span of a few
hundred hertz, then drops back. That peak is mechanical resonance: driving the disc at its natural frequency
makes each push land in step with the movement already happening.

Write the frequency down. Two buzzers from the same batch will not peak at quite the same place.
"""
while True:
    print("sweeping 500 Hz to 5000 Hz over 20 seconds")

    for hz in range(500, 5001, 25):
        buzzer.freq(hz)
        buzzer.duty_u16(32768)  # 50 %, half of 65535
        print(hz)
        time.sleep_ms(110)

    buzzer.duty_u16(0)
    print("done")
    time.sleep_ms(3000)
