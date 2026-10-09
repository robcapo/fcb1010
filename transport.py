from time import time
from .footswitch import FootSwitch, Layout, EventType
from .led import LEDController
import Live
import logging


logger = logging.getLogger(__name__)

class Metronome:
	"""
	Component that can be used as a tap tempo, and when
	press & held, will toggle the metronome state. If
	turning on the metronome, it will also make sure that
	the transport is playing.
	"""
	def __init__(self, footswitch: FootSwitch, leds: LEDController):
		self._song = Live.Application.get_application().get_document()
		self._leds = leds
		self._footswitch = footswitch
		self._song.add_metronome_listener(self._update)
		self._times = []
		self._update()

	def get_layout(self):
		l = Layout()
		l.listen(self._footswitch, EventType.DOWN, self.tapped)
		l.listen(self._footswitch, EventType.LONG_PRESS, self.held)
		return l

	def tapped(self, *a):
		t = time()
		if len(self._times) > 0:
			if t - self._times[len(self._times) - 1] > 2:
				self._times = []
		self._times.append(t)
		if len(self._times) > 2:
			tempo = 120 / (self._times[len(self._times) - 1] - self._times[len(self._times) - 3])
			# Live only accepts tempos in this range
			self._song.tempo = min(max(tempo, 20.0), 999.0)


	def held(self, *a):
		self._song.metronome = not self._song.metronome
		if self._song.metronome and not self._song.is_playing:
			self._song.continue_playing()
		
	def disconnect(self):
		if self._song.metronome_has_listener(self._update):
			self._song.remove_metronome_listener(self._update)

	def _update(self):
		if self._song.metronome:
			self._leds.on(self._footswitch.led_value())
		else:
			self._leds.off(self._footswitch.led_value())