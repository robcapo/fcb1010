from .footswitch import Layout, FootSwitch, EventType, top_row
from .board import Mode
from .led import LEDController
from functools import partial
import Live
import logging

CHAN = 7
NOTE_ON = 0x90 | CHAN
NOTE_OFF = 0x80 | CHAN

logger = logging.getLogger(__name__)

class LoopMode(Mode):
	"""
	Controls two Looper Devices. The problem with this controller is that it can only
	set the state of the Looper device via Live's API. This will only work when the
	Live Set is playing.
	"""
	def __init__(self, leds: LEDController):
		super(LoopMode, self).__init__(leds)
		self._leds = leds
		self._song = Live.Application.get_application().get_document()
		self._song.add_metronome_listener(self._metronome_changed)
		self._metronome_changed()
		self._looper1 = MaxLooper()
		self._looper2 = MaxLooper()
		self._bars_param = None

	def get_layout(self):
		l = Layout()
		# looper buttons
		l.listen(FootSwitch.ONE, EventType.DOWN, self._looper1.start)
		l.listen(FootSwitch.THREE, EventType.DOWN, self._looper2.start)
		
		# bar quantization
		l.listen(FootSwitch.SIX, EventType.PRESS, partial(self._set_bars, 0))
		l.listen(FootSwitch.SEVEN, EventType.PRESS, partial(self._set_bars, 1))
		l.listen(FootSwitch.EIGHT, EventType.PRESS, partial(self._set_bars, 2))
		l.listen(FootSwitch.NINE, EventType.PRESS, partial(self._set_bars, 3))
		l.listen(FootSwitch.TEN, EventType.PRESS, partial(self._set_bars, 4))

		# tap tempo
		def tap(*a):
			self._song.tap_tempo()
		l.listen(FootSwitch.FIVE, EventType.DOWN, tap)
		l.listen(FootSwitch.FIVE, EventType.LONG_PRESS, self._toggle_metronome)
		return l

	def _metronome_changed(self):
		if self._song.metronome:
			self._leds.on(FootSwitch.FIVE.led_value())
		else:
			self._leds.off(FootSwitch.FIVE.led_value())

	def _toggle_metronome(self, *a):
		self._song.metronome = not self._song.metronome

	def _set_bars(self, value, *a):
		self._looper1.set_bars(value)
		self._looper2.set_bars(value)

	def _update_bars(self):
		for ind, fs in enumerate(top_row()):
			if ind == self._bars_param.value:
				self._leds.on(fs.led_value())
			else:
				self._leds.off(fs.led_value())


	def set_track(self, track):
		for rack in track.devices:
			if not isinstance(rack, Live.RackDevice.RackDevice):
				continue
			if not rack.can_have_chains:
				continue
			if "#loop" not in rack.name:
				continue

			for device in rack.chains[0].devices:
				self._looper1.set_device(device)
				logger.info("Found device {}".format(device.class_name))
				logger.info("--- Looper methods ----\n{}\n---------".format(dir(device)))
				for p in device.parameters:
					logger.info("Parameter: {} min {} max {} value {}".format(p.name, p.min, p.max, p.value))
					if p.name == "bars":
						p.add_value_listener(self._update_bars)
						self._bars_param = p
						self._update_bars()

			for device in rack.chains[1].devices:
				self._looper2.set_device(device)

	def print_looper(self):
		for p in self._looper.parameters:
			logger.info("Parameter: {} {}".format(p.name, p.value))

class MaxLooper:
	def __init__(self):
		self._device = None
		self._enable = None
		self._bars = None

	def set_device(self, device):
		self._device = device
		for p in self._device.parameters:
			if p.name == "enable":
				self._enable = p
			if p.name == "bars":
				self._bars = p

	def set_bars(self, value):
		self._bars.value = value

	def start(self, *a):
		if self._device is None:
			return
		self._enable.value = 1


class Looper:
	# the Looper's parameter that gets / sets its state
	STATE_PARAMETER_IND = 1

	STATE_STOPPED = 0
	STATE_RECORDING = 1
	STATE_PLAYING = 2
	STATE_OVERDUBBING = 3

	def __init__(self, song):
		self._looper = None
		self._song = song

	def set_looper(self, looper):
		if device.class_name != "Looper":
			raise RuntimeError("{} is a {}, not a Looper".format(device.name, device.class_name))
		self._looper = looper

	def left(self, *a):
		if not self._song.is_playing:
			self._song.continue_playing()
		state = self._looper.parameters[STATE_PARAMETER_IND]
		if state.value == STATE_RECORDING:
			state.value = STATE_STOPPED
		else:
			state.value = STATE_RECORDING

	def right(self, *a):
		if not self._song.is_playing:
			self._song.continue_playing()
		state = self._looper.parameters[STATE_PARAMETER_IND]
		if state.value == STATE_OVERDUBBING:
			state.value = STATE_STOPPED
		else:
			state.value = STATE_OVERDUBBING