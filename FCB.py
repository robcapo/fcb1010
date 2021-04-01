from ableton.v2.control_surface import ControlSurface
from enum import Enum
from .Events import FootSwitchEventBus, FootSwitch, EventType, Notifier
import logging
import Live
from random import randint
import threading
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
		logger.info("Initializing FcbSurface")
		logger.info("Python version")
		logger.info(sys.version)
		logger.info("Version info.")
		logger.info(sys.version_info)
		self.__c_instance = c_instance

		with self.component_guard():
			self._event_bus = FootSwitchEventBus()
			self._event_bus.subscribe(1, FootSwitch.ONE, EventType.PRESS, self.rand_light_on)
			self._event_bus.subscribe(1, FootSwitch.TWO, EventType.PRESS, self.rand_light_off)
			self._event_bus.subscribe(1, FootSwitch.THREE, EventType.PRESS | EventType.DOUBLE_PRESS | EventType.LONG_PRESS, self.lights_on)
			self._event_bus.subscribe(1, FootSwitch.FOUR, EventType.PRESS, self.all_lights_off)
			self._event_bus.set_mode(1)

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

	def rand_light_on(self, *a):
		self.light_on(randint(0, 9))
	
	def rand_light_off(self, *a):
		self.light_off(randint(0, 9))

	def all_lights_off(self, *a):
		for i in range(1, 23):
			if i == 10:
				i = 0
			self.light_off(i)

	def lights_on(self, event_type):
		logger.info("Event type was {}".format(event_type))
		if event_type == EventType.PRESS:
			self.rand_light_on()
		elif event_type == EventType.DOUBLE_PRESS:
			self.all_lights_off()
		elif event_type == EventType.LONG_PRESS:
			for i in range(1, 23):
				if i == 10:
					i = 0
				self.light_on(i)
