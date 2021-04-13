from .footswitch import FootSwitchEventBus
from .led import LEDController
from .effects_mode import EffectsMode
import Live
import logging


logger = logging.getLogger(__name__)

class Session:
	def __init__(self, leds: LEDController, footswitch_events: FootSwitchEventBus):
		self._leds = leds
		self._tracks = {}
		self._fx = EffectsMode(leds)
		footswitch_events.install(self._fx.get_layout())
		self._song = Live.Application.get_application().get_document()
		self._song.add_tracks_listener(self._update_tracks)
		self._update_tracks()

	def _update_tracks(self):
		if len(self._song.tracks) > len(self._tracks):
			for track in self._song.tracks:
				if track._live_ptr not in self._tracks:
					logger.info("Adding new track {} with name {}".format(track._live_ptr, track.name))
					self._tracks[track._live_ptr] = Track(track, self._fx)
		else:
			tracks = {t._live_ptr: t for t in self._song.tracks}
			for track_ptr in list(self._tracks.keys()):
				if track_ptr not in tracks:
					logger.info("Removing track")
					del self._tracks[track_ptr]


class Track:
	def __init__(self, track: Live.Track.Track, fx: EffectsMode):
		self._track = track
		self._controlling = False
		self._fx = fx
		self._track.add_name_listener(self._update_name)
		self._update_name()

	def _update_name(self):
		if "fcb" in self._track.name and not self._controlling:
			logger.info("Controlling track {}".format(self._track.name))
			self._fx.set_track(self._track)
		if "fcb" not in self._track.name and self._controlling:
			logger.info("Releasing track {}".format(self._track.name))
			self._controlling = False
			self._fx.clear(self._track)
