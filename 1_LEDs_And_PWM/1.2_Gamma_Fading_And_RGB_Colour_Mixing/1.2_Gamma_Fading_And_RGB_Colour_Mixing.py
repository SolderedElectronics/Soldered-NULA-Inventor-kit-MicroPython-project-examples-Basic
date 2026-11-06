"""
@file       1.2_Gamma_Fading_And_RGB_Colour_Mixing.py
@brief      Ramps an LED linearly and then with a gamma curve so you can compare them back to back.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM
import time

# The LED on IO38 needs a 330 Ohm resistor in series or it will be damaged.
LED_PIN = 38

# 5 kHz is far above what the eye can follow.
PWM_FREQ = 5000

# Hardware PWM: once running, a timer in the chip generates the waveform and the processor is free.
# duty_u16() only changes the duty cycle, it does not do the switching. MicroPython's duty is 16-bit, 0 to 65535,
# so a brightness from 0 to 255 is multiplied by 257 to cover the same range.
led = PWM(Pin(LED_PIN), freq=PWM_FREQ, duty_u16=0)

print("Fade: linear ramp, then gamma-corrected ramp. Watch the LED, not the numbers.")

while True:
    # Even steps of duty. The LED brightens fast and then looks like it stopped, though the duty is still climbing.
    print("linear")

    # Count up from 0 to 255, writing each number straight to the LED.
    for duty in range(256):
        led.duty_u16(duty * 257)
        time.sleep_ms(8)

    # Count back down from 255 to 0.
    for duty in range(255, -1, -1):
        led.duty_u16(duty * 257)
        time.sleep_ms(8)

    time.sleep_ms(600)

    # Same step count, same timing. Only the number written to the LED is bent first.
    # Vision is roughly logarithmic, so the linear ramp spends nearly all its visible change in the bottom twenty
    # counts. Raising the step to the power of 2.2 undoes that.
    print("gamma")

    # Count up from 0 to 255.
    for step in range(256):
        # Turn the step into a fraction between 0 and 1, bend it with the power of 2.2, then scale it back to 0-255.
        # The 0.5 rounds the result to the nearest whole number.
        fraction = step / 255.0
        curved = pow(fraction, 2.2)
        duty = int(curved * 255.0 + 0.5)

        led.duty_u16(duty * 257)
        time.sleep_ms(8)

    # Count back down from 255 to 0, bending each step the same way.
    for step in range(255, -1, -1):
        fraction = step / 255.0
        curved = pow(fraction, 2.2)
        duty = int(curved * 255.0 + 0.5)

        led.duty_u16(duty * 257)
        time.sleep_ms(8)

    time.sleep_ms(600)
