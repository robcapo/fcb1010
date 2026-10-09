from ableton.v2.base import liveobj_valid
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

	def disconnect(self):
		self._tracks_updated_callback = None
		if self._song.tracks_has_listener(self._update_tracks):
			self._song.remove_tracks_listener(self._update_tracks)
		for track in self._tracks.values():
			if liveobj_valid(track) and track.name_has_listener(self._update_tracks):
				track.remove_name_listener(self._update_tracks)
		self._tracks = {}

	def _update_tracks(self):
		tracks = {t._live_ptr: t for t in self._song.tracks}
		for track_ptr in list(self._tracks.keys()):
			if track_ptr not in tracks:
				logger.info("Removing track {}".format(track_ptr))
				del self._tracks[track_ptr]
		for track_ptr, track in tracks.items():
			if track_ptr not in self._tracks:
				logger.info("Adding new track {} with name {}".format(track_ptr, track.name))
				self._tracks[track_ptr] = track
				track.add_name_listener(self._update_tracks)

		# Use the order of the tracks in the set
		tracked_tracks = [t for t in self._song.tracks if "#fcb" in t.name]
		if tracked_tracks != self._tracked_tracks:
			self._tracked_tracks = tracked_tracks
			if self._tracks_updated_callback is not None:
				self._tracks_updated_callback()
