"""
@file       3.3_Transistor_Base_Resistor_And_Saturation.py
@brief      Sweeps the base drive of an NPN transistor with the potentiometer and measures load current, base
            current and the ratio between them. Finds the point where the transistor stops saturating, and ends
            with the calculation you would do to pick a base resistor.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
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
travel, passes through its linear region in a narrow band of wiper voltage between 0.86 V and 0.96 V, and is
saturated for the rest. The base itself barely moves across all of that, sitting near 0.66 V the whole way. The
edge of saturation needs about 30 uA of base current, which no combination of the kit's 10 kOhm resistors gets
near, which is why the base is swept with the pot.
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

# Used by the design step at the end. A datasheet gain is a minimum, so assume a pessimistic one, and overdrive the
# base by five so the transistor stays well past the edge of saturation. 700 mV is what the base sits at.
PESSIMISTIC_GAIN = 50.0
OVERDRIVE = 5.0
V_BE_MV = 700.0

drive = Pin(DRIVE_PIN, Pin.OUT)
drive.value(1)

sense_a = ADC(Pin(SENSE_A_PIN), atten=ADC.ATTN_11DB)
sense_base = ADC(Pin(SENSE_BASE_PIN), atten=ADC.ATTN_11DB)
sense_c = ADC(Pin(SENSE_C_PIN), atten=ADC.ATTN_11DB)
sense_drive = ADC(Pin(SENSE_DRIVE_PIN), atten=ADC.ATTN_11DB)

time.sleep_ms(50)

while True:
    # Every voltage below is the mean of 64 readings, because a single one carries a few counts of noise. Each block
    # adds up 64 readings and divides by 64.
    drive_total = 0
    for _ in range(64):
        drive_total += sense_drive.read_uv() // 1000
    v_drive = drive_total / 64.0

    a_total = 0
    for _ in range(64):
        a_total += sense_a.read_uv() // 1000
    v_a = a_total / 64.0

    base_total = 0
    for _ in range(64):
        base_total += sense_base.read_uv() // 1000
    v_base = base_total / 64.0

    c_total = 0
    for _ in range(64):
        c_total += sense_c.read_uv() // 1000
    v_c = c_total / 64.0

    # Everything in that branch is in series, so this is the current through the LED and the transistor too.
    load_ma = (VSUPPLY_MV - v_a) / R_LOAD_OHMS

    # Both ends are measured rather than assumed: the pot is a 10 kOhm divider, so its wiper sags as soon as the
    # base draws anything. Notice how little the base voltage moves across the sweep, because it is a diode holding
    # near 0.7 V, which is why the design step at the end subtracts it instead of assuming the full supply reaches
    # the resistor.
    base_ma = 0.0
    if v_drive > v_base:
        base_ma = (v_drive - v_base) / R_BASE_OHMS

    """
    This ratio is not the transistor's gain, and reading it as one is the trap the example is built around. While it
    is saturated the collector current is set by the load resistor and the supply, so more base current changes
    nothing and the ratio just falls as you turn the pot up.

    The real gain shows only at the edge. Turn slowly until the collector starts to climb: the ratio printed just
    before it does is the closest this circuit gets to the datasheet figure. On the bench a 2N2222A read 17 fully
    saturated against about 119 at the edge, same transistor, same wiring. Take the edge figure as give or take a
    fifth: it comes out of a 295 mV difference between two ADC pins divided by a 10 kOhm resistor.
    """
    ratio = 0
    if base_ma > 0.0001:
        ratio = load_ma / base_ma

    print()
    print("wiper voltage:     {:.0f} mV".format(v_drive))
    print("base voltage:      {:.0f} mV".format(v_base))
    print("collector voltage: {:.0f} mV".format(v_c))
    print("load current:      {:.3f} mA".format(load_ma))
    print("base current:      {:.1f} uA".format(base_ma * 1000.0))
    print("current ratio:     {:.0f}".format(ratio))

    # This ADC pins at 4095 near 3140 mV, as T15 found. Here that happens with the transistor off, when the bottom of
    # the load resistor sits at the full supply.
    transistor_off = False
    if v_a > 3100:
        transistor_off = True

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

    # The design step. With nothing conducting it would run on the ceiling reading and print nonsense, so skip it
    # then. Start from the load current you need, divide by the pessimistic gain, and multiply by the overdrive.
    # Overdriving the base costs almost nothing, so err generous.
    if not transistor_off:
        needed_base_ma = (load_ma / PESSIMISTIC_GAIN) * OVERDRIVE
        r_recommended = (VSUPPLY_MV - V_BE_MV) / needed_base_ma

        print("safe base resistor for this load: about {:.1f} kOhm".format(r_recommended / 1000.0))

        # Convert what the pot is doing right now back into the resistor that would do the same job from 3.3 V.
        # Sweep to the edge and that is the largest base resistor this load could have got away with.
        if base_ma > 0.0001:
            r_equivalent = (VSUPPLY_MV - V_BE_MV) / base_ma
            print("this base current equals a {:.1f} kOhm resistor driven from 3V3".format(r_equivalent / 1000.0))

    time.sleep_ms(500)
