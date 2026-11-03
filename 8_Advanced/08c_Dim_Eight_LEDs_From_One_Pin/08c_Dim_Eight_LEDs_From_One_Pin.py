"""
@file       08c_Dim_Eight_LEDs_From_One_Pin.py
@brief      Lights all eight LEDs on a 74HC595 and dims them together with a PWM signal on output enable,
            with a pot setting the level.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM, ADC
import time

"""
Find pin 1 first. It is at the end with the half-moon notch, left-hand pin with the notch at the top. Some packages
also carry a round dimple that is not next to the notch and is not pin 1 on this part.

Two things here are not optional and neither announces itself when missing. SRCLR must be held at 3V3 or the
register clears itself at random. And the 100 nF must sit as close to the chip's supply pins as the breadboard
allows, because eight outputs switching at once is a current spike the supply cannot follow.

Each of the eight outputs needs its own 330 Ohm resistor in series with its LED.
"""
DATA_PIN = 11
CLOCK_PIN = 12
LATCH_PIN = 10
OE_PIN = 13
POT_PIN = 4

latch = Pin(LATCH_PIN, Pin.OUT, value=0)
data = Pin(DATA_PIN, Pin.OUT)
clock = Pin(CLOCK_PIN, Pin.OUT)
pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)

# Output enable gets a PWM signal instead of a steady level.
oe_pwm = PWM(Pin(OE_PIN), freq=5000, duty_u16=0)

print()
print("74HC595 on IO11 (data), IO12 (clock), IO10 (latch), IO13 (output enable)")


def write_manual(value):
    """
    The manual version, one pin write at a time. A shift register is a row of eight memory cells: put a bit on the
    data pin, pulse the clock, and every cell hands its contents to the next while the first takes the new bit.

    Nothing appears on the outputs while this happens. They are fed from a second set of latches that only copy the
    row when the latch pin is pulsed.
    """
    for bit in range(7, -1, -1):
        data.value((value >> bit) & 1)
        clock.value(1)
        clock.value(0)

    latch.value(1)
    latch.value(0)


# Output enable does not change what is in the register, it decides whether the outputs are connected at all.
# Feed it PWM and all eight dim together for no processor time at all. The duty is inverted because the pin is
# active low: full duty would hold the outputs off permanently.
while True:
    # All eight on, so the dimming happens to the whole row and not to a pattern.
    write_manual(0b11111111)

    brightness = pot.read() * 16  # 0-4095 counts scaled to roughly 0-65535
    oe_pwm.duty_u16(65535 - min(65535, brightness))

    time.sleep_ms(20)
