"""
@file       11f_Light_Beam_Alarm.py
@brief      A light-beam alarm with arming. The LED on IO38 shines on the photoresistor on IO4 and the pair is
            the beam. A short press of the button arms the alarm, with a 10 second countdown to leave. When the
            countdown ends the script measures the beam and from then on sounds a siren if the light on the sensor
            stays below 60 percent of that level for three reads in a row. Holding the button for one second
            disarms it. The onboard LED shows the state: green is disarmed, yellow is arming, red is alarm.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC, PWM
import neopixel
import time

# The button is on IO21 with the internal pull-up, the photoresistor divider on IO4, the beam LED on IO38 and the
# buzzer's transistor on IO48. The status LED is the one built into the board, on IO2.
BUTTON_PIN = 21
LIGHT_PIN = 4
BEAM_LED_PIN = 38
BUZZER_PIN = 48
RGB_PIN = 2

# From T17. Yours will be a different number. The siren warbles between this pitch and a lower one.
BUZZER_HZ = 2700
BUZZER_LOW_HZ = 2200
BUZZER_DUTY = 32768

# How bright the status LED is, from 0 to 255. It is bright at full value, so it stays low.
STATUS_BRIGHTNESS = 32

# The time to leave the room after arming, and how long the button must be held to count as a long press.
ARMING_MS = 10000
LONG_PRESS_MS = 1000

# After the first edge of a press or a release, further edges for this long are contact bounce and are ignored.
BOUNCE_MS = 30

# The beam is read every 20 ms. Three low reads in a row, 60 ms, trigger the alarm, so a flicker does not.
SAMPLE_MS = 20
LOW_READS_TO_TRIGGER = 3

# The alarm triggers below this percentage of the calibrated beam level.
TRIGGER_PERCENT = 60

# The calibration averages this many reads. A beam below MIN_BEAM_COUNTS means the LED is not aimed at the sensor.
CALIBRATION_READS = 16
MIN_BEAM_COUNTS = 300

# The siren changes pitch this often, in milliseconds.
WARBLE_MS = 200

# The four states of the alarm. Only one is active at a time.
STATE_DISARMED = 0
STATE_ARMING = 1
STATE_ARMED = 2
STATE_ALARM = 3

# What the button just did. A short press is reported on release, a long press as soon as the second is up.
NO_PRESS = 0
SHORT_PRESS = 1
LONG_PRESS = 2

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
beam_led = Pin(BEAM_LED_PIN, Pin.OUT, value=0)
light_sensor = ADC(Pin(LIGHT_PIN), atten=ADC.ATTN_11DB)
rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)
buzzer = PWM(Pin(BUZZER_PIN), freq=BUZZER_HZ, duty_u16=0)

state = STATE_DISARMED
state_start_ms = 0

# The calibrated beam level, the level below which the alarm triggers, and the latest read.
beam_level = 0
trigger_level = 0
last_level = 0

last_sample_ms = 0
low_reads = 0

# State for the button, the arming chirp and the siren.
button_down = False
long_reported = False
button_down_ms = 0
button_up_ms = 0

last_chirp_second = -1
chirping = False
chirp_end_ms = 0
siren_pitch_hz = 0


def read_button():
    """Reads the button and reports a short or a long press. A press is accepted at its first edge, and edges that
    follow within BOUNCE_MS are ignored."""
    global button_down, long_reported, button_down_ms, button_up_ms

    is_down = (button.value() == 0)
    now = time.ticks_ms()

    if is_down and not button_down:
        # The button has just gone down, unless this is bounce right after a release.
        if time.ticks_diff(now, button_up_ms) > BOUNCE_MS:
            button_down = True
            button_down_ms = now
            long_reported = False

    elif is_down and button_down:
        # Still held. Report the long press once, the moment the second is up.
        if not long_reported and time.ticks_diff(now, button_down_ms) >= LONG_PRESS_MS:
            long_reported = True
            return LONG_PRESS

    elif not is_down and button_down:
        # Released, unless this is bounce right after the press.
        if time.ticks_diff(now, button_down_ms) > BOUNCE_MS:
            button_down = False
            button_up_ms = now
            if not long_reported:
                return SHORT_PRESS

    return NO_PRESS


def start_chirp(duration_ms):
    """Plays one short chirp without waiting. update_sound() ends it."""
    global chirping, chirp_end_ms

    buzzer.freq(BUZZER_HZ)
    buzzer.duty_u16(BUZZER_DUTY)
    chirping = True
    chirp_end_ms = time.ticks_add(time.ticks_ms(), duration_ms)


def update_sound():
    """Ends a chirp when its time is up, and warbles the siren while the alarm is on."""
    global chirping, siren_pitch_hz

    now = time.ticks_ms()

    if state == STATE_ALARM:
        # The pitch flips every WARBLE_MS. It is set only when it changes, so the tone is not restarted on every pass.
        pitch = BUZZER_HZ if (now // WARBLE_MS) % 2 == 0 else BUZZER_LOW_HZ
        if pitch != siren_pitch_hz:
            siren_pitch_hz = pitch
            buzzer.freq(pitch)
            buzzer.duty_u16(BUZZER_DUTY)
        return

    if chirping and time.ticks_diff(now, chirp_end_ms) >= 0:
        buzzer.duty_u16(0)
        chirping = False


def show_status(shown):
    """Shows the state on the board's own LED. Armed is dark on purpose, so nothing tells an intruder the beam is
    live."""
    if shown == STATE_DISARMED:
        rgb[0] = (0, STATUS_BRIGHTNESS, 0)
    elif shown == STATE_ARMING:
        rgb[0] = (STATUS_BRIGHTNESS, STATUS_BRIGHTNESS, 0)
    elif shown == STATE_ARMED:
        rgb[0] = (0, 0, 0)
    else:
        rgb[0] = (STATUS_BRIGHTNESS, 0, 0)
    rgb.write()


def calibrate_beam():
    """Measures the beam by averaging a few reads and works out the trigger level. Returns False when the beam is too
    weak to use, which usually means the LED is not pointing at the sensor."""
    global beam_level, trigger_level

    total = 0
    for _ in range(CALIBRATION_READS):
        total += light_sensor.read()
        time.sleep_ms(2)

    beam_level = total // CALIBRATION_READS
    trigger_level = beam_level * TRIGGER_PERCENT // 100

    if beam_level < MIN_BEAM_COUNTS:
        print("cannot arm: the beam reads only {}, aim the LED at the photoresistor".format(beam_level))
        return False

    return True


def enter_state(new_state):
    """Moves to a new state and does what that state needs once, on the way in."""
    global state, state_start_ms, last_chirp_second, low_reads, siren_pitch_hz, chirping

    state = new_state
    state_start_ms = time.ticks_ms()
    show_status(new_state)

    if new_state == STATE_DISARMED:
        beam_led.value(0)
        buzzer.duty_u16(0)
        chirping = False
        print("state: DISARMED")

    elif new_state == STATE_ARMING:
        # The beam goes on now, so it is steady by the time it is measured.
        beam_led.value(1)
        last_chirp_second = -1
        print("state: ARMING, leave now, 10 s to go")

    elif new_state == STATE_ARMED:
        low_reads = 0
        print("state: ARMED, beam level {}, alarm below {}".format(beam_level, trigger_level))

    elif new_state == STATE_ALARM:
        siren_pitch_hz = 0
        chirping = False
        print("state: ALARM, beam broken, level {}".format(last_level))


print()
print("beam alarm ready: press the button to arm it, hold it for 1 s to disarm")
enter_state(STATE_DISARMED)

while True:
    press = read_button()
    now = time.ticks_ms()
    elapsed = time.ticks_diff(now, state_start_ms)

    if state == STATE_DISARMED:
        if press == SHORT_PRESS:
            enter_state(STATE_ARMING)

    elif state == STATE_ARMING:
        # One slow chirp each second, counted by how many whole seconds have passed.
        second = elapsed // 1000
        if second != last_chirp_second:
            last_chirp_second = second
            start_chirp(60)

        if press == SHORT_PRESS:
            # A press during the countdown cancels it.
            enter_state(STATE_DISARMED)
        elif elapsed >= ARMING_MS:
            # The countdown is over, so measure the beam. If it is too weak, go back to disarmed.
            if calibrate_beam():
                enter_state(STATE_ARMED)
            else:
                enter_state(STATE_DISARMED)
                start_chirp(400)

    elif state == STATE_ARMED:
        if press == LONG_PRESS:
            enter_state(STATE_DISARMED)
        elif time.ticks_diff(now, last_sample_ms) >= SAMPLE_MS:
            # Read the beam on a fixed beat. A low read adds one to the count and a good read sets it back to zero.
            last_sample_ms = now
            last_level = light_sensor.read()

            if last_level < trigger_level:
                low_reads += 1
            else:
                low_reads = 0

            if low_reads >= LOW_READS_TO_TRIGGER:
                enter_state(STATE_ALARM)

    elif state == STATE_ALARM:
        # Only a long press silences the siren. The beam coming back does nothing.
        if press == LONG_PRESS:
            enter_state(STATE_DISARMED)

    update_sound()
