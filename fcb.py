from ableton.v2.control_surface import ControlSurface
from .footswitch import FootSwitchEventBus, numbered_footswitches
from .led import LEDController
from .effects_mode import EffectsMode
from .loop_mode import LoopMode
from .session_mode import SessionMode
from .racks_controller import RacksControllerMode
from .board import Board
import logging
import Live
import sys
import inspect

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
		logger.info("Executable {}".format(sys.executable))
		logger.info("Path {}".format(sys.path))
		self.__c_instance = c_instance

		with self.component_guard():
			leds = LEDController(self.send_cc)
			event_bus = FootSwitchEventBus()
			
			self._board = Board(leds, event_bus)
			self._board.add_mode(RacksControllerMode(leds.copy([f.led_value() for f in numbered_footswitches()]), self.schedule_message))
			# self._board.add_mode(EffectsMode(leds.copy([f.led_value() for f in numbered_footswitches()])))
			# self._board.add_mode(LoopMode(leds.copy([f.led_value() for f in numbered_footswitches()])))
			self._board.add_mode(SessionMode(leds.copy([f.led_value() for f in numbered_footswitches()]), self.schedule_message))

			self.add_received_midi_listener(event_bus.midi_callback)
			logger.info("Added midi received listener")


	def build_midi_map(self, midi_map_handle):
		Live.MidiMap.forward_midi_cc(self.__c_instance.handle(), midi_map_handle, 0, FOOTSWITCH_DOWN_ID) # button down
		Live.MidiMap.forward_midi_cc(self.__c_instance.handle(), midi_map_handle, 0, FOOTSWITCH_UP_ID) # button up
		Live.MidiMap.forward_midi_cc(self.__c_instance.handle(), midi_map_handle, 0, LEFT_EXPRESSION_ID) # button up
		Live.MidiMap.forward_midi_cc(self.__c_instance.handle(), midi_map_handle, 0, RIGHT_EXPRESSION_ID) # button up
		super(FcbSurface, self).build_midi_map(midi_map_handle)

	def send_cc(self, identifier, value):
		self.__c_instance.send_midi((CC_MSG, identifier, value))

def inspect_and_log(obj, indent = 0):
	for name, memb in inspect.getmembers(obj):
		logger.info("{}{}{}".format(indent*"  ", name, memb))
		if inspect.ismodule(memb):
			inspect_and_log(memb, indent + 1)
