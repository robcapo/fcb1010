from .led import LEDController
from .footswitch import FootSwitchEventBus, Layout, FootSwitch, EventType
from .session import Session
from functools import partial
import logging
import Live

logger = logging.getLogger(__name__)

class Mode:
	def __init__(self, leds: LEDController):
		self.leds = leds

	def activate(self):
		self.leds.activate()

	def deactivate(self):
		self.leds.deactivate()

	def set_layout_changed_callback(self, callback):
		pass

	def get_layout(self):
		raise NotImplementedError()

	def set_track(self, track: Live.Track.Track):
		"""Called with the track to control, or None if there isn't one"""
		raise NotImplementedError()

	def disconnect(self):
		"""Remove any listeners. Called when the control surface is disconnected"""
		pass

class Board:
	def __init__(self, leds: LEDController, footswitch_events: FootSwitchEventBus):
		self._leds = leds
		self._modes = []
		self._current_mode = None
		self._current_mode_layout = None
		self._mode_led_values = [20, 21, 22]
		for val in self._mode_led_values:
			self._leds.off(val)
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
		mode.set_layout_changed_callback(partial(self._refresh_layout, len(self._modes)))
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
			self._footswitch_events.uninstall(self._current_mode_layout)
			if self._current_mode < len(self._mode_led_values):
				self._leds.off(self._mode_led_values[self._current_mode])
		self._modes[ind].activate()
		self._install_mode_layout(ind)
		self._current_mode = ind
		if self._current_mode < len(self._mode_led_values):
			self._leds.on(self._mode_led_values[self._current_mode])

	def disconnect(self):
		self._session.disconnect()
		for mode in self._modes:
			mode.disconnect()

	def _set_track(self, track):
		if track == self._current_track:
			return
		self._current_track = track
		for mode in self._modes:
			mode.set_track(track)

	def _tracks_updated(self):
		tracks = self._session.get_tracks()
		# just use the first track for now. If there are no tracks, clear the modes
		self._set_track(tracks[0] if len(tracks) > 0 else None)

	def _refresh_layout(self, ind):
		if self._current_mode == ind:
			self._footswitch_events.uninstall(self._current_mode_layout)
			self._install_mode_layout(ind)

	def _install_mode_layout(self, ind):
		self._current_mode_layout = self._modes[ind].get_layout()
		self._footswitch_events.install(self._current_mode_layout)
