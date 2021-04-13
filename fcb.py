from ableton.v2.control_surface import ControlSurface
from .footswitch import FootSwitchEventBus
from .led import LEDController
from .session import Session
import logging
import Live
import sys

logger = logging.getLogger(__name__)

LEFT_EXPRESSION_ID = 102
RIGHT_EXPRESSION_ID = 103
FOOTSWITCH_DOWN_ID = 104
FOOTSWITCH_UP_ID = 105

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
			leds = LEDController(self.send_cc)
			event_bus = FootSwitchEventBus()
			self._session = Session(leds, event_bus)

			self.add_received_midi_listener(event_bus.midi_callback)


	def build_midi_map(self, midi_map_handle):
		Live.MidiMap.forward_midi_cc(self.__c_instance.handle(), midi_map_handle, 0, 104) # button down
		Live.MidiMap.forward_midi_cc(self.__c_instance.handle(), midi_map_handle, 0, 105) # button up
		super(FcbSurface, self).build_midi_map(midi_map_handle)

	def send_cc(self, identifier, value):
		self.__c_instance.send_midi((CC_MSG, identifier, value))
