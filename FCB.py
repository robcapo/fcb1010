from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import InputControlElement, MIDI_CC_TYPE
from _Framework.Signal import Slot
from enum import Enum
from AFCB.Events import FootSwitchEventBus, FootSwitch, EventType
import logging
import Live
from random import randint
from threading import Timer
import sys

logger = logging.getLogger(__name__)

LEFT_EXPRESSION_ID = 102
RIGHT_EXPRESSION_ID = 103
FOOTSWITCH_DOWN_ID = 104
FOOTSWITCH_UP_ID = 105
LED_ON_ID = 106
LED_OFF_ID = 107

CC_MSG = 0xB0

class FcbSurface(ControlSurface):

	def __init__(self, c_instance, *a, **k):
		(super(FcbSurface, self).__init__)(c_instance, *a, **k)
		self.log_message("Initializing FcbSurface")
		self.log_message("Python version")
		self.log_message(sys.version)
		self.log_message("Version info.")
		self.log_message(sys.version_info)
		self.__c_instance = c_instance

		with self.component_guard():
			self._event_bus = FootSwitchEventBus()
			self._event_bus.subscribe(EventType.DOWN, FootSwitch.ONE, self.rand_light_on)
			self._event_bus.subscribe(EventType.DOWN, FootSwitch.TWO, self.rand_light_off)
			self._event_bus.subscribe(EventType.DOWN, FootSwitch.THREE, self.all_lights_on)
			self._event_bus.subscribe(EventType.DOWN, FootSwitch.FOUR, self.all_lights_off)

			self.add_received_midi_listener(self._event_bus.midi_callback)


	def build_midi_map(self, midi_map_handle):
		Live.MidiMap.forward_midi_cc(self.__c_instance.handle(), midi_map_handle, 0, 104) # button down
		Live.MidiMap.forward_midi_cc(self.__c_instance.handle(), midi_map_handle, 0, 105) # button up
		super(FcbSurface, self).build_midi_map(midi_map_handle)

	def light_on(self, value):
		self.send_cc(LED_ON_ID, value)

	def light_off(self, value):
		self.send_cc(LED_OFF_ID, value)

	def send_cc(self, identifier, value):
		self.__c_instance.send_midi((CC_MSG, identifier, value))

	def input_callback(self, *a, **k):
		self.log_message("Callback called with {} and {}".format(a, k))

	def rand_light_on(self):
		self.light_on(randint(0, 9))
	
	def rand_light_off(self):
		self.light_off(randint(0, 9))

	def all_lights_off(self):
		for i in range(1, 23):
			if i == 10:
				i = 0
			self.light_off(i)

	def all_lights_on(self):
		for i in range(1, 23):
			if i == 10:
				i = 0
			self.light_on(i)
