from typing import Callable
from ableton.v2.base.dependency import depends
import threading
import logging
from time import sleep

logger = logging.getLogger(__name__)

ON_CC = 106
OFF_CC = 107

FAST_BLINK = .3
SLOW_BLINK = .8

class LEDController:
	def __init__(self, send_cc):
		self._send_cc = send_cc
		self._kill_events = {}

	def on(self, value):
		self._kill(value)
		self._on(value)

	def off(self, value):
		self._kill(value)
		self._off(value)

	def blink_on(self, value, speed = SLOW_BLINK):
		self._kill(value)
		def cb():
			self._blink(value, speed)
		threading.Thread(target = cb).start()

	def blink_off(self, value, speed = SLOW_BLINK):
		self._kill(value)
		def cb():
			self._blink(value, speed, False)
		threading.Thread(target = cb).start()

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
		self._kill_events[value].clear()
		while not self._kill_events[value].is_set():
			cb1(value)
			if self._kill_events[value].wait(.1):
				break
			cb2(value)
			if self._kill_events[value].wait(speed):
				break

	def _kill(self, value):
		if value in self._kill_events:
			self._kill_events[value].set()

