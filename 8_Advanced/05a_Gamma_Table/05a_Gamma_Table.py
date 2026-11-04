"""
@file       05a_Gamma_Table.py
@brief      Ramps an LED linearly and then through a gamma table so you can compare them back to back.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM
import time

# The LED on IO38 needs a 330 Ohm resistor in series or it will be damaged.
LED_PIN = 38

# 5 kHz is far above what the eye can follow.
PWM_FREQ = 5000

# Vision is roughly logarithmic, so a linear duty ramp spends nearly all its visible change in the bottom twenty
# counts and then appears to stall. Raising the input to the power of 2.2 undoes that.
gamma8 = [int(pow(i / 255.0, 2.2) * 255.0 + 0.5) for i in range(256)]

# Hardware PWM: once running, a timer in the chip generates the waveform and the processor is free.
# duty_u16() only changes the duty cycle, it does not do the switching. MicroPython's duty is 16-bit, 0 to 65535,
# so an 8-bit table value is scaled up by 257 to cover the same range.
led = PWM(Pin(LED_PIN), freq=PWM_FREQ, duty_u16=0)

print("Fade: linear ramp, then gamma-corrected ramp. Watch the LED, not the numbers.")

while True:
    # Even steps of duty. The LED brightens fast and then looks like it stopped, though the duty is still climbing.
    print("linear")
    for duty in range(256):
        led.duty_u16(duty * 257)
        time.sleep_ms(8)
    for duty in range(255, -1, -1):
        led.duty_u16(duty * 257)
        time.sleep_ms(8)

    time.sleep_ms(600)

    # Same step count, same timing, same code. Only the number written to the pin changed.
    print("gamma")
    for i in range(256):
        led.duty_u16(gamma8[i] * 257)
        time.sleep_ms(8)
    for i in range(255, -1, -1):
        led.duty_u16(gamma8[i] * 257)
        time.sleep_ms(8)

    time.sleep_ms(600)
