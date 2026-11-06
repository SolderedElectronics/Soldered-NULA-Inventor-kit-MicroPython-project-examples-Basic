"""
@file       7.3_Two_Sensor_Sun_Tracker.py
@brief      Two photoresistors either side of a paper strip turn a servo needle towards the brighter one, with a
            dead band and a rate limit to keep it from shuffling on its own noise.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC, PWM
import time

"""
The two photoresistors are on IO4 and IO5, the servo on IO47, and the 74HC595 LED bar on the four pins below.

The sensors need a strip of paper standing upright in the channel between them, so light from one side falls on one
and is shadowed from the other. Without it they read almost the same value and the script has nothing to steer by.

Nothing is mounted on the servo. It is a needle: the horn turns to face whichever side is brighter, and you move a
light around the sensor head to lead it. A real tracker carries its sensors on the moving part, which needs a
bracket this kit does not have.

The servo takes its power from VCC, as in T19.
"""
LDR_LEFT_PIN = 4
LDR_RIGHT_PIN = 5

SERVO_PIN = 47

DATA_PIN = 11
CLOCK_PIN = 12
LATCH_PIN = 10
OE_PIN = 13

# Your servo's real limits, measured in T19.
PULSE_MIN_US = 550
PULSE_MAX_US = 2500

# Where the needle sits when the sensors agree. Halfway is only halfway by arithmetic: the horn refits no finer
# than one spline, 18 degrees on an SG90. Each half of the sweep is mapped from this separately, so you can trim
# the centre without disturbing either end stop.
PULSE_CENTRE_US = 1525

"""
How hard the needle reacts to a difference between the sensors. In room light the two readings land within a few
points of each other, and five points out of a hundred barely moves the horn, so the difference is multiplied to
make the needle commit to a side rather than hover.

Raise it until the needle takes a side in ordinary light. Too far and it slams between the ends, because gain
multiplies the sensors' noise along with the signal, which is what DEAD_BAND and the rate limit are for.
"""
ERROR_GAIN = 5

SERVO_FREQ = 50

# How far the needle may travel per update and how often one happens: together, its top speed, about one and a half
# seconds across the full sweep. Raise STEP_US to 2000 and it jumps instead, which is worth seeing once.
STEP_US = 40
UPDATE_INTERVAL_MS = 30

"""
The dead band, on the same 0 to 100 scale as the error, measured against where the needle already points rather
than against zero. The question is not whether the light is off centre but whether it has moved far enough since
last time to be worth chasing.

Set it to 0 and the needle never settles. Raise it if yours twitches with the light held still, lower it if it
ignores a light you have genuinely moved.
"""
DEAD_BAND = 8

# The console would be unreadable at one line every 30 ms, so only every fifth update prints.
PRINT_EVERY = 5

ldr_left = ADC(Pin(LDR_LEFT_PIN), atten=ADC.ATTN_11DB)
ldr_right = ADC(Pin(LDR_RIGHT_PIN), atten=ADC.ATTN_11DB)

data = Pin(DATA_PIN, Pin.OUT)
clock = Pin(CLOCK_PIN, Pin.OUT)
latch = Pin(LATCH_PIN, Pin.OUT, value=0)
Pin(OE_PIN, Pin.OUT, value=0)

# duty_ns() takes the pulse width directly, which is what a servo reads.
servo = PWM(Pin(SERVO_PIN), freq=SERVO_FREQ)

# Calibration, filled in at startup. Each sensor gets its own darkest and brightest reading. They start at the
# opposite ends so that the first reading replaces both.
left_min = 4095
left_max = 0
right_min = 4095
right_max = 0

current_pulse_us = PULSE_CENTRE_US
update_count = 0

# Start with the needle in the centre.
servo.duty_ns(current_pulse_us * 1000)

# Calibration: ten seconds of moving a light around the sensor head. Each sensor records its own darkest and
# brightest reading, and everything afterwards is a percentage of that sensor's own range.
print()
print("CALIBRATING for 10 seconds. Move a light around both sensors, and shade them.")

start = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), start) < 10000:
    left_reading = ldr_left.read()
    right_reading = ldr_right.read()

    if left_reading < left_min:
        left_min = left_reading
    if left_reading > left_max:
        left_max = left_reading
    if right_reading < right_min:
        right_min = right_reading
    if right_reading > right_max:
        right_max = right_reading

    time.sleep_ms(5)

# If a sensor barely changed, give it a range of at least 10 so the percentages below never divide by zero.
if left_max - left_min < 10:
    left_max = left_min + 10
if right_max - right_min < 10:
    right_max = right_min + 10

print("left  {} to {}".format(left_min, left_max))
print("right {} to {}".format(right_min, right_max))
print()
print("left right error pulse_us")

last_update_ms = 0

while True:
    # One update every 30 ms. The rest of the time the loop just comes round again.
    if time.ticks_diff(time.ticks_ms(), last_update_ms) >= UPDATE_INTERVAL_MS:
        last_update_ms = time.ticks_ms()

        # Calibrate each sensor to its own range before subtracting, not after. Two photoresistors from the same bag
        # are not matched, and subtracting raw readings turns that mismatch into a permanent error the needle cannot
        # tell from a real one: it sits off-centre and looks exactly like a bug in the code. Each reading becomes a
        # percentage of that sensor's own range, from 0 to 100.
        left = (ldr_left.read() - left_min) * 100 // (left_max - left_min)
        if left < 0:
            left = 0
        if left > 100:
            left = 100

        right = (ldr_right.read() - right_min) * 100 // (right_max - right_min)
        if right < 0:
            right = 0
        if right > 100:
            right = 100

        # Gained here, once, so the needle, the LED bar and the printed error all mean the same thing.
        error = (left - right) * ERROR_GAIN
        if error < -100:
            error = -100
        if error > 100:
            error = 100

        # The LED bar, lit from the middle outwards, so it shows both the size of the error and which way it points.
        # It moves while the needle is still gliding, which is the quickest way to tell a too-wide dead band from a
        # dead sensor. Every 12 points of error lights one more LED, up to four on each side. Each pattern is the
        # eight LEDs written as eight 1s and 0s, left to right.
        magnitude = abs(error) // 12
        if magnitude > 4:
            magnitude = 4

        pattern = "00011000"

        if error > 0 and magnitude == 1:
            pattern = "00001000"
        elif error > 0 and magnitude == 2:
            pattern = "00001100"
        elif error > 0 and magnitude == 3:
            pattern = "00001110"
        elif error > 0 and magnitude == 4:
            pattern = "00001111"
        elif error < 0 and magnitude == 1:
            pattern = "00010000"
        elif error < 0 and magnitude == 2:
            pattern = "00110000"
        elif error < 0 and magnitude == 3:
            pattern = "01110000"
        elif error < 0 and magnitude == 4:
            pattern = "11110000"

        # Send the eight digits to the shift register one at a time, then pulse the latch to show them.
        for digit in pattern:
            data.value(int(digit))
            clock.value(1)
            clock.value(0)

        latch.value(1)
        latch.value(0)

        # Hard over at full error, on the trimmed centre when the sensors agree. The two halves of the sweep are
        # worked out separately, so the centre trim moves only the centre.
        if error >= 0:
            target_us = PULSE_CENTRE_US + (error * (PULSE_MAX_US - PULSE_CENTRE_US)) // 100
        else:
            target_us = PULSE_CENTRE_US + (error * (PULSE_CENTRE_US - PULSE_MIN_US)) // 100

        # Where the needle points now, on the same -100 to 100 scale, so the two can be compared directly. This is the
        # same sum run backwards.
        if current_pulse_us >= PULSE_CENTRE_US:
            shown_error = (current_pulse_us - PULSE_CENTRE_US) * 100 // (PULSE_MAX_US - PULSE_CENTRE_US)
        else:
            shown_error = -((PULSE_CENTRE_US - current_pulse_us) * 100 // (PULSE_CENTRE_US - PULSE_MIN_US))

        if abs(error - shown_error) > DEAD_BAND:
            # Move towards the target rather than jumping, so a sudden change in the light becomes a glide.
            gap = target_us - current_pulse_us
            if gap < -STEP_US:
                gap = -STEP_US
            if gap > STEP_US:
                gap = STEP_US
            current_pulse_us = current_pulse_us + gap

        if current_pulse_us < PULSE_MIN_US:
            current_pulse_us = PULSE_MIN_US
        if current_pulse_us > PULSE_MAX_US:
            current_pulse_us = PULSE_MAX_US

        servo.duty_ns(current_pulse_us * 1000)

        # Printed whether or not the needle moved, so a still needle is visibly a decision rather than a crash.
        update_count = update_count + 1
        if update_count >= PRINT_EVERY:
            update_count = 0
            print(left, right, error, current_pulse_us)

# The LED bar is bright, close to the sensors, and the photoresistors can see it. If the needle drifts towards the
# breadboard whenever the bar lights up, that is the LEDs, not the control loop.
