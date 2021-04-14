from .footswitch import FootSwitchEventBus
from .led import LEDController
import Live
import logging


logger = logging.getLogger(__name__)

class Session:
	"""
	Keeps track of all the Tracks in the set. Will call tracks_updated_callback
	whenever the tracks change
	"""
	def __init__(self):
		self._tracks = {}
		self._tracked_tracks = []
		self._song = Live.Application.get_application().get_document()
		self._song.add_tracks_listener(self._update_tracks)
		self._tracks_updated_callback = None
		self._update_tracks()

	def get_tracks(self):
		return self._tracked_tracks

	def add_callback(self, cb):
		self._tracks_updated_callback = cb

	def _update_tracks(self):
		if len(self._song.tracks) > len(self._tracks):
			for track in self._song.tracks:
				if track._live_ptr not in self._tracks:
					logger.info("Adding new track {} with name {}".format(track._live_ptr, track.name))
					self._tracks[track._live_ptr] = track
					track.add_name_listener(self._update_tracks)
		elif len(self._song.tracks) < len(self._tracks):
			tracks = {t._live_ptr: t for t in self._song.tracks}
			for track_ptr in list(self._tracks.keys()):
				if track_ptr not in tracks:
					logger.info("Removing track {}".format(track_ptr))
					del self._tracks[track_ptr]

		tracked_tracks = [t for t in self._tracks.values() if "#fcb" in t.name]
		if tracked_tracks != self._tracked_tracks:
			self._tracked_tracks = tracked_tracks
			if self._tracks_updated_callback is not None:
				self._tracks_updated_callback()
