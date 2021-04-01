from enum import IntEnum, Enum
from threading import Timer
from typing import Callable
import logging
import time
import threading
import queue

CC_BYTE = 176
DOWN_BYTE = 104
UP_BYTE = 105

logger = logging.getLogger(__name__)

# Types of events that can happen to a foot switch on the pedal
class EventType(IntEnum):
	# Physical events, foot switch went down or up
	DOWN 			= 1 << 0
	UP 				= 1 << 1

	# Abstract events based on the timing of downs and ups
	PRESS 			= 1 << 2
	LONG_PRESS 		= 1 << 3
	DOUBLE_PRESS 	= 1 << 4

# Foot switch identifier
class FootSwitch(Enum):
	ONE = 1
	TWO = 2
	THREE = 3
	FOUR = 4
	FIVE = 5
	SIX = 6
	SEVEN = 7
	EIGHT = 8
	NINE = 9
	TEN = 10
	UP = 11
	DOWN = 12

class FootSwitchEvent(object):
	"""An event that happens to a foot switch"""

	def __init__(self, switch, event_type):
		self.switch = switch
		self.type = event_type

	def __str__(self):
		return "FootSwitchEvent: {} {}".format(self.switch.name, self.type.name)


class FootSwitchEventBus(object):
	"""
	Handles all the events of the 10 numbered foot switches + UP + DOWN.
	Does not handle expression pedal events.
	"""

	def __init__(self):
		self._subscribers = {}
		self._is_down = {switch: False for switch in FootSwitch}
		self._double_press_switch = None
		self._long_press_timers = {switch: None for switch in FootSwitch}
		self._mode = None

	def subscribe(self, mode, footswitch: FootSwitch, event_types: EventType, callback: Callable[[FootSwitchEvent], None]):
		if self._mode is not None:
			raise RuntimeError("No messing with subscribers once the mode is set.")

		if mode not in self._subscribers:
			self._subscribers[mode] = {}

		self._subscribers[mode][footswitch] = Notifier(event_types, callback)

	def set_mode(self, mode):
		if mode not in self._subscribers:
			raise RuntimeError("Could not find mode {}. Modes are {}".format(mode, self._subscribers.keys()))
		self._mode = mode

	def midi_callback(self, byte1, byte2, byte3, *a):
		if byte1 == CC_BYTE:
			if byte2 == DOWN_BYTE:
				switch = value_to_switch(byte3)
				if switch in self._subscribers[self._mode]:
					self._subscribers[self._mode][switch].down_callback()
			elif byte2 == UP_BYTE:
				switch = value_to_switch(byte3)
				if switch in self._subscribers[self._mode]:
					self._subscribers[self._mode][switch].up_callback()
		

class Notifier:
	LONG_PRESS_DURATION = 0.8
	DOUBLE_PRESS_DURATION = 0.5

	def __init__(self, event_types: EventType, callback: Callable[[FootSwitchEvent], None]):
		self._event_types = event_types
		self._callback = callback
		self._down_event = threading.Event()
		self._up_event = threading.Event()
		self._killed = threading.Event()
		threading.Thread(target=self.run).start()

	def __del__(self):
		self._killed.set()

	def down_callback(self) -> None:
		self._down_event.set()

	def up_callback(self) -> None:
		self._up_event.set()

	def run(self) -> None:
		logger.info("Running event loop")
		while not self._killed.is_set():
			self._await_down()
			up = self._await_up(self.LONG_PRESS_DURATION)
			if not up:
				self.notify(EventType.LONG_PRESS)
				self._await_up()
				continue

			press_event = EventType.PRESS

			if self._event_types & EventType.DOUBLE_PRESS:
				if self._await_down(self.DOUBLE_PRESS_DURATION):
					press_event = EventType.DOUBLE_PRESS
					self._await_up()

			self.notify(press_event)

		logger.info("Event loop killed")

			
	def _await_down(self, timeout=None):{}
		down = self._down_event.wait(timeout)
		if down:
			self.notify(EventType.DOWN)
			self._down_event.clear()
		return down

	def _await_up(self, timeout=None):
		up = self._up_event.wait(timeout)
		if up:
			self.notify(EventType.UP)
			self._up_event.clear()
		return up

	def notify(self, event_type):
		if self._event_types & event_type:
			self._callback(event_type)


def value_to_switch(value: int) -> FootSwitch:
	return {
		1: FootSwitch.ONE,
		2: FootSwitch.TWO,
		3: FootSwitch.THREE,
		4: FootSwitch.FOUR,
		5: FootSwitch.FIVE,
		6: FootSwitch.SIX,
		7: FootSwitch.SEVEN,
		8: FootSwitch.EIGHT,
		9: FootSwitch.NINE,
		0: FootSwitch.TEN,
		10: FootSwitch.DOWN,
		11: FootSwitch.UP,
	}[value]