"""
@file       03d_Morse_Keyer.py
@brief      Turns the button into a Morse key. A short press is a dot, a long press is a dash, a pause ends the
            letter and the script prints it. A longer silence adds a space. The LED on IO38 follows the button.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

BUTTON_PIN = 21
LED_PIN = 38

# A press shorter than this is a dot, and a press at least this long is a dash.
DASH_MS = 250

# Silence after a release that ends the letter, and silence that adds a space between words.
LETTER_GAP_MS = 700
WORD_GAP_MS = 2000

# Ignore changes that come sooner than this after the last one, so the contact bounce is not counted.
DEBOUNCE_MS = 30

# The longest pattern in the table is five symbols, so five is all the script keeps for one letter.
MAX_SYMBOLS = 5

# The Morse table: every letter and digit. A dictionary maps the pattern of dots and dashes to the character,
# so looking a pattern up is all the decoding there is.
MORSE_TABLE = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
    "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K", ".-..": "L",
    "--": "M", "-.": "N", "---": "O", ".--.": "P", "--.-": "Q", ".-.": "R",
    "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
    "-.--": "Y", "--..": "Z",
    "-----": "0", ".----": "1", "..---": "2", "...--": "3", "....-": "4",
    ".....": "5", "-....": "6", "--...": "7", "---..": "8", "----.": "9",
}

led = Pin(LED_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# The button state machine: is the button down, when did it go down, and when did it last change.
was_pressed = False
pressed_at_ms = 0
last_edge_ms = time.ticks_ms()

# The letter being keyed right now, as a text of dots and dashes, and the time of the last release.
pattern = ""
last_release_ms = time.ticks_ms()

# The message so far, and whether a space is still due after the last letter.
message = ""
space_due = False


# Looks a pattern up in the table and gives back its character, or "?" if the pattern is not in the table.
def decode_pattern(keyed):
    return MORSE_TABLE.get(keyed, "?")


# Adds a dot or a dash to the letter being keyed. A sixth symbol is dropped, because no pattern is that long.
def add_symbol(symbol):
    global pattern
    if len(pattern) < MAX_SYMBOLS:
        pattern = pattern + symbol


# Prints the message so far in quotes, so a trailing space can be seen.
def print_message():
    print('   message: "' + message + '"')


# Decodes the finished letter, prints it with its pattern, and clears the pattern for the next letter.
def finish_letter():
    global pattern, message, space_due

    letter = decode_pattern(pattern)
    message = message + letter

    print(pattern + " = " + letter + '   message: "' + message + '"')

    pattern = ""
    space_due = True


# Adds a space to the message and prints it.
def add_space():
    global message, space_due

    message = message + " "
    print('(space)   message: "' + message + '"')
    space_due = False


print("MORSE: tap for a dot, hold for a dash. 0.7 s of silence ends a letter, 2 s adds a space.")

while True:
    now = time.ticks_ms()

    # The pull-up makes a press read 0, so a pressed button gives True here.
    pressed = (button.value() == 0)

    # Act only when the button changes state and the change is not bounce.
    if pressed != was_pressed and time.ticks_diff(now, last_edge_ms) >= DEBOUNCE_MS:
        was_pressed = pressed
        last_edge_ms = now

        if pressed:
            # The button has just gone down: note the time and show the press on the LED.
            pressed_at_ms = now
            led.value(1)
        else:
            # The button has just come up: the length of the press decides dot or dash.
            led.value(0)
            held_ms = time.ticks_diff(now, pressed_at_ms)
            add_symbol("." if held_ms < DASH_MS else "-")
            last_release_ms = now

    # While the button is up, the silence since the last release decides what happens next.
    if not was_pressed:
        silence_ms = time.ticks_diff(now, last_release_ms)

        if len(pattern) > 0 and silence_ms >= LETTER_GAP_MS:
            finish_letter()
        elif len(pattern) == 0 and space_due and silence_ms >= WORD_GAP_MS:
            add_space()

    time.sleep_ms(5)
