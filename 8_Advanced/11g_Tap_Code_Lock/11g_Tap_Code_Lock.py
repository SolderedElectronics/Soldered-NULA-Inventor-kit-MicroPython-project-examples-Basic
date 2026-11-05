"""
@file       11g_Tap_Code_Lock.py
@brief      A tap code lock with a servo latch. The secret is three taps on the button with a short gap and then a
            long gap between them. The script records the taps, waits 1.5 seconds after the last one and compares
            the pattern with the code. A right code turns the servo to the open position for 5 seconds. A wrong
            one gives a long low tone, and three wrong tries in a row lock the button for 10 seconds while the LED
            blinks fast.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM
import time

# The button is on IO21 with the internal pull-up, the LED on IO38, the servo on IO47 and the buzzer's transistor on
# IO48.
BUTTON_PIN = 21
LED_PIN = 38
SERVO_PIN = 47
BUZZER_PIN = 48

# From T17. Yours will be a different number. A wrong code plays the lower pitch.
BUZZER_HZ = 2700
BUZZER_LOW_HZ = 800
BUZZER_DUTY = 32768

# From T19. Yours will be different numbers. The servo only turns, nothing is mounted on it, so the arm position is
# what you watch.
LOCKED_PULSE_US = 1000
OPEN_PULSE_US = 2000
SERVO_FREQ = 50

# A gap shorter than SHORT_GAP_MS counts as short and one longer than LONG_GAP_MS counts as long. A gap in between is
# unclear and never matches the code.
SHORT_GAP_MS = 400
LONG_GAP_MS = 700

# This long after the last tap, the attempt is over and gets judged.
TAP_TIMEOUT_MS = 1500

OPEN_MS = 5000
LOCKOUT_MS = 10000
MAX_WRONG_IN_A_ROW = 3

# After the first edge of a press, further edges for this long are contact bounce and are ignored.
BOUNCE_MS = 30

# The kinds of gap between two taps, and their names for printing.
GAP_SHORT = 0
GAP_LONG = 1
GAP_UNCLEAR = 2
GAP_NAMES = ["short", "long", "unclear"]

# The secret code as a list of gaps. Three taps make two gaps: short, then long. Change the list to change the code.
SECRET_CODE = [GAP_SHORT, GAP_LONG]

# The three states of the lock.
STATE_LOCKED = 0
STATE_OPEN = 1
STATE_LOCKOUT = 2

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
led = Pin(LED_PIN, Pin.OUT, value=0)
servo = PWM(Pin(SERVO_PIN), freq=SERVO_FREQ)
buzzer = PWM(Pin(BUZZER_PIN), freq=BUZZER_HZ, duty_u16=0)

state = STATE_LOCKED
state_start_ms = 0

# The attempt in progress: the gap after each tap, and when the last tap was. The number of taps is len(gaps) + 1,
# or zero when no attempt has started.
gaps = []
tap_count = 0
last_tap_ms = 0

attempt_number = 0
wrong_in_a_row = 0

# State for the button and for the buzzer's tone.
last_reading = 1
last_press_ms = 0
tone_sounding = False
tone_end_ms = 0


def button_pressed():
    """Returns True once for each press, at the first edge."""
    global last_reading, last_press_ms

    reading = button.value()
    now = time.ticks_ms()

    pressed = (last_reading == 1 and reading == 0 and time.ticks_diff(now, last_press_ms) > BOUNCE_MS)
    if pressed:
        last_press_ms = now

    last_reading = reading
    return pressed


def play_tone(hz, duration_ms):
    """Plays a tone without waiting. update_tone() ends it."""
    global tone_sounding, tone_end_ms

    buzzer.freq(hz)
    buzzer.duty_u16(BUZZER_DUTY)
    tone_sounding = True
    tone_end_ms = time.ticks_add(time.ticks_ms(), duration_ms)


def update_tone():
    """Silences the buzzer when the tone's time is up."""
    global tone_sounding

    if tone_sounding and time.ticks_diff(time.ticks_ms(), tone_end_ms) >= 0:
        buzzer.duty_u16(0)
        tone_sounding = False


def move_servo(pulse_us):
    """Turns the servo arm to a pulse width. duty_ns() takes the pulse width in nanoseconds."""
    servo.duty_ns(pulse_us * 1000)


def classify_gap(gap_ms):
    """Sorts the time between two taps into short, long or unclear."""
    if gap_ms < SHORT_GAP_MS:
        return GAP_SHORT
    if gap_ms > LONG_GAP_MS:
        return GAP_LONG
    return GAP_UNCLEAR


def record_tap():
    """Records one tap. From the second tap on, the time since the previous tap is sorted into a gap and stored."""
    global tap_count, last_tap_ms

    now = time.ticks_ms()

    if tap_count > 0:
        gaps.append(classify_gap(time.ticks_diff(now, last_tap_ms)))

    tap_count += 1
    last_tap_ms = now

    # A very short tick tells the player that the tap was heard.
    play_tone(BUZZER_HZ, 25)


def matches_code():
    """Returns True when the attempt has the right number of taps and every gap matches the code in order."""
    return tap_count == len(SECRET_CODE) + 1 and gaps == SECRET_CODE


def enter_state(new_state):
    """Moves to a new state and does what that state needs once, on the way in."""
    global state, state_start_ms, wrong_in_a_row

    state = new_state
    state_start_ms = time.ticks_ms()

    if new_state == STATE_LOCKED:
        move_servo(LOCKED_PULSE_US)
        led.value(0)

    elif new_state == STATE_OPEN:
        move_servo(OPEN_PULSE_US)
        led.value(1)

    elif new_state == STATE_LOCKOUT:
        move_servo(LOCKED_PULSE_US)
        wrong_in_a_row = 0


def judge_attempt():
    """Judges the attempt that just ended: prints it, then opens the lock, counts a wrong try or starts the
    lockout."""
    global attempt_number, tap_count, wrong_in_a_row, gaps

    attempt_number += 1
    correct = matches_code()

    # Print how many taps were heard and the gaps between them.
    gap_text = " ".join(GAP_NAMES[g] for g in gaps) if gaps else "none"
    print("attempt {}: taps {}, gaps {}".format(attempt_number, tap_count, gap_text), end="")

    # The attempt is over, so the next tap starts a new one.
    tap_count = 0
    gaps = []

    if correct:
        wrong_in_a_row = 0
        print(", correct, open for 5 s")
        play_tone(BUZZER_HZ, 300)
        enter_state(STATE_OPEN)
        return

    wrong_in_a_row += 1
    print(", wrong code ({} wrong in a row)".format(wrong_in_a_row))
    play_tone(BUZZER_LOW_HZ, 600)

    if wrong_in_a_row >= MAX_WRONG_IN_A_ROW:
        print("lockout: 3 wrong tries in a row, locked for 10 s")
        enter_state(STATE_LOCKOUT)


print()
print("tap code lock ready: tap short, then long, on the button to open it")
enter_state(STATE_LOCKED)

while True:
    pressed = button_pressed()
    now = time.ticks_ms()
    elapsed = time.ticks_diff(now, state_start_ms)

    if state == STATE_LOCKED:
        if pressed:
            record_tap()

        # Once 1.5 s pass with no new tap, the attempt is judged.
        if tap_count > 0 and time.ticks_diff(now, last_tap_ms) >= TAP_TIMEOUT_MS:
            judge_attempt()

    elif state == STATE_OPEN:
        if elapsed >= OPEN_MS:
            print("locked again")
            enter_state(STATE_LOCKED)

    elif state == STATE_LOCKOUT:
        # The LED blinks fast and the button is ignored until the time is up.
        led.value(1 if (now // 100) % 2 == 0 else 0)

        if elapsed >= LOCKOUT_MS:
            print("lockout over, ready for a new attempt")
            enter_state(STATE_LOCKED)

    update_tone()
