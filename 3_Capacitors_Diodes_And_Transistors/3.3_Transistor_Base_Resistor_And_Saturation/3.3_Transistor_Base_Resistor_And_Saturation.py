"""
@file       3.3_Transistor_Base_Resistor_And_Saturation.py
@brief      Sweeps the base drive of an NPN transistor with the potentiometer and measures load current, base
            current and the ratio between them. Finds the point where the transistor stops saturating, and ends
            with the calculation you would do to pick a base resistor.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin, ADC
import time

"""
The TO-92 legs are usually emitter, base, collector from left to right with the flat face towards you, but this
varies by part number. Check yours against its datasheet: getting it wrong costs you a transistor.

IO48 feeds the potentiometer, the wiper feeds the base through a 10 kOhm resistor, and four pins measure the
result: IO7 the wiper, IO5 the base itself, IO4 the bottom of the load resistor and IO6 the collector.

The 10 kOhm is not optional. The base-emitter junction is a diode, so a wiper near 3.3 V wired straight to the base
would put the whole supply across it and destroy the transistor.

Turn the pot slowly up from the ground end and watch the collector. The transistor is off for the first part of the
travel, passes through its linear region in a narrow band around a wiper voltage of 0.66 V, and is saturated for
the rest. The edge of saturation needs only about 5 uA of base current, which no combination of the kit's 10 kOhm
resistors gets near, which is why the base is swept with the pot.
"""
DRIVE_PIN = 48

SENSE_A_PIN = 4
SENSE_BASE_PIN = 5
SENSE_C_PIN = 6
SENSE_DRIVE_PIN = 7

# The base resistor you actually fitted, in ohms.
R_BASE_OHMS = 10000.0

# The load resistor in series with the LED, in ohms.
R_LOAD_OHMS = 330.0

VSUPPLY_MV = 3300.0

drive = Pin(DRIVE_PIN, Pin.OUT)
drive.value(1)

sense_a = ADC(Pin(SENSE_A_PIN), atten=ADC.ATTN_11DB)
sense_base = ADC(Pin(SENSE_BASE_PIN), atten=ADC.ATTN_11DB)
sense_c = ADC(Pin(SENSE_C_PIN), atten=ADC.ATTN_11DB)
sense_drive = ADC(Pin(SENSE_DRIVE_PIN), atten=ADC.ATTN_11DB)

time.sleep_ms(50)


def averaged(adc):
    total = 0
    for _ in range(64):
        total += adc.read_uv() // 1000
    return total / 64.0


def design_check(load_ma, actual_base_ma):
    """
    The design step. Start from the load current you need, divide by a pessimistic gain because a datasheet figure
    is a minimum, then multiply by five so the transistor stays well past the edge of saturation. Overdriving the
    base costs almost nothing, so err generous.

    The second print converts what the pot is doing right now back into the resistor that would do the same job
    from 3.3 V. Sweep to the edge and that is the largest base resistor this load could have got away with.
    """
    PESSIMISTIC_GAIN = 50.0
    OVERDRIVE = 5.0
    V_BE_MV = 700.0

    needed_base_ma = (load_ma / PESSIMISTIC_GAIN) * OVERDRIVE
    r_recommended = (VSUPPLY_MV - V_BE_MV) / needed_base_ma

    print("safe base resistor for this load: about {:.1f} kOhm".format(r_recommended / 1000.0))

    if actual_base_ma > 0.0001:
        r_equivalent = (VSUPPLY_MV - V_BE_MV) / actual_base_ma
        print("this base current equals a {:.1f} kOhm resistor driven from 3V3".format(r_equivalent / 1000.0))


while True:
    v_drive = averaged(sense_drive)
    v_a = averaged(sense_a)
    v_base = averaged(sense_base)
    v_c = averaged(sense_c)

    # Everything in that branch is in series, so this is the current through the LED and the transistor too.
    load_ma = (VSUPPLY_MV - v_a) / R_LOAD_OHMS

    # Both ends are measured rather than assumed: the pot is a 10 kOhm divider, so its wiper sags as soon as the
    # base draws anything. Notice how little the base voltage moves across the sweep, because it is a diode holding
    # near 0.7 V, which is why design_check() subtracts it instead of assuming the full supply reaches the resistor.
    base_ma = (v_drive - v_base) / R_BASE_OHMS if v_drive > v_base else 0.0

    """
    This ratio is not the transistor's gain, and reading it as one is the trap the example is built around. While it
    is saturated the collector current is set by the load resistor and the supply, so more base current changes
    nothing and the ratio just falls as you turn the pot up.

    The real gain shows only at the edge. Turn slowly until the collector starts to climb: the ratio printed just
    before it does is the closest this circuit gets to the datasheet figure. On the bench that is 11 to 15 saturated
    against 250 at the edge, same transistor, same wiring. Take the edge figure as give or take a fifth, since it
    comes from a 53 mV difference between two ADC pins.
    """
    ratio = (load_ma / base_ma) if base_ma > 0.0001 else 0

    print()
    print("wiper voltage:     {:.0f} mV".format(v_drive))
    print("base voltage:      {:.0f} mV".format(v_base))
    print("collector voltage: {:.0f} mV".format(v_c))
    print("load current:      {:.3f} mA".format(load_ma))
    print("base current:      {:.1f} uA".format(base_ma * 1000.0))
    print("current ratio:     {:.0f}".format(ratio))

    # This ADC pins at 4095 near 3140 mV, as 3.2 found. Here that happens with the transistor off, when the bottom of
    # the load resistor sits at the full supply.
    transistor_off = v_a > 3100

    if transistor_off:
        print("state: off. Load current is at the ADC ceiling and the collector is a floating node, so both")
        print("       readings above are meaningless. Nothing is conducting.")
    elif v_c < 300:
        # As far on as it can get. Power is current times voltage, and the voltage across it is nearly nothing.
        print("state: saturated, behaving like a closed switch")
    else:
        # The base has run out, so a whole volt is dropped inside the transistor at the load current. Touch it: the
        # warmth is the power the LED did not get.
        print("state: NOT saturated. Touch the transistor, it is dissipating the difference.")

    # With nothing conducting the calculation would run on the ceiling reading and print nonsense.
    if not transistor_off:
        design_check(load_ma, base_ma)

    time.sleep_ms(500)
