from functools import partial
import logging

logger = logging.getLogger(__name__)

ON_CC = 106
OFF_CC = 107

# Blink timings are in scheduler ticks (Live ticks every ~100ms)
BLINK_FLASH = 1
FAST_BLINK = 3
SLOW_BLINK = 8

"""
Stores the last fn call for each LED. If controller is active,
also executes it.
"""
def command(f):
	def wrapper(self, value, *a, **k):
		self._last_commands[value] = partial(f, self, value, *a, **k)
		if self._is_active:
			self._last_commands[value]()
	return wrapper

class LEDController:
	"""
	Controls LEDs on the board. Controller can be deactivated, which means it
	will only keep track of the last command for each LED (and not actually
	send the CC to turn it on or off). When activated, it will draw the
	current state of each LED.

	Controller also keeps track of last command when active, so activate
	can also be used to redraw the LEDs, e.g. if the board lost power
	temporarily.

	Blinking is driven by Live's scheduler so that MIDI is only ever sent
	from Live's main thread.
	"""
	def __init__(self, send_cc, scheduler, is_active = True, initialize_off = ()):
		self._send_cc = send_cc
		self._scheduler = scheduler
		# Incremented per LED to stop any blink that is in progress
		self._generations = {}
		self._last_commands = {}
		self._is_active = is_active
		for value in initialize_off:
			self.off(value)

	def copy(self, initialize_off = ()):
		return LEDController(self._send_cc, self._scheduler, False, initialize_off)

	@command
	def on(self, value):
		self._kill(value)
		self._on(value)

	@command
	def off(self, value):
		self._kill(value)
		self._off(value)

	@command
	def blink_on(self, value, speed = SLOW_BLINK):
		self._kill(value)
		self._blink(value, speed, True, self._generations[value], True)

	@command
	def blink_off(self, value, speed = SLOW_BLINK):
		self._kill(value)
		self._blink(value, speed, False, self._generations[value], True)

	def activate(self):
		self._is_active = True
		for f in list(self._last_commands.values()):
			f()

	def deactivate(self):
		self._is_active = False
		for value in list(self._generations.keys()):
			self._kill(value)

	def _on(self, value):
		self._send_cc(ON_CC, value)

	def _off(self, value):
		self._send_cc(OFF_CC, value)

	def _blink(self, value, speed, on, generation, flash):
		"""
		Blink the LED either on or off. A blink is a short flash of the
		blink state, followed by a longer period of the opposite state.
		"""
		if generation != self._generations.get(value) or not self._is_active:
			return
		if flash == on:
			self._on(value)
		else:
			self._off(value)
		self._scheduler(
			BLINK_FLASH if flash else speed,
			partial(self._blink, value, speed, on, generation, not flash))

	def _kill(self, value):
		self._generations[value] = self._generations.get(value, 0) + 1
