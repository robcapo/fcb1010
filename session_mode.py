from .board import Mode
from .led import LEDController
from .footswitch import FootSwitch, Layout, EventType
from .transport import Metronome
from ableton.v2.base import liveobj_valid
import logging
import Live

logger = logging.getLogger(__name__)

class SessionMode(Mode):
	"""
	Mode for jamming / recording clips in a session.

	This mode will make sure that when the track is set, it has
	4 tracks immediately to its right, and each of them is taking
	input from the set track. Like this:

	[#fcb] [ch1] [ch2] [ch3] [ch4]

	Each "ch" track will have monitoring set to Off, be armed, and
	have its Audio In set to the #fcb track.

	[1]: Play/stop/record ch1 | double press to delete the clip
	[2]: Play/stop/record ch2 | double press to delete the clip
	[3]: Play/stop/record ch3 | double press to delete the clip
	[4]: Play/stop/record ch4 | double press to delete the clip
	[5]: Tap Tempo | hold to toggle metronome
	[6-10]: Unused
	"""
	def __init__(self, leds: LEDController, scheduler):
		super(SessionMode, self).__init__(leds)
		self._leds = leds
		self._scheduler = scheduler
		self._track_generation = 0
		self._tracks_controller = TracksController(leds, scheduler)
		self._metronome = Metronome(FootSwitch.FIVE, leds)

	def set_track(self, track: Live.Track.Track):
		# Setting up the channel tracks modifies the song, which Live doesn't
		# allow from inside a notification (e.g. the tracks listener), so defer it.
		self._track_generation += 1
		generation = self._track_generation
		def apply():
			if generation != self._track_generation:
				return
			self._tracks_controller.set_main_track(track if liveobj_valid(track) else None)
		self._scheduler(0, apply)

	def get_layout(self):
		l = Layout()
		l.union_with(self._tracks_controller.get_layout())
		l.union_with(self._metronome.get_layout())
		return l

	def disconnect(self):
		self._track_generation += 1
		self._tracks_controller.set_main_track(None)
		self._metronome.disconnect()


class TracksController:
	def __init__(self, leds: LEDController, scheduler, size = 4):
		logger.info("Initializing Tracks controller")
		self._size = size
		self._scheduler = scheduler
		self._leds = leds
		self._track_controllers = [
			TrackController(leds, FootSwitch.ONE, scheduler),
			TrackController(leds, FootSwitch.TWO, scheduler),
			TrackController(leds, FootSwitch.THREE, scheduler),
			TrackController(leds, FootSwitch.FOUR, scheduler),
		]
		# (track, callback) for each input routing listener we've added
		self._routing_listeners = []

	def get_layout(self):
		l = Layout()
		for t in self._track_controllers: l.union_with(t.get_layout())
		return l

	def set_main_track(self, track: Live.Track.Track):
		logger.info("Setting main track")
		self._clear_routing_listeners()
		for c in self._track_controllers:
			c.set_track(None)
		if track is None:
			return

		song = Live.Application.get_application().get_document()
		tracks = song.tracks
		for i, main_track in enumerate(tracks):
			if main_track._live_ptr == track._live_ptr:
				for j in range(1, self._size + 1):
					channel_track = None
					if i + j < len(tracks) and tracks[i + j].name == "ch{}".format(j):
						channel_track = tracks[i + j]
					else:
						channel_track = song.create_audio_track(i + j)
						tracks = song.tracks
					channel_track.name = "ch{}".format(j)
					channel_track.color = main_track.color
					channel_track.current_monitoring_state = 2 # Monitoring Off
					channel_track.arm = True
					update_routing = self._set_routing_callback(channel_track, main_track.name)
					channel_track.add_available_input_routing_types_listener(update_routing)
					self._routing_listeners.append((channel_track, update_routing))
					update_routing()
					self._track_controllers[j - 1].set_track(channel_track)
				break

	def _clear_routing_listeners(self):
		for track, cb in self._routing_listeners:
			if liveobj_valid(track) and track.available_input_routing_types_has_listener(cb):
				track.remove_available_input_routing_types_listener(cb)
		self._routing_listeners = []

	def _set_routing_callback(self, track: Live.Track.Track, routing):
		def update_routing():
			if not liveobj_valid(track):
				return
			current = track.input_routing_type
			if current is not None and current.display_name == routing:
				return
			for t in track.available_input_routing_types:
				if t.display_name == routing:
					def update(typ):
						def go():
							if liveobj_valid(track):
								track.input_routing_type = typ
						return go
					self._scheduler(0, update(t))
					break
		return update_routing

class TrackController:
	"""
	Controls a single Track
	"""
	def __init__(self, leds: LEDController, footswitch: FootSwitch, scheduler):
		self._footswitch = footswitch
		self._leds = leds
		self._track = None
		self._clip_slot = None
		self._clip = None
		self._scheduler = scheduler

	def set_track(self, track: Live.Track.Track):
		self._clear()
		self._track = track
		if self._track is not None:
			self._clip_slot = self._track.clip_slots[0]
			self._clip_slot.add_has_clip_listener(self._update_clip)
		self._update_clip()

	def get_layout(self):
		l = Layout()
		l.listen(self._footswitch, EventType.DOWN, self._footswitch_down)
		l.listen(self._footswitch, EventType.DOUBLE_PRESS, self._double_press)
		return l

	def _footswitch_down(self, *a):
		if self._clip_slot is not None and liveobj_valid(self._clip_slot):
			self._clip_slot.fire()

	def _double_press(self, *a):
		if self._clip_slot is not None and liveobj_valid(self._clip_slot) and self._clip_slot.has_clip:
			self._scheduler(0, self._delete_clip)

	def _delete_clip(self):
		if self._clip_slot is not None and liveobj_valid(self._clip_slot) and self._clip_slot.has_clip:
			self._clip_slot.set_fire_button_state(False)
			self._clip_slot.delete_clip()

	def _clear(self):
		self._clear_clip()
		if self._clip_slot is not None and liveobj_valid(self._clip_slot):
			if self._clip_slot.has_clip_has_listener(self._update_clip):
				self._clip_slot.remove_has_clip_listener(self._update_clip)
		self._clip_slot = None
		self._track = None

	def _clear_clip(self):
		if self._clip is not None and liveobj_valid(self._clip):
			if self._clip.playing_status_has_listener(self._update_led):
				self._clip.remove_playing_status_listener(self._update_led)
		self._clip = None

	def _update_clip(self):
		self._clear_clip()
		if self._clip_slot is not None and liveobj_valid(self._clip_slot) and self._clip_slot.has_clip:
			self._clip = self._clip_slot.clip
			self._clip.add_playing_status_listener(self._update_led)

		self._update_led()

	def _update_led(self):
		if self._track is None or self._clip is None:
			self.off()
		elif self._clip.is_playing:
			self.on()
		else:
			self.blink()


	def off(self):
		self._leds.off(self._footswitch.led_value())

	def on(self):
		self._leds.on(self._footswitch.led_value())

	def blink(self):
		self._leds.blink_on(self._footswitch.led_value())
