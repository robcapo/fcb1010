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

	def led_value(self):
		if self in [FootSwitch.UP, FootSwitch.DOWN]:
			raise RuntimeError("Tried to get LED for {}, which doesn't exist.".format(self.name))
		if self is FootSwitch.TEN:
			return 0
		return self.value


# Types of events that can happen to a foot switch on the pedal
class EventType(IntEnum):
	# Physical events, foot switch went down or up
	DOWN 			= 1 << 0
	UP 				= 1 << 1

	# Abstract events based on the timing of downs and ups
	PRESS 			= 1 << 2
	LONG_PRESS 		= 1 << 3
	DOUBLE_PRESS 	= 1 << 4

class FootSwitchEventType:
	"""An event that happens to a foot switch"""

	def __init__(self, switch, event_type):
		self.switch = switch
		self.type = event_type

	def __str__(self):
		return "FootSwitchEventType: {} {}".format(self.switch.name, self.type.name)

class FootSwitchEventSpec:
	def __init__(self):
		self._events = []

	def add_event(self, fset: FootSwitchEventType):
		self._events.append(fset)
		return self

	def get_events(self):
		return self._events


class FootSwitchEventBus:
	"""
	Handles all the events of the 10 numbered foot switches + UP + DOWN.
	Does not handle expression pedal events.
	"""

	def __init__(self):
		self._notifiers = {switch: Notifier() for switch in FootSwitch}

	def get_notifier(self, footswitch: FootSwitch):
		return self._notifiers[footswitch]

	def midi_callback(self, byte1, byte2, byte3, *a):
		if byte1 == CC_BYTE:
			if byte2 == DOWN_BYTE:
				self._notifiers[value_to_switch(byte3)].down_callback()
			elif byte2 == UP_BYTE:
				self._notifiers[value_to_switch(byte3)].up_callback()

class Notifier:
	LONG_PRESS_DURATION = 0.8
	DOUBLE_PRESS_DURATION = 0.5

	def __init__(self):
		self._callbacks = {}
		self._down_event = threading.Event()
		self._up_event = threading.Event()
		self._killed = threading.Event()
		threading.Thread(target=self.run).start()

	def __del__(self):
		self._killed.set()

	def set_callback(self, event_types: EventType, callback: Callable[[EventType], None]) -> None:
		for event in EventType:
			if event_types & event:
				self._callbacks[event] = callback

	def clear_callback(self, event_types: EventType):
		for event in EventType:
			if event_types & event:
				del self._callbacks[event]

	def run(self) -> None:
		logger.info("Running event loop")
		while not self._killed.is_set():
			self._await_down()
			up = self._await_up(self.LONG_PRESS_DURATION)
			if not up:
				self._notify(EventType.LONG_PRESS)
				self._await_up()
				continue

			press_event = EventType.PRESS

			if EventType.DOUBLE_PRESS in self._callbacks:
				if self._await_down(self.DOUBLE_PRESS_DURATION):
					press_event = EventType.DOUBLE_PRESS
					self._await_up()

			self._notify(press_event)

		logger.info("Event loop killed")


	def down_callback(self) -> None:
		self._down_event.set()

	def up_callback(self) -> None:
		self._up_event.set()
			
	def _await_down(self, timeout=None):
		down = self._down_event.wait(timeout)
		if down:
			self._notify(EventType.DOWN)
			self._down_event.clear()
		return down

	def _await_up(self, timeout=None):
		up = self._up_event.wait(timeout)
		if up:
			self._notify(EventType.UP)
			self._up_event.clear()
		return up

	def _notify(self, event_type):
		if event_type in self._callbacks:
			self._callbacks[event_type](event_type)

def numbered_footswitches():
	return [
		FootSwitch.ONE,
		FootSwitch.TWO,
		FootSwitch.THREE,
		FootSwitch.FOUR,
		FootSwitch.FIVE,
		FootSwitch.SIX,
		FootSwitch.SEVEN,
		FootSwitch.EIGHT,
		FootSwitch.NINE,
		FootSwitch.TEN,
	]

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