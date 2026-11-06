"""
@file       7.1_Thermostat_With_Relay_And_Alarm.py
@brief      A cooling thermostat. The pot sets the temperature you want, the TMP117 measures the room, and the
            relay switches a fan on the moment the room goes above your number. It runs on for five seconds after
            the room drops back below, so a reading wobbling across the setpoint cannot chatter the relay. The LED
            and the buzzer both follow the relay, chirping once every two seconds for as long as it is closed, and
            the buzzer warbles continuously instead if the sensor stops answering.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C, ADC, PWM
import time

# The Soldered drivers for the TMP117 and the relay board, found in the lib folder of this repository.
from tmp117 import TMP117
from Relay import Relay, CHANNEL1

"""
The whole example in one line: above the number on the pot, the fan runs; five seconds below it, the fan stops.

Cup a hand over the sensor and the relay clicks in straight away. Let go, and once the reading has been back under
your number for five unbroken seconds it clicks out again.

The parts came from earlier tasks: TMP117 and relay from T22 and T23, the pot from T9, the LED from T2, the
buzzer and its transistor from T17. The 330 Ohm on the LED is still not optional.
"""
SDA_PIN = 8
SCL_PIN = 9

TMP117_ADDRESS = 0x49
RELAY_ADDRESS = 0x30

POT_PIN = 4
FAN_LED_PIN = 38
BUZZER_PIN = 48

# The resonant frequency you measured in T17. Yours will not be this one.
BUZZER_HZ = 2700

# Setpoint range the pot maps across, in degrees. Room temperature wants to be somewhere in the middle of it.
SETPOINT_MIN_C = 15.0
SETPOINT_MAX_C = 35.0

"""
How long the room has to stay below the setpoint before the fan may stop. Switching on is immediate; the wait
restarts every time the temperature goes back above, so five continuous seconds is what it takes.

This is a hysteresis band done in time instead of in degrees, so that the number on the pot stays the number: the
fan comes on the instant you pass it. A band would have moved one of those two points somewhere else. Real
extractor fans use a run-on timer for the same reason, and T23 builds the band version on this same relay.
"""
OFF_DELAY_MS = 5000

# How often the sensor is read and how often a status line is printed.
SENSOR_INTERVAL_MS = 250
PRINT_INTERVAL_MS = 1000

"""
The two alarm patterns, deliberately nothing like each other, because two alarms that sound the same are one alarm:

  fan running     one short chirp every two seconds, for as long as the LED is lit
  sensor fault    a continuous warble, on and off every 300 ms

The duty of 25 % is the compromise T17 found: loudness peaks at half duty, and this carries across a room without
being unbearable next to your hand.
"""
OVER_CHIRP_ON_MS = 120
OVER_CHIRP_OFF_MS = 1880
FAULT_PHASE_MS = 300
BUZZER_DUTY = (25 * 65535) // 100

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

# 0x49 because JP2 on the breakout ties ADD0 high.
tmp = TMP117(i2c, TMP117_ADDRESS)

# No setAveraging() call. Every configuration call writes the sensor's EEPROM, and the TMP117 already sits at its
# 0.0078 degree step with averaging off, as T22 measured.
tmp.init(None)

relay = Relay(i2c, RELAY_ADDRESS)
relay.relayControl(CHANNEL1, 0)

fan_led = Pin(FAN_LED_PIN, Pin.OUT, value=0)
pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)

buzzer = PWM(Pin(BUZZER_PIN), freq=BUZZER_HZ, duty_u16=0)

# Nothing here calls sleep for longer than a moment, so every part that needs to wait keeps its own deadline and
# the loop runs thousands of times a second regardless of what any one part is doing.
setpoint_c = 22.0
temperature_c = 0.0
sensor_ok = False

fan_on = False
below_since_ms = 0

buzzer_sounding = False
buzzer_phase_ms = 0

last_sensor_ms = 0
last_print_ms = 0

print()
print("cooling thermostat running: above the pot's number the fan runs, below it the fan stops")

while True:
    # Part 1: read the pot. This happens on every pass, because it is cheap and there is no reason to make the knob
    # feel laggy.
    raw = pot.read()
    target = SETPOINT_MIN_C + (raw / 4095.0) * (SETPOINT_MAX_C - SETPOINT_MIN_C)

    # Light smoothing, the exponential moving average from T13, so the setpoint does not jitter.
    setpoint_c = setpoint_c + 0.05 * (target - setpoint_c)

    # Part 2: read the sensor, but only when its 250 ms are up.
    if time.ticks_diff(time.ticks_ms(), last_sensor_ms) >= SENSOR_INTERVAL_MS:
        last_sensor_ms = time.ticks_ms()

        # Check before believing, every time. MicroPython raises when nothing answers, and the device ID catches the
        # case where something answers but is not a TMP117.
        try:
            sensor_ok = (tmp.getDeviceID() == 0x117)
            if sensor_ok:
                temperature_c = tmp.getTemperature()
        except OSError:
            sensor_ok = False

    # Part 3: decide whether the fan runs. The relay, the LED and fan_on are always changed together, so the three
    # can never disagree.
    if not sensor_ok:
        # A failed read is not a temperature of zero, it is an absence of information. Stop the fan and make a noise.
        if fan_on:
            fan_on = False
            relay.relayControl(CHANNEL1, 0)
            fan_led.value(0)
        below_since_ms = 0
    elif temperature_c > setpoint_c:
        # Above the setpoint the fan runs, no delay and no conditions, and any shutdown counting down is forgotten.
        # That is what makes the five seconds have to be continuous.
        below_since_ms = 0

        if not fan_on:
            fan_on = True
            relay.relayControl(CHANNEL1, 1)
            fan_led.value(1)
    else:
        # Below it: note when that started and stop the fan only once the room has stayed under for the whole delay.
        if below_since_ms == 0:
            below_since_ms = time.ticks_ms()

        if fan_on and time.ticks_diff(time.ticks_ms(), below_since_ms) >= OFF_DELAY_MS:
            fan_on = False
            relay.relayControl(CHANNEL1, 0)
            fan_led.value(0)

    # Part 4: the buzzer keeps its own time, which is what lets it beep in a pattern without stopping the relay logic
    # or the sensor reads. A blocking sleep here would freeze the whole thermostat for the length of a beep.
    #
    # The fault wins when both are true, because a temperature you cannot trust is more urgent than one you can. The
    # chirp follows the relay, run-on included, so light, click and sound are one state shown three ways.
    if not sensor_ok:
        # Sensor fault: a continuous warble, switching every 300 ms.
        if time.ticks_diff(time.ticks_ms(), buzzer_phase_ms) >= FAULT_PHASE_MS:
            buzzer_phase_ms = time.ticks_ms()

            if buzzer_sounding:
                buzzer_sounding = False
                buzzer.duty_u16(0)
            else:
                buzzer_sounding = True
                buzzer.duty_u16(BUZZER_DUTY)
    elif fan_on:
        # Fan running: one short chirp, then a long wait. The two halves have different lengths.
        if buzzer_sounding and time.ticks_diff(time.ticks_ms(), buzzer_phase_ms) >= OVER_CHIRP_ON_MS:
            buzzer_phase_ms = time.ticks_ms()
            buzzer_sounding = False
            buzzer.duty_u16(0)
        elif not buzzer_sounding and time.ticks_diff(time.ticks_ms(), buzzer_phase_ms) >= OVER_CHIRP_OFF_MS:
            buzzer_phase_ms = time.ticks_ms()
            buzzer_sounding = True
            buzzer.duty_u16(BUZZER_DUTY)
    else:
        # Nothing to report, so the buzzer is silent.
        if buzzer_sounding:
            buzzer.duty_u16(0)
            buzzer_sounding = False

        # Leave the timestamp stale, so the next alarm starts on its first pass rather than a chirp late.
        buzzer_phase_ms = 0

    # Part 5: print one status line a second.
    if time.ticks_diff(time.ticks_ms(), last_print_ms) >= PRINT_INTERVAL_MS:
        last_print_ms = time.ticks_ms()

        if not sensor_ok:
            print("SENSOR FAULT: nothing answering at 0x49. Fan off, alarm sounding.")
        else:
            fan_text = "off"
            if fan_on:
                fan_text = "ON "

            line = "setpoint {:.2f} C   temperature {:.2f} C   fan {}".format(setpoint_c, temperature_c, fan_text)

            # Signed, so the sign alone tells you what the fan will do.
            line += "   {:.2f} C from the switch point".format(temperature_c - setpoint_c)

            if fan_on and below_since_ms != 0:
                waited = time.ticks_diff(time.ticks_ms(), below_since_ms)
                if waited < OFF_DELAY_MS:
                    line += "   off in {:.1f} s".format((OFF_DELAY_MS - waited) / 1000.0)

            print(line)

"""
Read part 3 of the loop again. Two comparisons and a few lines that switch the relay, and it is a working thermostat.
Everything else here is about not being fooled: a sensor that answers with a device ID before it answers with a
temperature, and a buzzer for when it stops answering.
"""
