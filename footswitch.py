from enum import IntEnum, Enum
from typing import Callable
import logging
import traceback

CC_BYTE = 176
DOWN_BYTE = 104
UP_BYTE = 105
LEFT_EXPR_BYTE = 102
RIGHT_EXPR_BYTE = 103

logger = logging.getLogger(__name__)

# Foot switch identifier
class FootSwitch(Enum):
	ONE 	= 1
	TWO 	= 2
	THREE 	= 3
	FOUR 	= 4
	FIVE 	= 5
	SIX 	= 6
	SEVEN 	= 7
	EIGHT 	= 8
	NINE 	= 9
	TEN 	= 10
	UP 		= 11
	DOWN 	= 12

	def led_value(self):
		if self in [FootSwitch.UP, FootSwitch.DOWN]:
			raise RuntimeError("Tried to get LED for {}, which doesn't exist.".format(self.name))
		if self is FootSwitch.TEN:
			return 0
		return self.value


# Types of events that can happen to a foot switch on the pedal
class EventType(Enum):
	# Physical events, foot switch went down or up
	DOWN 			= 1
	UP 				= 2

	# Abstract events based on the timing of downs and ups
	PRESS 			= 3
	LONG_PRESS 		= 4
	DOUBLE_PRESS 	= 5

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

class Layout:
	"""
	Represents a layout of callbacks for the footswitches on the board.
	"""
	def __init__(self):
		self._callbacks = {}
		self._left_expression_callback = None
		self._right_expression_callback = None

	def listen(self, footswitch: FootSwitch, event_type: EventType, cb):
		if footswitch not in self._callbacks:
			self._callbacks[footswitch] = {}
		self._callbacks[footswitch][event_type] = cb

	def set_left_expression_callback(self, cb):
		self._left_expression_callback = cb

	def set_right_expression_callback(self, cb):
		self._right_expression_callback = cb

	def left_expression_callback(self):
		return self._left_expression_callback

	def right_expression_callback(self):
		return self._right_expression_callback
		
	def get_callbacks(self):
		return self._callbacks

	def union_with(self, other):
		for footswitch, cb_map in other._callbacks.items():
			self._callbacks.setdefault(footswitch, {}).update(cb_map)
		if other._left_expression_callback is not None:
			self._left_expression_callback = other._left_expression_callback
		if other._right_expression_callback is not None:
			self._right_expression_callback = other._right_expression_callback

class FootSwitchEventBus:
	"""
	Handles all the events of the 10 numbered foot switches + UP + DOWN,
	plus the two expression pedals.

	Everything runs on Live's main thread: MIDI arrives via midi_callback,
	and the timing for long / double presses is done with Live's scheduler.
	Live's API isn't thread safe, so callbacks must never run on another thread.
	"""
	def __init__(self, scheduler):
		self._notifiers = {switch: Notifier(scheduler) for switch in FootSwitch}
		self._left_expression = self._noop
		self._right_expression = self._noop

	def install(self, layout: Layout):
		for footswitch, cb_map in layout.get_callbacks().items():
			for event_type, cb in cb_map.items():
				self._notifiers[footswitch].set_callback(event_type, cb)
		if layout.left_expression_callback() is not None:
			self._left_expression = layout.left_expression_callback()
		if layout.right_expression_callback() is not None:
			self._right_expression = layout.right_expression_callback()

	def uninstall(self, layout: Layout):
		for footswitch, cb_map in layout.get_callbacks().items():
			for event_type in cb_map.keys():
				self._notifiers[footswitch].clear_callback(event_type)
		if layout.left_expression_callback() is not None:
			self._left_expression = self._noop
		if layout.right_expression_callback() is not None:
			self._right_expression = self._noop

	def midi_callback(self, byte1, byte2, byte3, *a):
		if byte1 == CC_BYTE:
			if byte2 == DOWN_BYTE:
				switch = value_to_switch(byte3)
				if switch is not None:
					self._notifiers[switch].down()
			elif byte2 == UP_BYTE:
				switch = value_to_switch(byte3)
				if switch is not None:
					self._notifiers[switch].up()
			elif byte2 == LEFT_EXPR_BYTE:
				_call_safely(self._left_expression, byte3)
			elif byte2 == RIGHT_EXPR_BYTE:
				_call_safely(self._right_expression, byte3)

	def _noop(self, val):
		pass

class Notifier:
	"""
	Turns the physical DOWN / UP events of one foot switch into
	PRESS / LONG_PRESS / DOUBLE_PRESS events.

	PRESS fires as soon as the switch comes up, unless a DOUBLE_PRESS
	callback is installed, in which case it waits to see if a second
	press is coming.
	"""
	# Durations are in scheduler ticks (Live ticks every ~100ms)
	LONG_PRESS_TICKS = 8
	DOUBLE_PRESS_TICKS = 5

	_IDLE = 0
	_DOWN = 1 			# down, waiting to see if it's a long press
	_HELD = 2 			# long press already fired, waiting for up
	_WAIT_SECOND = 3 	# up after a short press, waiting for a possible second press
	_SECOND_DOWN = 4 	# second press of a double press is down

	def __init__(self, scheduler):
		self._scheduler = scheduler
		self._callbacks = {}
		self._state = self._IDLE
		# Incremented to invalidate any pending scheduled timeout
		self._generation = 0

	def set_callback(self, event_type: EventType, callback: Callable[[EventType], None]) -> None:
		self._callbacks[event_type] = callback

	def clear_callback(self, event_type: EventType):
		self._callbacks.pop(event_type, None)

	def down(self) -> None:
		self._notify(EventType.DOWN)
		if self._state == self._WAIT_SECOND:
			self._generation += 1
			self._state = self._SECOND_DOWN
		else:
			self._state = self._DOWN
			self._schedule(self.LONG_PRESS_TICKS, self._long_press_timeout)

	def up(self) -> None:
		self._notify(EventType.UP)
		state = self._state
		self._generation += 1
		self._state = self._IDLE
		if state == self._DOWN:
			if EventType.DOUBLE_PRESS in self._callbacks:
				self._state = self._WAIT_SECOND
				self._schedule(self.DOUBLE_PRESS_TICKS, self._double_press_timeout)
			else:
				self._notify(EventType.PRESS)
		elif state == self._SECOND_DOWN:
			self._notify(EventType.DOUBLE_PRESS)

	def _long_press_timeout(self):
		if self._state == self._DOWN:
			self._state = self._HELD
			self._notify(EventType.LONG_PRESS)

	def _double_press_timeout(self):
		if self._state == self._WAIT_SECOND:
			self._state = self._IDLE
			self._notify(EventType.PRESS)

	def _schedule(self, ticks, cb):
		self._generation += 1
		generation = self._generation
		def run():
			if generation == self._generation:
				cb()
		self._scheduler(ticks, run)

	def _notify(self, event_type):
		if event_type in self._callbacks:
			_call_safely(self._callbacks[event_type], event_type)

def _call_safely(cb, *a):
	try:
		cb(*a)
	except Exception:
		logger.error('Caught exception in footswitch callback: {}'.format(traceback.format_exc()))

def bottom_row():
	return [
		FootSwitch.ONE,
		FootSwitch.TWO,
		FootSwitch.THREE,
		FootSwitch.FOUR,
		FootSwitch.FIVE,
	]

def top_row():
	return [
		FootSwitch.SIX,
		FootSwitch.SEVEN,
		FootSwitch.EIGHT,
		FootSwitch.NINE,
		FootSwitch.TEN,
	]

def numbered_footswitches():
	return bottom_row() + top_row()

def value_to_switch(value: int):
	"""Returns the FootSwitch for a CC value, or None if it's not a known switch"""
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
		10: FootSwitch.UP,
		11: FootSwitch.DOWN,
	}.get(value)