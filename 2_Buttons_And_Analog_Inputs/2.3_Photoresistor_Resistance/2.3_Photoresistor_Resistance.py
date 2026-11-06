"""
@file       2.3_Photoresistor_Resistance.py
@brief      Measures the photoresistor's own resistance from the voltage at the junction of the divider, so you can pick
            a fixed resistor to pair it with.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

"""
The board cannot measure resistance, only voltage. Pairing the photoresistor with a fixed resistor turns its
changing resistance into a changing voltage at the junction, and IO4 reads that junction.
"""
LDR_PIN = 4

# The fixed resistor you actually fitted. Start with the kit's 10 kOhm, then change this to whatever you pick
# after measuring, or the calculation lies.
R_FIXED_OHMS = 10000.0

VSUPPLY_MV = 3300.0

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)

while True:
    """
    In a divider the two voltages are in the same ratio as the two resistances, so the unknown falls out:

      R_ldr = R_fixed * (Vsupply - Vjunction) / Vjunction

    Run it covered by your hand, then under a phone torch. Then fit a resistor near the geometric middle of the
    two results, the square root of them multiplied, set R_FIXED_OHMS above, and see whether the reading now
    covers more of the 0 to 4095 range than the 10 kOhm did.
    """
    # Average 64 readings, so a few counts of wobble do not show up in the answer.
    total = 0
    for _ in range(64):
        total += ldr.read_uv() // 1000
    v_mv = total / 64.0

    # Below a few millivolts the arithmetic blows up and the answer means nothing.
    if v_mv < 5:
        print("Reading too low to work with. Is the divider wired the right way round?")
        time.sleep_ms(500)
        continue

    r_ldr = R_FIXED_OHMS * (VSUPPLY_MV - v_mv) / v_mv

    if r_ldr > 1000:
        print("junction {:.0f} mV,  photoresistor about {:.1f} kOhm".format(v_mv, r_ldr / 1000.0))
    else:
        print("junction {:.0f} mV,  photoresistor about {:.0f} ohm".format(v_mv, r_ldr))

    time.sleep_ms(500)
