from .led import LEDController
from .footswitch import FootSwitchEventBus, Layout, FootSwitch, EventType
from .session import Session
import logging


logger = logging.getLogger(__name__)

class Mode:
	def __init__(self, leds: LEDController):
		self.leds = leds

	def activate(self):
		self.leds.activate()

	def deactivate(self):
		self.leds.deactivate()

	def get_layout(self):
		raise NotImplementedError()

	def set_track(self):
		raise NotImplementedError()

class Board:
	def __init__(self, leds: LEDController, footswitch_events: FootSwitchEventBus):
		self._leds = leds
		self._modes = []
		self._current_mode = None
		self._mode_led_values = [20, 21, 22]
		self._footswitch_events = footswitch_events
		l = Layout()
		l.listen(FootSwitch.UP, EventType.PRESS, self._prev_mode)
		l.listen(FootSwitch.DOWN, EventType.PRESS, self._next_mode)
		self._footswitch_events.install(l)
		
		self._current_track = None
		self._session = Session()
		self._session.add_callback(self._tracks_updated)
		self._tracks_updated()


	def add_mode(self, mode: Mode):
		self._modes.append(mode)

		if self._current_track is not None:
			mode.set_track(self._current_track)

		if self._current_mode is None:
			self._next_mode()

	def _next_mode(self, *a):
		logger.info("Next mode")
		if len(self._modes) == 0:
			return
		if self._current_mode is None:
			mode = 0
		else:
			mode = self._current_mode + 1
			if mode == len(self._modes):
				mode = 0
		self._set_mode(mode)

	def _prev_mode(self, *a):
		logger.info("Previous mode")
		if len(self._modes) == 0:
			return
		if self._current_mode is None:
			mode = len(self._modes) - 1
		else:
			mode = self._current_mode - 1
			if mode == -1:
				mode = len(self._modes) - 1
		self._set_mode(mode)

	def _set_mode(self, ind):
		if self._current_mode == ind:
			logger.info("Not changing mode. It's already set.")
			return
		if self._current_mode is not None:
			self._modes[self._current_mode].deactivate()
			self._footswitch_events.uninstall(self._modes[self._current_mode].get_layout())
			if self._current_mode < len(self._mode_led_values):
				self._leds.off(self._mode_led_values[self._current_mode])
		self._modes[ind].activate()
		self._footswitch_events.install(self._modes[ind].get_layout())
		self._current_mode = ind
		if self._current_mode < len(self._mode_led_values):
			self._leds.on(self._mode_led_values[self._current_mode])

	def _set_track(self, track):
		if track == self._current_track:
			return
		self._current_track = track
		for mode in self._modes:
			mode.set_track(track)

	def _tracks_updated(self):
		for track in self._session.get_tracks():
			self._set_track(track)
			# just use the first track for now
			break
