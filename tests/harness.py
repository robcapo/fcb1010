"""
Drives the control surface the way Live and the pedal would: MIDI in,
scheduler ticks, and a record of the MIDI the script sends back.
"""
import fcb1010
from fcb1010.footswitch import FootSwitch, Notifier
from fcb1010.led import ON_CC, OFF_CC
from fcb1010.display import TENS_CC, ONES_CC, OFF_VALUE

from fakes import live

CC = 0xB0
DOWN_CC = 104
UP_CC = 105
LEFT_EXPRESSION_CC = 102
RIGHT_EXPRESSION_CC = 103

# The CC value the pedal sends for each switch
SWITCH_VALUES = {fs: (0 if fs is FootSwitch.TEN else fs.value) for fs in FootSwitch}
SWITCH_VALUES[FootSwitch.UP] = 10
SWITCH_VALUES[FootSwitch.DOWN] = 11

LONG_PRESS_TICKS = Notifier.LONG_PRESS_TICKS + 1
DOUBLE_PRESS_TICKS = Notifier.DOUBLE_PRESS_TICKS + 1


class CInstance:
	"""Live's c_instance: how the script sends MIDI"""
	def __init__(self):
		self.sent = []

	def send_midi(self, midi_bytes):
		self.sent.append(tuple(midi_bytes))

	def handle(self):
		return self


class MidiMap:
	def __init__(self):
		self.forwarded_ccs = set()


class Rig:
	def __init__(self, song):
		self.song = song
		self.c_instance = CInstance()
		self.surface = None
		self.midi_map = None
		# Seconds, for tap tempo
		self.clock = 1000.0

	# Lifecycle

	def connect(self):
		self.surface = fcb1010.create_instance(self.c_instance)
		self.midi_map = MidiMap()
		self.surface.build_midi_map(self.midi_map)
		self.tick()
		return self

	def disconnect(self, check_listeners=True):
		surface, self.surface = self.surface, None
		surface.disconnect()
		if check_listeners:
			leaks = [
				"{} {}: {}".format(type(o).__name__, getattr(o, "_values", {}).get("name", ""), {
					k: v for k, v in o._listeners.items() if v})
				for o in self.song._all_objects() if not o._deleted and o._listener_count() > 0]
			assert leaks == [], "Listeners left connected after disconnect:\n" + "\n".join(leaks)
			assert surface._midi_listeners == []

	def tick(self, n=1):
		for _ in range(n):
			self.clock += 0.1
			self.surface.update_display()

	# The pedal

	def send_cc(self, cc, value):
		"""MIDI from the pedal. Live only passes on CCs the script forwarded"""
		if (0, cc) in self.midi_map.forwarded_ccs:
			self.surface.receive_midi((CC, cc, value))

	def down(self, fs):
		self.send_cc(DOWN_CC, SWITCH_VALUES[fs])

	def up(self, fs):
		self.send_cc(UP_CC, SWITCH_VALUES[fs])

	def press(self, fs, settle=True):
		"""A short press. settle waits out the double press window"""
		self.down(fs)
		self.tick()
		self.up(fs)
		if settle:
			self.tick(DOUBLE_PRESS_TICKS)

	def long_press(self, fs):
		self.down(fs)
		self.tick(LONG_PRESS_TICKS)
		self.up(fs)
		self.tick()

	def double_press(self, fs):
		self.down(fs)
		self.up(fs)
		self.tick()
		self.down(fs)
		self.up(fs)
		self.tick(2)

	def expression(self, side, value):
		self.send_cc(LEFT_EXPRESSION_CC if side == "left" else RIGHT_EXPRESSION_CC, value)

	# What the pedal shows

	def led_value(self, led):
		"""True / False for the last on / off sent to an LED, None if never sent"""
		state = None
		for status, cc, value in self.c_instance.sent:
			if status == CC and value == led and cc in (ON_CC, OFF_CC):
				state = cc == ON_CC
		return state

	def led(self, fs):
		return self.led_value(fs.led_value())

	def led_states(self, fs, ticks=20):
		"""The states an LED goes through over some ticks, to spot blinking"""
		states = set()
		for _ in range(ticks):
			self.tick()
			states.add(self.led(fs))
		return states

	def display(self):
		chars = {}
		for status, cc, value in self.c_instance.sent:
			if status == CC and cc in (TENS_CC, ONES_CC):
				chars[cc] = " " if value >= OFF_VALUE else chr(ord("A") + value)
		return (chars.get(TENS_CC, " ") + chars.get(ONES_CC, " ")).strip()

	def errors(self):
		return list(live.errors)
