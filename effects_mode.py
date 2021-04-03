from .led import LEDController
from .events import FootSwitchEventBus, FootSwitchEventType, FootSwitch, EventType, numbered_footswitches
from .sesison import Track
import Live

class EffectsMode:
	def __init__(self, leds: LEDController, track: Track):
		self._leds = leds
		self._stomps = []
		self._patch = None
		self.set_track(track)

	def set_track(self, track: Track):
		self._track.remove_devices_listener()

	def _update_devices(self):
		pass

	def get_events(self) -> list[FootSwitchEventType]:
		return [FootSwitchEventType(fs, EventType.PUSH) for fs in numbered_footswitches()]

	def footswitch_event_callback(self, event: FootSwitchEventType):
		pass