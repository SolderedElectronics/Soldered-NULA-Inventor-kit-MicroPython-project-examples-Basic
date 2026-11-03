"""
@file       07a_Measuring_An_RC_Time_Constant.py
@brief      Charges a capacitor through a resistor, captures the rise into a buffer, and prints the measured
            time constant next to the calculated one. Do it with the 10 uF, then with the 100 nF.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

"""
IO38 charges the capacitor through the resistor, IO4 reads the voltage across the capacitor as it rises, and the
button on IO21 starts a capture.

The 10 uF is an electrolytic and is polarised: the leg next to the stripe is the negative one. Fitting it backwards
is one of the few ways to damage a part on this page.
"""
DRIVE_PIN = 38
SENSE_PIN = 4
BUTTON_PIN = 21

"""
The parts you actually fitted. Change C_FARADS to 0.0000001 when you swap the 10 uF for the 100 nF.

  100 nF = 0.0000001 F
   10 uF = 0.00001 F

The measurement comes from the samples, so getting this wrong does not break it. It makes the calculated figure
printed beside it meaningless, and it paces the sampling for the wrong part.
"""
R_OHMS = 10000.0
C_FARADS = 0.00001

VSUPPLY_MV = 3300.0

# Nothing is printed until the capture is over. A print() in the sampling loop costs milliseconds, and with the
# 100 nF the whole event lasts about five milliseconds.
SAMPLES = 512

"""
One trip round the sampling loop costs roughly 120 us in MicroPython, most of it in read_uv() and the interpreter
itself. That is slower than the same loop in C, which matters here: the 100 nF capture gets fewer points on the
rise than the Arduino version does, and the 10 uF one is unaffected because its event is a hundred times longer.

Charging finishes after about five time constants, so a capture aimed at three of them puts the 63.2 % crossing
well inside, and the gap below is whatever is left after the loop has spent its own time.
"""
LOOP_COST_US = 120.0
SPAN_TAUS = 3.0
WANTED_INTERVAL_US = SPAN_TAUS * R_OHMS * C_FARADS * 1000000.0 / SAMPLES
SAMPLE_GAP_US = int(WANTED_INTERVAL_US - LOOP_COST_US) if WANTED_INTERVAL_US > LOOP_COST_US else 0

drive = Pin(DRIVE_PIN, Pin.OUT)
sense = ADC(Pin(SENSE_PIN), atten=ADC.ATTN_11DB)
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

drive.value(0)

value_mv = [0] * SAMPLES
time_us = [0] * SAMPLES

print()
print("R = {:.0f} ohm, C = {:.3f} uF, gap = {} us per sample".format(R_OHMS, C_FARADS * 1000000.0, SAMPLE_GAP_US))
print("Press the button to charge the capacitor and capture the rise.")


def report_capture():
    # A capacitor fills quickly at first and then slowly, because the closer it gets to the supply the smaller the
    # voltage difference driving current into it. Tau is the time to reach 63.2 %, and it is R times C, nothing else.
    tau_calculated_us = R_OHMS * C_FARADS * 1000000.0
    target_mv = VSUPPLY_MV * 0.632

    # Find the first sample above the 63.2 % line.
    crossing = -1
    for i in range(SAMPLES):
        if value_mv[i] >= target_mv:
            crossing = i
            break

    total_us = time_us[SAMPLES - 1]
    interval_us = total_us / SAMPLES

    print()
    print("Capture covered {:.2f} ms at about {:.1f} us per sample".format(total_us / 1000.0, interval_us))
    print("Calculated R x C: {:.3f} ms".format(tau_calculated_us / 1000.0))

    if crossing < 0:
        print("Never reached 63.2 %. The capture is shorter than the rise.")
    else:
        print("Measured to 63.2 %: {:.3f} ms, from sample {} of {}".format(
            time_us[crossing] / 1000.0, crossing, SAMPLES))

        # How many samples landed on the rise decides whether to believe the answer.
        if crossing < 20:
            print("Only a handful of samples on the rise. Treat this figure with suspicion.")

    """
    Both ends of the CSV lie, and neither is the capacitor's fault. The flat top of the 100 nF capture reads about
    3139 mV rather than 3300 because that is the top of this ADC's range, and the first samples of the 10 uF capture
    read 0 mV while the capacitor is plainly charging. A measurement taken in the middle is worth more than one at
    either extreme, which is the other reason tau is defined at 63.2 %.
    """
    print()
    print("us,mV")
    for i in range(SAMPLES):
        print("{},{}".format(time_us[i], value_mv[i]))


while True:
    if button.value() != 0:
        continue

    # Empty the capacitor first, or the next capture starts halfway up. Five time constants is the usual rule.
    drive.value(0)
    time.sleep_ms(int(5000 * R_OHMS * C_FARADS) + 20)

    # Throw one reading away before starting the clock. The first conversion after the ADC has been idle is much
    # slower than the ones that follow, and it lands where the voltage is moving fastest.
    sense.read_uv()

    # Anything between these two lines is time the rise happened without you watching.
    start_us = time.ticks_us()
    drive.value(1)

    for i in range(SAMPLES):
        value_mv[i] = sense.read_uv() // 1000
        time_us[i] = time.ticks_diff(time.ticks_us(), start_us)
        if SAMPLE_GAP_US > 0:
            time.sleep_us(SAMPLE_GAP_US)

    report_capture()

    # Wait for the button to be released before arming again.
    while button.value() == 0:
        time.sleep_ms(10)
    time.sleep_ms(200)
