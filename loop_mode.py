from .footswitch import Layout
from .board import Mode
from .led import LEDController

class LoopMode(Mode):
	def __init__(self, leds: LEDController):
		super(LoopMode, self).__init__(leds)
		self._leds = leds
		self._track = None

	def get_layout(self):
		return Layout()

	def set_track(self, track):
		self._track = track