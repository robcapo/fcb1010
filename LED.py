from typing import Callable
from ableton.v2.base.dependency import depends
import threading
import logging
from time import sleep

logger = logging.getLogger(__name__)

ON_CC = 106
OFF_CC = 107

FAST = .3
SLOW = .8

class LEDController:
	def __init__(self, send_cc):
		self._send_cc = send_cc
		self._kill = threading.Event()

	def on(self, value):
		self._kill.set()
		self._on(value)

	def off(self, value):
		self._kill.set()
		self._off(value)

	def blink_on(self, value, speed = SLOW):
		def cb():
			self._blink(value, speed)
		threading.Thread(target = cb).start()

	def blink_off(self, value, speed = SLOW):
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
		self._kill.set()
		self._kill.clear()
		while not self._kill.is_set():
			cb1(value)
			sleep(.1)
			cb2(value)
			sleep(speed)
