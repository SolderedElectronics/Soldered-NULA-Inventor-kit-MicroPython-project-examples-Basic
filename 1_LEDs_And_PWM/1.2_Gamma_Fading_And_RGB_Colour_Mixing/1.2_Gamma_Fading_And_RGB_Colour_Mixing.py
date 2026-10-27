"""
@file       1.2_Gamma_Fading_And_RGB_Colour_Mixing.py
@brief      FADE mode ramps an LED linearly and then through a gamma table so you can compare them back to back.
            COLOUR mode drives the onboard WS2812B from one pot feeding the hue.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM, ADC
import neopixel
import time

"""
Pick a mode and run.

  MODE_FADE    ramps one LED on IO38 linearly, then through the gamma table, so you can compare them back to back
  MODE_COLOUR  reads one pot on IO4 as a hue and drives the RGB LED that is already on the board

The LED on IO38 needs a 330 Ohm resistor in series or it will be damaged.
"""
MODE_FADE = 0
MODE_COLOUR = 1

MODE = MODE_COLOUR

LED_PIN = 38

# The pot's wiper, same pin as example 0.2 used.
POT_PIN = 4

# The onboard WS2812B, wired to IO2 through a 1 kOhm series resistor. Not brought out to a header.
RGB_PIN = 2

# 5 kHz is far above what the eye can follow.
PWM_FREQ = 5000

# Fixed so the pot changes one thing only. A quarter brightness is plenty: the onboard LED is uncomfortable
# to look at wide open.
SATURATION = 1.0
BRIGHTNESS = 0.25

# Vision is roughly logarithmic, so a linear duty ramp spends nearly all its visible change in the bottom twenty
# counts and then appears to stall. Raising the input to the power of 2.2 undoes that.
gamma8 = [int(pow(i / 255.0, 2.2) * 255.0 + 0.5) for i in range(256)]


def hsv_to_rgb(h, s, v):
    """Convert a hue in degrees, saturation and value into three 0-255 channel levels."""
    c = v * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = v - c

    if h < 60:
        rf, gf, bf = c, x, 0.0
    elif h < 120:
        rf, gf, bf = x, c, 0.0
    elif h < 180:
        rf, gf, bf = 0.0, c, x
    elif h < 240:
        rf, gf, bf = 0.0, x, c
    elif h < 300:
        rf, gf, bf = x, 0.0, c
    else:
        rf, gf, bf = c, 0.0, x

    return (int((rf + m) * 255), int((gf + m) * 255), int((bf + m) * 255))


if MODE == MODE_FADE:
    """
    Hardware PWM: once running, a timer in the chip generates the waveform and the processor is free.
    duty_u16() only changes the duty cycle, it does not do the switching. MicroPython's duty is 16-bit, 0 to 65535,
    so an 8-bit table value is scaled up by 257 to cover the same range.
    """
    led = PWM(Pin(LED_PIN), freq=PWM_FREQ, duty_u16=0)
    print("FADE mode: linear ramp, then gamma-corrected ramp. Watch the LED, not the numbers.")

    while True:
        # Even steps of duty. The LED brightens fast and then looks like it stopped, though the duty is still
        # climbing.
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

else:
    pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)

    # The LED is a WS2812B: IO2 sends it a serial message rather than a voltage, and a controller inside the
    # package sets the three channels. The neopixel module handles the GRB byte order and the strict timing.
    rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)

    print("COLOUR mode: hue on IO4.")

    while True:
        raw = pot.read()

        # Hue is the colour as an angle: 0 red, 120 green, 240 blue, 360 back to red. One knob walks through every
        # colour there is, which three separate red, green and blue levels could not do.
        hue = (raw / 4095.0) * 360.0

        rgb[0] = hsv_to_rgb(hue, SATURATION, BRIGHTNESS)
        rgb.write()

        time.sleep_ms(20)

# Before section 6: opening the JP1 solder jumper disconnects this LED to stop its leakage during deep sleep,
# and COLOUR mode then does nothing at all.
