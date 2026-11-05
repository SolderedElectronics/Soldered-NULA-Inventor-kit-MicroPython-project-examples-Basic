"""
@file       11e_Reaction_Timer.py
@brief      A reaction timer game. Press the button to start a round. The LED stays dark for a random time
            between 1.5 and 4 seconds, then lights and the buzzer chirps, and you press the button as fast as
            you can. The script prints your reaction in milliseconds, your best time of the session and the
            average of your last five rounds. A press before the LED lights is a false start and voids the round.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM
import os
import random
import time

# The button is on IO21 with the internal pull-up, the LED on IO38 and the buzzer's transistor on IO48.
BUTTON_PIN = 21
LED_PIN = 38
BUZZER_PIN = 48

# From T17. Yours will be a different number.
BUZZER_HZ = 2700
BUZZER_DUTY = 32768

# The LED stays dark for a random time between these two limits, in milliseconds.
MIN_WAIT_MS = 1500
MAX_WAIT_MS = 4000

# A round with no press this long after the LED lit is void.
TOO_SLOW_MS = 2000

# How long the result stays on the screen before the next round can start, in milliseconds.
RESULT_HOLD_MS = 1500

# After the first edge of a press, further edges for this long are contact bounce and are ignored.
BOUNCE_MS = 30

# The ring buffer holds the last five reaction times.
HISTORY_SIZE = 5

# The four states of a round. Only one is active at a time.
STATE_IDLE = 0      # waiting for a press to start a round
STATE_WAITING = 1   # LED dark, the random delay is running
STATE_GO = 2        # LED lit, the timer is running
STATE_RESULT = 3    # the round is over, a short pause before the next one

state = STATE_IDLE

# The moment the current state began, from ticks_ms().
state_start_ms = 0

# The random delay chosen for this round, in milliseconds.
wait_ms = 0

# The ring buffer of recent reactions, where the next one goes, and how many slots hold a real value so far.
recent = [0] * HISTORY_SIZE
next_slot = 0
recent_count = 0

# The best reaction of the session. Zero means there is none yet.
best_ms = 0
rounds_done = 0

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
led = Pin(LED_PIN, Pin.OUT, value=0)
buzzer = PWM(Pin(BUZZER_PIN), freq=BUZZER_HZ, duty_u16=0)

# Start the random number generator from the chip's hardware source, so every session plays different delays.
random.seed(int.from_bytes(os.urandom(4), "little"))

# State for the button and for the buzzer's beep sequence.
last_reading = 1
last_press_ms = 0

beeps_left = 0
beep_sounding = False
beep_change_ms = 0
beep_on_ms = 0
beep_gap_ms = 0


def button_pressed():
    """Returns True once for each press, at the first edge. The reaction is timed from that edge, so the script does
    not wait for the contact to settle before it takes the time."""
    global last_reading, last_press_ms

    reading = button.value()
    now = time.ticks_ms()

    pressed = (last_reading == 1 and reading == 0 and time.ticks_diff(now, last_press_ms) > BOUNCE_MS)
    if pressed:
        last_press_ms = now

    last_reading = reading
    return pressed


def start_beeps(count, on_ms, gap_ms):
    """Starts a series of beeps without waiting. update_beeps() plays it out on later passes of the main loop."""
    global beeps_left, beep_on_ms, beep_gap_ms, beep_sounding, beep_change_ms

    beeps_left = count
    beep_on_ms = on_ms
    beep_gap_ms = gap_ms
    beep_sounding = True
    beep_change_ms = time.ticks_ms()
    buzzer.duty_u16(BUZZER_DUTY)


def update_beeps():
    """Switches the buzzer on and off in step with the series that start_beeps() began."""
    global beeps_left, beep_sounding, beep_change_ms

    if beeps_left == 0:
        return

    now = time.ticks_ms()

    if beep_sounding:
        if time.ticks_diff(now, beep_change_ms) >= beep_on_ms:
            buzzer.duty_u16(0)
            beep_sounding = False
            beep_change_ms = now
            beeps_left -= 1
    elif time.ticks_diff(now, beep_change_ms) >= beep_gap_ms:
        buzzer.duty_u16(BUZZER_DUTY)
        beep_sounding = True
        beep_change_ms = now


def enter_state(new_state):
    """Moves to a new state and does what that state needs once, on the way in. The time of the move is kept in
    state_start_ms, and for STATE_GO that time is the start of the reaction."""
    global state, state_start_ms, wait_ms

    state = new_state
    state_start_ms = time.ticks_ms()

    if new_state == STATE_IDLE:
        led.value(0)

    elif new_state == STATE_WAITING:
        led.value(0)
        wait_ms = random.randint(MIN_WAIT_MS, MAX_WAIT_MS)
        print("get ready, press the button the moment the LED lights")

    elif new_state == STATE_GO:
        led.value(1)
        start_beeps(1, 150, 0)

    elif new_state == STATE_RESULT:
        led.value(0)


def record_reaction(reaction_ms):
    """Stores one reaction in the ring buffer, updates the best time and prints the round."""
    global next_slot, recent_count, best_ms, rounds_done

    # The new value goes over the oldest one once the buffer is full. The % wraps the slot number back to 0.
    recent[next_slot] = reaction_ms
    next_slot = (next_slot + 1) % HISTORY_SIZE
    if recent_count < HISTORY_SIZE:
        recent_count += 1

    rounds_done += 1
    if best_ms == 0 or reaction_ms < best_ms:
        best_ms = reaction_ms

    # The average covers only the slots that hold a real value.
    total = 0
    for i in range(recent_count):
        total += recent[i]
    average = total // recent_count

    print("round {}: {} ms   best {} ms   average of last {}: {} ms".format(
        rounds_done, reaction_ms, best_ms, recent_count, average))


print()
print("reaction timer: press the button to start a round")
enter_state(STATE_IDLE)

while True:
    pressed = button_pressed()
    update_beeps()
    elapsed = time.ticks_diff(time.ticks_ms(), state_start_ms)

    if state == STATE_IDLE:
        if pressed:
            enter_state(STATE_WAITING)

    elif state == STATE_WAITING:
        if pressed:
            # A press while the LED is still dark is a false start.
            print("false start, round void")
            start_beeps(2, 80, 80)
            enter_state(STATE_RESULT)
        elif elapsed >= wait_ms:
            enter_state(STATE_GO)

    elif state == STATE_GO:
        if pressed:
            # state_start_ms holds the moment the LED lit, so the elapsed time is the reaction.
            record_reaction(elapsed)
            enter_state(STATE_RESULT)
        elif elapsed >= TOO_SLOW_MS:
            print("too slow, round void")
            enter_state(STATE_RESULT)

    elif state == STATE_RESULT:
        # Presses are ignored here, so a button held down cannot start the next round by accident.
        if elapsed >= RESULT_HOLD_MS:
            print("press the button to start a round")
            enter_state(STATE_IDLE)
