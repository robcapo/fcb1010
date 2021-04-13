from typing import Callable
from ableton.v2.base.dependency import depends
from functools import partial
import threading
import logging
from time import sleep

logger = logging.getLogger(__name__)

ON_CC = 106
OFF_CC = 107

FAST_BLINK = .3
SLOW_BLINK = .8

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
	"""
	def __init__(self, send_cc, initialize_off = []):
		self._send_cc = send_cc
		self._kill_events = {}
		self._event_locks = {}
		self._last_commands = {}
		self._is_active = True
		for value in initialize_off:
			self.off(value)

	def copy(self, initialize_off = []):
		return LEDController(self._send_cc, initialize_off)

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
		def cb():
			self._blink(value, speed)
		threading.Thread(target = cb).start()

	@command
	def blink_off(self, value, speed = SLOW_BLINK):
		self._kill(value)
		def cb():
			self._blink(value, speed, False)
		threading.Thread(target = cb).start()

	def activate(self):
		self._is_active = True
		for f in self._last_commands.values():
			f()

	def deactivate(self):
		self._is_active = False
		for value in self._kill_events.keys():
			self._kill(value)

	def _on(self, value):
		self._send_cc(ON_CC, value)

	def _off(self, value):
		self._send_cc(OFF_CC, value)

	def _blink(self, value, speed, on = True):
		"""Blink the LED either on or off"""
		cb1 = self._on if on else self._off
		cb2 = self._off if on else self._on
		if value not in self._kill_events:
			self._kill_events[value] = threading.Event()
			self._event_locks[value] = threading.Lock()
		self._kill_events[value].clear()
		while not self._kill_events[value].is_set():
			self._event_locks[value].acquire()
			cb1(value)
			self._event_locks[value].release()
			if self._kill_events[value].wait(.1):
				break
			self._event_locks[value].acquire()
			cb2(value)
			self._event_locks[value].release()
			if self._kill_events[value].wait(speed):
				break

	def _kill(self, value):
		if value in self._kill_events:
			self._event_locks[value].acquire()
			self._kill_events[value].set()
			self._event_locks[value].release()

