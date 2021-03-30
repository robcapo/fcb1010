from enum import Enum
from threading import Timer
from typing import Callable
import logging
import time
import asyncio
import queue


logger = logging.getLogger(__name__)

# Types of events that can happen to a foot switch on the pedal
class EventType(Enum):
	# Physical events, foot switch went down or up
	DOWN 			= 1 << 0
	UP 				= 1 << 1

	# Abstract events based on the timing of downs and ups
	PRESS 			= 1 << 3
	LONG_PRESS 		= 1 << 4
	DOUBLE_PRESS 	= 1 << 5

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

# An event that happens to a foot switch
class FootSwitchEvent(object):
	def __init__(self, switch, event_type):
		self.switch = switch
		self.type = event_type

	def __str__(self):
		return "FootSwitchEvent: {} {}".format(self.switch.name, self.type.name)


class FootSwitchEventBus(object):
	def __init__(self):
		self._subscribers = {switch: {} for switch in FootSwitch}
		self._is_down = {switch: False for switch in FootSwitch}
		self._double_press_switch = None
		self._long_press_timers = {switch: None for switch in FootSwitch}

	def subscribe(self, event_type, footswitch, callback):
		self._subscribers[footswitch][event_type] = callback

	def _notify(self, event):
		logger.info(event)
		if event.type in self._subscribers[event.switch]:
			self._subscribers[event.switch][event.type]()


	def midi_callback(self, byte1, byte2, byte3, *a):
		if byte1 == 176:
			if byte2 == 104:
				self._down_callback(byte3)
			elif byte2 == 105:
				self._up_callback(byte3)

	def _down_callback(self, value):
		switch = value_to_switch(value)
		self._is_down[switch] = True
		self._notify(FootSwitchEvent(switch, EventType.DOWN))

		def long_press_notification():
			if self._is_down[switch]:
				self._notify(FootSwitchEvent(switch, EventType.LONG_PRESS))
		self._long_press_timers[switch] = Timer(1.0, long_press_notification)
		self._long_press_timers[switch].start()

		if self._double_press_switch == switch:
			self._notify(FootSwitchEvent(switch, EventType.DOUBLE_PRESS))
		else:
			def double_press_reset():
				if self._double_press_switch == switch:
					self._double_press_switch = None
			self._double_press_switch = switch
			Timer(1.0, double_press_reset).start()

	def _up_callback(self, value):
		switch = value_to_switch(value)
		self._is_down[switch] = False
		if self._long_press_timers[switch] is not None:
			self._long_press_timers[switch].cancel()
			del self._long_press_timers[switch]
		self._notify(FootSwitchEvent(switch, EventType.UP))

class Notifier:
	LONG_PRESS_DURATION = 0.8
	DOUBLE_PRESS_DURATION = 0.5

	def __init__(self, event_types: list[EventType], callback: Callable[[FootSwitchEvent], None]):
		self._event_types = event_types
		self._callback = callback
		self._down_event = asyncio.Event()
		self._up_event = asyncio.Event()

	def down_callback(self) -> None:
		self._down_event.set()

	def up_callback(self) -> None:
		self._up_event.set()

	async def start(self) -> None:
		while True:
			self._down_event.wait()
			self._down_event.reset()
			self.notify(EventType.DOWN)

			asyncio.create_task(self.notify_up(!bool(self._event_types & EventType.DOUBLE_PRESS)))
			asyncio.create_task(self.notify_long_press())
			if self._event_types & EventType.DOUBLE_PRESS:
				asyncio.create_task(self.notify_press_or_double_press())

	async def notify_up(self, notify_press: bool) -> None:
		self._up_event.wait()
		self._up_event.reset()
		self.notify(EventType.UP)
		if notify_press:
			self.notify(EventType.PRESS)

	async def notify_long_press(self) -> None:
		try:
			asyncio.wait_for(self._up_event, LONG_PRESS_DURATION)
		except:
			# if up hasn't occurred over duration, it was a long press
			self.notify(EventType.LONG_PRESS)

	async def notify_press_or_double_press(self):
		try:
			asyncio.wait_for(self._down_event, DOUBLE_PRESS_DURATION)
			self.notify(EventType.DOUBLE_PRESS)
		except:
			self.notify(EventType.PRESS)

	def notify(self, event_type):
		if self._event_types & event_type:
			self._callback()




def value_to_switch(value: int) -> FootSwitch:
	switch = {
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
	}

	return switch[value]