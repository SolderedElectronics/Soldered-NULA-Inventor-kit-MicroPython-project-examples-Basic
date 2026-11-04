"""
@file       08i_Melody_Player.py
@brief      Plays a tune stored as two tables, one of note frequencies and one of note lengths, on the buzzer. The
            servo swings between 60 and 120 degrees on every beat, as if it were conducting. Nothing blocks, so
            the notes and the servo both run from the clock.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM
import time

# IO48 drives the transistor under the buzzer through the 10 kOhm resistor, and IO47 carries the servo's signal.
BUZZER_PIN = 48
SERVO_PIN = 47

# The tune, as data. Each note has a frequency in hertz, a length in beats and a name to print. The three lists
# line up, so entry 0 of each describes the first note. Frequencies near 2.7 kHz are where this buzzer is loudest,
# so the tune sits in the sixth octave.
MELODY_HZ = [1319, 1319, 1397, 1568, 1568, 1397, 1319, 1175, 1047, 1047, 1175, 1319, 1319, 1175, 1175]
MELODY_BEATS = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1.5, 0.5, 2]
MELODY_NAMES = ["E6", "E6", "F6", "G6", "G6", "F6", "E6", "D6", "C6", "C6", "D6", "E6", "E6", "D6", "D6"]

# The speed of the tune. At 120 beats a minute one beat lasts 500 ms.
TEMPO_BPM = 120
BEAT_MS = 60000 // TEMPO_BPM

# The buzzer goes quiet this long before each note ends, so that two equal notes in a row sound like two.
GAP_MS = 40

# Half of the full duty range. A square wave that is high half of the time is the loudest this buzzer gets.
HALF_DUTY = 32768

# The two ends of the conductor's swing, in degrees.
ANGLE_LOW = 60
ANGLE_HIGH = 120

# The servo's pulse widths for 0 and 180 degrees. These are the limits you measured in T19.
PULSE_MIN_US = 550
PULSE_MAX_US = 2500

# The servo wants a pulse every 20 ms.
SERVO_FREQ = 50

# The buzzer starts silent, and every note then sets its own frequency. It starts at 1000 Hz rather than 50 Hz so that
# it gets a PWM timer of its own, and a new note never disturbs the servo's 20 ms period.
buzzer = PWM(Pin(BUZZER_PIN), freq=1000, duty_u16=0)
servo = PWM(Pin(SERVO_PIN), freq=SERVO_FREQ)


def write_angle(degrees):
    """Turn the servo to an angle in degrees. The angle becomes a pulse width between your two limits, and duty_ns()
    takes the pulse width directly in nanoseconds."""
    pulse_us = PULSE_MIN_US + degrees * (PULSE_MAX_US - PULSE_MIN_US) // 180
    servo.duty_ns(pulse_us * 1000)


def start_note(index):
    """Start sounding one note from the tables, print its name, and return how long it lasts in milliseconds."""
    buzzer.freq(MELODY_HZ[index])
    buzzer.duty_u16(HALF_DUTY)

    print("{}  {:.1f} beats".format(MELODY_NAMES[index], MELODY_BEATS[index]))

    return int(MELODY_BEATS[index] * BEAT_MS)


# Start the servo at the low end of its swing.
write_angle(ANGLE_LOW)

print("MELODY: Ode to Joy at 120 beats a minute.")

# Start the clock for the first note and the first beat. The beat is set back by one beat length so that the
# servo swings at once.
song_start_ms = time.ticks_ms()
note_index = 0
note_start_ms = song_start_ms
note_ms = start_note(0)
note_sounding = True
last_beat_ms = time.ticks_add(song_start_ms, -BEAT_MS)
servo_high = False

while True:
    now = time.ticks_ms()

    # On every beat, swing the servo to the other end.
    if time.ticks_diff(now, last_beat_ms) >= BEAT_MS:
        last_beat_ms = time.ticks_add(last_beat_ms, BEAT_MS)
        servo_high = not servo_high
        write_angle(ANGLE_HIGH if servo_high else ANGLE_LOW)

    # Just before the note ends, silence the buzzer to leave the small gap between notes.
    if note_sounding and time.ticks_diff(now, note_start_ms) >= note_ms - GAP_MS:
        buzzer.duty_u16(0)
        note_sounding = False

    # When the note is over, move on to the next one, and go back to the first one after the last.
    if time.ticks_diff(now, note_start_ms) >= note_ms:
        # Add the length instead of using the time now, so small delays do not add up over the tune.
        note_start_ms = time.ticks_add(note_start_ms, note_ms)
        note_index += 1

        if note_index >= len(MELODY_HZ):
            print("End of the tune. Starting again.")
            note_index = 0

        note_ms = start_note(note_index)
        note_sounding = True
