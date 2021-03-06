from .board import Mode
from .led import LEDController
from .footswitch import FootSwitch, Layout, EventType
from .transport import Metronome
from functools import partial
import logging
import threading
import Live

logger = logging.getLogger(__name__)

class SessionMode(Mode):
	"""
	Mode for jamming / recording clips in a session.

	This mode will make sure that when the track is set, it has
	4 tracks immediately to its right, and each of them is taking
	input from the set track. Like this:

	[#fcb] [#ch1] [#ch2] [#ch3] [#ch4]

	#fcb will be updated to have monitoring set to In.
	Each "#ch" will have monitoring set to Off.
	Each "#ch" will have its Audio In set to #fcb Post Mixer

	On the top row, there are three stomps. By default these
	will toggle the first 3 FX in the device chain. Rename
	devices to include #sesh6 #sesh7 or #sesh8 to override
	this behavior.

	[1]: Play/stop/record #ch1
	[2]: Play/stop/record #ch2
	[3]: Play/stop/record #ch3
	[4]: Play/stop/record #ch4 
	[5]: Tap Tempo | hold to Toggle metronome
	[6]: Stomp
	[7]: Stomp
	[8]: Stomp
	[9]: Stack [tap / solid] / Erase [hold / blink]
	[0]: Metronome toggle
	"""
	def __init__(self, leds: LEDController, scheduler):
		super(SessionMode, self).__init__(leds)
		self._leds = leds
		self._track = None
		self._tracks_controller = TracksController(leds, scheduler)
		self._metronome = Metronome(FootSwitch.FIVE, leds)

	def set_track(self, track: Live.Track.Track):
		self._tracks_controller.set_main_track(track)

	def get_layout(self):
		l = Layout()
		l.union_with(self._tracks_controller.get_layout())
		l.union_with(self._metronome.get_layout())
		return l



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

	def get_layout(self):
		l = Layout()
		for t in self._track_controllers: l.union_with(t.get_layout())
		return l

	def set_main_track(self, track: Live.Track.Track):
		logger.info("Setting main track")
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
					channel_track.name = "ch{}".format(j)
					channel_track.color = main_track.color
					channel_track.current_monitoring_state = 2 # Monitoring Off
					channel_track.arm = True
					channel_track.add_available_input_routing_types_listener(self._set_routing_callback(channel_track, main_track.name))
					self._track_controllers[j - 1].set_track(channel_track)
				break

	def _set_routing_callback(self, track: Live.Track.Track, routing):
		def update_routing():
			if track.current_input_routing == routing:
				return
			for t in track.available_input_routing_types:
				if t.display_name == routing:
					def update(typ):
						def go():
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
		self._track = track
		self.update()

	def get_layout(self):
		l = Layout()
		l.listen(self._footswitch, EventType.DOWN, self._footswitch_down)
		l.listen(self._footswitch, EventType.DOUBLE_PRESS, self._double_press)
		return l

	def _footswitch_down(self, *a):
		self._clip_slot.fire()

	def _double_press(self, *a):
		if self._clip_slot.has_clip:
			self._scheduler(0, self._delete_clip)

	def _delete_clip(self):
		if self._clip_slot.has_clip:
			self._clip_slot.set_fire_button_state(False)
			self._clip_slot.delete_clip()

	def update(self):
		if self._track is not None:
			self._clip_slot = self._track.clip_slots[0]
			self._clip_slot.add_has_clip_listener(self._update_clip)

	def _update_clip(self):
		if self._track is None:
			self._clip_slot = None
			self._clip = None
		else:
			if self._clip_slot.has_clip:
				self._clip = self._clip_slot.clip
				self._clip.add_playing_status_listener(self._update_led)
			else:
				self._clip = None

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

