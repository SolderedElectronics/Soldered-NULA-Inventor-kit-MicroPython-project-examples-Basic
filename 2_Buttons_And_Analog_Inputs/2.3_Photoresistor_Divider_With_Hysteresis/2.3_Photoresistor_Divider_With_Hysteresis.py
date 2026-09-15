"""
@file       2.3_Photoresistor_Divider_With_Hysteresis.py
@brief      Measure the photoresistor's own resistance, pick a divider resistor from that measurement, calibrate
            the light range, then switch an LED on one threshold and on two.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin, ADC
import time

"""
The board cannot measure resistance, only voltage. Pairing the photoresistor with a fixed resistor turns its
changing resistance into a changing voltage at the junction, and IO4 reads that junction.

  MODE_MEASURE_R   work out the photoresistor's resistance right now. Run it covered, then under a torch.
  MODE_CALIBRATE   record the darkest and brightest readings over ten seconds and report light as a percentage.
  MODE_SINGLE      LED switched by one threshold. Hold the light at the boundary and watch it fail.
  MODE_HYSTERESIS  LED switched by two thresholds. Same light, steady output.
"""
MODE_MEASURE_R = 0
MODE_CALIBRATE = 1
MODE_SINGLE = 2
MODE_HYSTERESIS = 3

MODE = MODE_HYSTERESIS

LDR_PIN = 4
LED_PIN = 38

# The fixed resistor you actually fitted. Start with the kit's 10 kOhm, then change this to whatever you pick
# after MODE_MEASURE_R, or the calculation lies.
R_FIXED_OHMS = 10000.0

VSUPPLY_MV = 3300.0

# Thresholds, as a percentage of the calibrated range.
THRESHOLD_PCT = 50
HYSTERESIS_PCT = 8

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)
led = Pin(LED_PIN, Pin.OUT)

# Calibration results, in raw ADC counts.
light_min = 4095
light_max = 0

led_on = False


def averaged_millivolts():
    total = 0
    for _ in range(64):
        total += ldr.read_uv() // 1000
    return total / 64.0


def run_calibration():
    """
    Ten seconds of hand-waving, keeping the lowest and highest readings seen. A percentage of this sensor's range in
    this room is honest; converting to lux would be a fiction, because a photoresistor is not linear in light level
    or in anything else convenient and parts vary enormously.
    """
    global light_min, light_max

    print()
    print("CALIBRATING for 10 seconds. Cover the sensor, then light it up.")

    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < 10000:
        raw = ldr.read()
        if raw < light_min:
            light_min = raw
        if raw > light_max:
            light_max = raw
        time.sleep_ms(5)

    # A range of zero would make every later division fail.
    if light_max - light_min < 10:
        light_max = light_min + 10

    print("Range: {} to {}".format(light_min, light_max))
    print()


def light_percent():
    raw = ldr.read()
    pct = (raw - light_min) * 100 // (light_max - light_min)
    return max(0, min(100, pct))


if MODE != MODE_MEASURE_R:
    run_calibration()

while True:
    if MODE == MODE_MEASURE_R:
        """
        In a divider the two voltages are in the same ratio as the two resistances, so the unknown falls out:

          R_ldr = R_fixed * (Vsupply - Vjunction) / Vjunction

        Run it covered by your hand, then under a phone torch. Then fit a resistor near the geometric middle of the
        two results, the square root of them multiplied, set R_FIXED_OHMS above, and see whether the reading now
        covers more of the 0 to 4095 range than the 10 kOhm did.
        """
        v_mv = averaged_millivolts()

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

    elif MODE == MODE_CALIBRATE:
        print(light_percent())
        time.sleep_ms(100)

    elif MODE == MODE_SINGLE:
        # Hold the light steady right at the boundary. The reading wobbles a few counts, every wobble crosses the
        # line, and the LED flickers. Nothing is wrong with the code.
        pct = light_percent()

        led_on = pct > THRESHOLD_PCT
        led.value(1 if led_on else 0)

        print(pct, 100 if led_on else 0)
        time.sleep_ms(50)

    else:
        # Switching on takes more light than switching off, so noise cannot move the output back. Same mechanism as
        # the relay in 5.2 and the thermostat in 7.1.
        pct = light_percent()

        on_above = THRESHOLD_PCT + HYSTERESIS_PCT
        off_below = THRESHOLD_PCT - HYSTERESIS_PCT

        if not led_on and pct > on_above:
            led_on = True
        elif led_on and pct < off_below:
            led_on = False

        led.value(1 if led_on else 0)

        print(pct, 100 if led_on else 0)
        time.sleep_ms(50)

# The photoresistor sees the LED wired next to it. Here that only skews a threshold. In 7.3 it sends the tracker
# off course and looks exactly like a code bug.
