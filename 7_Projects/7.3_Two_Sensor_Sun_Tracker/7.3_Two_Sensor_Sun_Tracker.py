"""
@file       7.3_Two_Sensor_Sun_Tracker.py
@brief      Two photoresistors either side of a paper strip turn a servo needle towards the brighter one, with a
            dead band and a rate limit to keep it from shuffling on its own noise.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
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

The servo takes its power from VCC, as in example 4.2.
"""
LDR_LEFT_PIN = 4
LDR_RIGHT_PIN = 5

SERVO_PIN = 47

DATA_PIN = 11
CLOCK_PIN = 12
LATCH_PIN = 10
OE_PIN = 13

# Your servo's real limits, measured in example 4.2.
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

# Calibration, filled in at startup. Each sensor gets its own.
left_min, left_max = 4095, 0
right_min, right_max = 4095, 0

current_pulse_us = PULSE_CENTRE_US
update_count = 0


def write_pulse(pulse_us):
    servo.duty_ns(pulse_us * 1000)


def scaled(raw, minimum, maximum):
    pct = (raw - minimum) * 100 // (maximum - minimum)
    return max(0, min(100, pct))


def pulse_for(error):
    """An error of -100 to 100 turned into a pulse width, one half of the sweep at a time so the centre trim moves
    only the centre."""
    if error >= 0:
        return PULSE_CENTRE_US + (error * (PULSE_MAX_US - PULSE_CENTRE_US)) // 100
    return PULSE_CENTRE_US + (error * (PULSE_CENTRE_US - PULSE_MIN_US)) // 100


def error_for(pulse_us):
    """The reverse, used by the dead band to ask where the needle is currently pointing."""
    if pulse_us >= PULSE_CENTRE_US:
        return (pulse_us - PULSE_CENTRE_US) * 100 // (PULSE_MAX_US - PULSE_CENTRE_US)
    return -((PULSE_CENTRE_US - pulse_us) * 100 // (PULSE_CENTRE_US - PULSE_MIN_US))


def show_error(error):
    """Lit from the middle outwards, so the bar shows both the size of the error and which way it points. It moves
    while the needle is still gliding, which is the quickest way to tell a too-wide dead band from a dead sensor."""
    pattern = 0
    magnitude = max(0, min(4, abs(error) // 12))

    for i in range(magnitude):
        if error > 0:
            pattern |= 1 << (3 - i)
        else:
            pattern |= 1 << (4 + i)

    if magnitude == 0:
        pattern = 0b00011000

    for bit in range(7, -1, -1):
        data.value((pattern >> bit) & 1)
        clock.value(1)
        clock.value(0)

    latch.value(1)
    latch.value(0)


def calibrate():
    """Ten seconds of moving a light around the sensor head. Each sensor records its own darkest and brightest
    reading, and everything afterwards is a percentage of that sensor's own range."""
    global left_min, left_max, right_min, right_max

    print()
    print("CALIBRATING for 10 seconds. Move a light around both sensors, and shade them.")

    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < 10000:
        left = ldr_left.read()
        right = ldr_right.read()

        if left < left_min:
            left_min = left
        if left > left_max:
            left_max = left
        if right < right_min:
            right_min = right
        if right > right_max:
            right_max = right

        time.sleep_ms(5)

    if left_max - left_min < 10:
        left_max = left_min + 10
    if right_max - right_min < 10:
        right_max = right_min + 10

    print("left  {} to {}".format(left_min, left_max))
    print("right {} to {}".format(right_min, right_max))
    print()
    print("left right error pulse_us")


write_pulse(current_pulse_us)
calibrate()

last_update_ms = 0

while True:
    if time.ticks_diff(time.ticks_ms(), last_update_ms) < UPDATE_INTERVAL_MS:
        continue
    last_update_ms = time.ticks_ms()

    # Calibrate each sensor to its own range before subtracting, not after. Two photoresistors from the same bag are
    # not matched, and subtracting raw readings turns that mismatch into a permanent error the needle cannot tell
    # from a real one: it sits off-centre and looks exactly like a bug in the code.
    left = scaled(ldr_left.read(), left_min, left_max)
    right = scaled(ldr_right.read(), right_min, right_max)

    # Gained here, once, so the needle, the LED bar and the printed error all mean the same thing.
    error = max(-100, min(100, (left - right) * ERROR_GAIN))

    show_error(error)

    # Hard over at full error, on the trimmed centre when the sensors agree.
    target_us = pulse_for(error)

    # Where the needle points now, in the same units, so the two can be compared directly.
    shown_error = error_for(current_pulse_us)

    if abs(error - shown_error) > DEAD_BAND:
        # Move towards the target rather than jumping, so a sudden change in the light becomes a glide.
        gap = target_us - current_pulse_us
        current_pulse_us += max(-STEP_US, min(STEP_US, gap))

    current_pulse_us = max(PULSE_MIN_US, min(PULSE_MAX_US, current_pulse_us))
    write_pulse(current_pulse_us)

    # Printed whether or not the needle moved, so a still needle is visibly a decision rather than a crash.
    update_count += 1
    if update_count >= PRINT_EVERY:
        update_count = 0
        print(left, right, error, current_pulse_us)

# The LED bar is bright, close to the sensors, and the photoresistors can see it. If the needle drifts towards the
# breadboard whenever the bar lights up, that is the LEDs, not the control loop.
