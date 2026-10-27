"""
@file       1.1_LED_Current_And_Resistor_Sizing.py
@brief      The board measures its own LED circuit: forward voltage, actual current, and what resistor you would
            need for 5, 10 and 20 mA. Swap the 330 Ohm for the 10 kOhm and run it again.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

# IO38 drives the LED. IO4 reads the junction between the LED and its resistor, which is the only voltage here
# that has to be measured rather than worked out.
LED_PIN = 38
SENSE_PIN = 4

# The resistor you actually fitted, in ohms. Change this when you swap the resistor: every number below depends
# on it being right.
R_OHMS = 330.0

VSUPPLY_MV = 3300.0

# The currents we want a resistor recommendation for, in milliamps.
TARGETS_MA = (5.0, 10.0, 20.0)

led = Pin(LED_PIN, Pin.OUT)
sense = ADC(Pin(SENSE_PIN), atten=ADC.ATTN_11DB)

# The LED has to be lit for there to be a current to measure.
led.value(1)
time.sleep_ms(50)

while True:
    # Average a batch. Every other number here is derived from this one, so a few counts of wobble would show up
    # three times over. Example 2.2 is about that noise.
    total = 0
    for _ in range(64):
        total += sense.read_uv() // 1000

    # The resistor sits between the pin and the junction, so the junction is the LED's anode and this
    # reading is the forward voltage itself. Nothing here has to be worked out.
    v_forward_mv = total / 64.0

    # Whatever the supply gives that does not land across the LED lands across the resistor.
    v_resistor_mv = VSUPPLY_MV - v_forward_mv

    # Ohm's law, and the LED is in series with the resistor so this is its current too.
    # Millivolts divided by ohms gives milliamps directly.
    current_ma = v_resistor_mv / R_OHMS

    print()
    print("Resistor fitted:   {:.0f} ohm".format(R_OHMS))
    print("Across resistor:   {:.0f} mV".format(v_resistor_mv))
    print("LED forward volts: {:.3f} V".format(v_forward_mv / 1000.0))
    print("LED current:       {:.3f} mA".format(current_ma))

    # The same two equations run backwards: R = (supply - forward voltage) / target current.
    print("For this LED, to get:")
    for target in TARGETS_MA:
        r_needed = (VSUPPLY_MV - v_forward_mv) / target
        print("  {:.0f} mA, fit {:.0f} ohm".format(target, r_needed))

    time.sleep_ms(2000)
