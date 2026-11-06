"""
@file       4.3b_Buzzer_Loudness_From_A_Pot.py
@brief      Drives a passive buzzer through an NPN transistor at one fixed frequency, with a pot setting the duty
            cycle and so the loudness.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM, ADC
import time

"""
IO48 drives the base of the transistor through a 10 kOhm resistor, and the transistor switches the buzzer against
VCC. IO4 reads the pot, the volume knob.

The transistor is here because the pin cannot do this job: it gives a few tens of milliamps, while the coil is a
low resistance that will take as much current as it can get.

The band on the 1N4148 marks the cathode and belongs on the positive side. Fitted the other way round it conducts
all the time and shorts the buzzer out.
"""
DRIVE_PIN = 48
POT_PIN = 4

# The resonant frequency you measured in T17. T26 and T29 want the same number, so it is worth writing on
# the back of the kit box.
RESONANT_HZ = 2700

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
buzzer = PWM(Pin(DRIVE_PIN), freq=1000, duty_u16=0)

print()

"""
The pot maps to 0 to 50 %, not 0 to 100 %, and that upper limit is the interesting part. A 50 % square wave
spends half of every cycle pushing the disc and half letting it go, which is the most movement you can get.
Push the duty higher and the signal approaches a steady level, so the sound falls away.

No filtering on the reading: the pot's dozen counts of jitter is under a tenth of a percent of duty here and
you cannot hear it. Examples that act on a threshold do need averaging.
"""
buzzer.freq(RESONANT_HZ)
buzzer.duty_u16(0)
print("VOLUME: turn the pot. Duty and loudness follow it.")

while True:
    raw = pot.read()

    pct = (raw * 50) // 4095

    # MicroPython's PWM duty is 16-bit, so the percentage is scaled to 0-65535.
    buzzer.duty_u16((pct * 65535) // 100)

    print("duty {} %".format(pct))

    time.sleep_ms(150)
