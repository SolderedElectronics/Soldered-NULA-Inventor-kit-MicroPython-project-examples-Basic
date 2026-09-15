"""
@file       4.3_Driving_A_Buzzer_Through_A_Transistor.py
@brief      Drives a passive buzzer through an NPN transistor from the 5 V rail, with a flyback diode.
            Sweeps 500 Hz to 5 kHz to find its resonance, then steps the duty cycle at that frequency.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin, PWM, ADC
import time

"""
IO48 drives the base of the transistor through a 10 kOhm resistor, and the transistor switches the buzzer against
VCC. IO4 reads the pot, the volume knob in MODE_VOLUME.

The transistor is here because the pin cannot do this job: it gives 3.3 V and a few tens of milliamps, while the
coil is a low resistance that will take the whole 5 V rail and as much current as it can get.

The band on the 1N4148 marks the cathode and belongs on the positive side. Fitted the other way round it conducts
all the time and shorts the buzzer out.
"""
DRIVE_PIN = 48
POT_PIN = 4

"""
  MODE_LEVEL       drive it with a steady high level and listen to the silence.
  MODE_SWEEP       500 Hz to 5 kHz over twenty seconds. Note where it gets dramatically louder.
  MODE_DUTY        hold the resonant frequency and step the duty through 5, 10, 25 and 50 %.
  MODE_VOLUME      the same idea with your hand on it: the pot sets the duty, so the pot sets the loudness.
"""
MODE_LEVEL = 0
MODE_SWEEP = 1
MODE_DUTY = 2
MODE_VOLUME = 3

MODE = MODE_VOLUME

# The resonant frequency you measured in MODE_SWEEP. Examples 7.1 and 7.4 want the same number, so it is worth
# writing on the back of the kit box.
RESONANT_HZ = 2700


def duty_percent(pct):
    """MicroPython's PWM duty is 16-bit, so a percentage is scaled to 0-65535."""
    return (pct * 65535) // 100


print()

if MODE == MODE_LEVEL:
    # A passive buzzer is a coil and a metal disc with no oscillator inside, so it needs an alternating signal. A
    # steady high pushes the disc once and holds it: a faint click, then silence, with current flowing throughout.
    drive = Pin(DRIVE_PIN, Pin.OUT)
    drive.value(1)
    print("LEVEL: a steady HIGH. Silence, and current flowing. Do not leave this running.")

    while True:
        time.sleep_ms(1000)

else:
    pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
    buzzer = PWM(Pin(DRIVE_PIN), freq=1000, duty_u16=0)

    if MODE == MODE_SWEEP:
        """
        Listen rather than watch. Somewhere in the range the buzzer gets dramatically louder over a span of a few
        hundred hertz, then drops back. That peak is mechanical resonance: driving the disc at its natural frequency
        makes each push land in step with the movement already happening.

        Write the frequency down. Two buzzers from the same batch will not peak at quite the same place.
        """
        while True:
            print("sweeping 500 Hz to 5000 Hz over 20 seconds")

            for hz in range(500, 5001, 25):
                buzzer.freq(hz)
                buzzer.duty_u16(duty_percent(50))
                print(hz)
                time.sleep_ms(110)

            buzzer.duty_u16(0)
            print("done")
            time.sleep_ms(3000)

    elif MODE == MODE_DUTY:
        # Frequency decides the pitch; duty decides how long the coil is energised each cycle, so roughly how hard
        # the disc is pushed. It gets louder as the duty rises, and the transistor gets warmer with it.
        buzzer.freq(RESONANT_HZ)

        while True:
            for pct in (5, 10, 25, 50):
                print("duty {} %".format(pct))
                buzzer.duty_u16(duty_percent(pct))
                time.sleep_ms(1500)

            # Stop it with a duty of zero, not a level on the pin. A steady level is the MODE_LEVEL case: silent,
            # and drawing current through the coil until something gets warm.
            buzzer.duty_u16(0)
            time.sleep_ms(1500)

            """
            Now take the 1N4148 out and run this again with your finger on the transistor. A coil resists change in
            its current, so switching it off spikes the voltage the other way, hard enough to punch through the
            transistor over time. The diode gives that current a harmless loop to die out in, which is why it is
            fitted backwards relative to the supply and does nothing until the spike arrives. Without it the
            transistor runs noticeably warmer. Put it back.
            """

    else:
        """
        The pot maps to 0 to 50 %, not 0 to 100 %, and that upper limit is the interesting part. A 50 % square wave
        spends half of every cycle pushing the disc and half letting it go, which is the most movement you can get.
        Push the duty higher and the signal approaches the steady level from MODE_LEVEL, so the sound falls away.

        No filtering on the reading: the pot's dozen counts of jitter is under a tenth of a percent of duty here and
        you cannot hear it. Examples that act on a threshold do need the averaging from 2.2.
        """
        buzzer.freq(RESONANT_HZ)
        buzzer.duty_u16(0)
        print("VOLUME: turn the pot. Duty and loudness follow it.")

        while True:
            raw = pot.read()

            pct = (raw * 50) // 4095
            buzzer.duty_u16(duty_percent(pct))

            print("duty {} %".format(pct))

            time.sleep_ms(150)
