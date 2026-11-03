"""
@file       08f_Two_Tone_Alarm.py
@brief      Alternates a passive buzzer between two pitches like a siren, with a pot setting the loudness
            through the duty cycle.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM, ADC
import time

# IO48 drives the base of the transistor through the 10 kOhm resistor, and IO4 reads the pot, the volume knob.
DRIVE_PIN = 48
POT_PIN = 4

# The high pitch is the resonant frequency you measured in T22, where the buzzer is loudest. The low pitch is a
# third lower, which gives the familiar two-tone sound.
HIGH_HZ = 2700
LOW_HZ = 1800

# How long each pitch lasts before it swaps, in milliseconds.
TONE_MS = 400

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
buzzer = PWM(Pin(DRIVE_PIN), freq=HIGH_HZ, duty_u16=0)

high_tone = True
last_switch_ms = time.ticks_ms()

while True:
    # Swap pitch when the time is up.
    if time.ticks_diff(time.ticks_ms(), last_switch_ms) >= TONE_MS:
        last_switch_ms = time.ticks_ms()

        high_tone = not high_tone
        buzzer.freq(HIGH_HZ if high_tone else LOW_HZ)

    # The knob sets the duty from 0 to 50 %, the range in which a bigger duty is a louder sound. Half of 65535 is
    # 32767, so the raw 0-4095 reading is scaled to 0-32767.
    buzzer.duty_u16((pot.read() * 32767) // 4095)

    time.sleep_ms(5)
