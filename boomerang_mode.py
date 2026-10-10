from .board import Mode
from .led import LEDController, FAST_BLINK
from .footswitch import FootSwitch, Layout, EventType
from .session_mode import TracksController
from .transport import Metronome
from ableton.v2.base import liveobj_valid
from functools import partial
import logging
import Live

logger = logging.getLogger(__name__)

# Bar lengths for auto stop on pedals 7-10
AUTO_STOP_BARS = [1, 2, 4, 8]

class BoomerangMode(Mode):
	"""
	Mode that works like a Boomerang III phrase sampler. Like session mode,
	it makes sure the set track has 3 tracks to its right (after any session
	mode tracks), each armed and taking input from the set track:

	[#fcb] [ch1] ... [ch4] [lp1] [lp2] [lp3]

	Each loop lives in the first clip slot of its lp track.

	[1-3]: Loop 1-3. Press to record, press again to stop recording and
	       play, press while playing to stop, press while stopped to play.
	       Hold to erase the loop.
	[4]: Stack. When on, loops play on top of each other. When off, loops
	     are serial: starting one stops the others.
	[5]: Tap Tempo | hold to toggle metronome
	[6]: Sync. When on, loops start and stop on the 1 of a bar.
	[7-10]: Auto stop after 1, 2, 4 or 8 bars: recording stops and the
	        loop starts playing. Turning one on turns on sync. Press the
	        lit one to turn auto stop off. Turning off sync turns them off.

	LEDs for 1-3: off when empty, fast blink while recording or waiting
	to start, on while playing, slow blink when stopped.

	Sync works by setting Live's global launch quantization to 1 bar (or
	None when sync is off) while this mode is active. The previous value
	is restored when leaving the mode.
	"""
	display_text = "BR"

	def __init__(self, leds: LEDController, scheduler):
		super(BoomerangMode, self).__init__(leds)
		self._leds = leds
		self._scheduler = scheduler
		self._song = Live.Application.get_application().get_document()
		self._track_generation = 0
		self._active = False
		self._saved_quantization = None

		self._sync = False
		self._auto_stop = None # index into AUTO_STOP_BARS, or None
		self._stack = False

		self._loops = [
			LoopController(FootSwitch.ONE, leds, scheduler, self),
			LoopController(FootSwitch.TWO, leds, scheduler, self),
			LoopController(FootSwitch.THREE, leds, scheduler, self),
		]
		self._tracks_controller = TracksController(self._loops, scheduler, prefix = "lp")
		self._metronome = Metronome(FootSwitch.FIVE, leds)
		self._update_settings_leds()

	def activate(self):
		super(BoomerangMode, self).activate()
		self._active = True
		self._saved_quantization = self._song.clip_trigger_quantization
		self._apply_quantization()

	def deactivate(self):
		self._restore_quantization()
		self._active = False
		super(BoomerangMode, self).deactivate()

	def set_track(self, track: Live.Track.Track):
		# Setting up the loop tracks modifies the song, which Live doesn't
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
		l.listen(FootSwitch.FOUR, EventType.DOWN, self._toggle_stack)
		l.listen(FootSwitch.SIX, EventType.DOWN, self._toggle_sync)
		for ind, fs in enumerate([FootSwitch.SEVEN, FootSwitch.EIGHT, FootSwitch.NINE, FootSwitch.TEN]):
			l.listen(fs, EventType.DOWN, partial(self._select_auto_stop, ind))
		return l

	def disconnect(self):
		self._track_generation += 1
		if self._active:
			self._restore_quantization()
		self._tracks_controller.set_main_track(None)
		self._metronome.disconnect()

	def record_length(self):
		"""Length in beats that new recordings should stop at, or None to record until pressed"""
		if not self._sync or self._auto_stop is None:
			return None
		beats_per_bar = self._song.signature_numerator * 4.0 / self._song.signature_denominator
		return AUTO_STOP_BARS[self._auto_stop] * beats_per_bar

	def loop_starting(self, loop):
		"""Called when a loop is about to record or play"""
		if not self._stack:
			for other in self._loops:
				if other is not loop:
					other.stop()

	def _toggle_stack(self, *a):
		self._stack = not self._stack
		self._update_settings_leds()

	def _toggle_sync(self, *a):
		self._sync = not self._sync
		if not self._sync:
			self._auto_stop = None
		self._apply_quantization()
		self._update_settings_leds()

	def _select_auto_stop(self, ind, *a):
		if self._auto_stop == ind:
			self._auto_stop = None
		else:
			self._auto_stop = ind
			if not self._sync:
				self._sync = True
				self._apply_quantization()
		self._update_settings_leds()

	def _apply_quantization(self):
		if not self._active:
			return
		self._song.clip_trigger_quantization = (
			Live.Song.Quantization.q_bar if self._sync else Live.Song.Quantization.q_no_q)

	def _restore_quantization(self):
		if self._saved_quantization is not None:
			self._song.clip_trigger_quantization = self._saved_quantization
			self._saved_quantization = None

	def _update_settings_leds(self):
		self._set_led(FootSwitch.FOUR, self._stack)
		self._set_led(FootSwitch.SIX, self._sync)
		for ind, fs in enumerate([FootSwitch.SEVEN, FootSwitch.EIGHT, FootSwitch.NINE, FootSwitch.TEN]):
			self._set_led(fs, self._auto_stop == ind)

	def _set_led(self, footswitch, on):
		if on:
			self._leds.on(footswitch.led_value())
		else:
			self._leds.off(footswitch.led_value())


class LoopController:
	"""
	Controls one loop, which is the first clip slot of its track
	"""
	def __init__(self, footswitch: FootSwitch, leds: LEDController, scheduler, mode: BoomerangMode):
		self._footswitch = footswitch
		self._leds = leds
		self._scheduler = scheduler
		self._mode = mode
		self._track = None
		self._clip_slot = None
		self._clip = None
		# Whether holding the current press should erase the loop. Only
		# true if the loop already had something in it when it was pressed.
		self._erase_on_hold = False

	def set_track(self, track: Live.Track.Track):
		self._clear()
		self._track = track
		if self._track is not None:
			self._clip_slot = self._track.clip_slots[0]
			self._clip_slot.add_has_clip_listener(self._update_clip)
			self._clip_slot.add_is_triggered_listener(self._update_led)
		self._update_clip()

	def get_layout(self):
		l = Layout()
		l.listen(self._footswitch, EventType.DOWN, self._footswitch_down)
		l.listen(self._footswitch, EventType.LONG_PRESS, self._held)
		return l

	def stop(self):
		"""Stops this loop (at the next bar if sync is on)"""
		if not self._valid():
			return
		if self._clip_slot.has_clip:
			clip = self._clip_slot.clip
			if clip.is_recording or clip.is_playing or clip.is_triggered:
				self._track.stop_all_clips()
		elif self._clip_slot.is_triggered:
			self._track.stop_all_clips()

	def _valid(self):
		return self._clip_slot is not None and liveobj_valid(self._clip_slot) and liveobj_valid(self._track)

	def _footswitch_down(self, *a):
		self._erase_on_hold = False
		if not self._valid():
			return
		slot = self._clip_slot
		if not slot.has_clip:
			if slot.is_triggered:
				# Waiting to start recording. Cancel it.
				self._track.stop_all_clips()
			else:
				self._mode.loop_starting(self)
				self._record()
			return

		clip = slot.clip
		self._erase_on_hold = True
		if clip.is_recording:
			# Ends the recording and starts playing the loop
			slot.fire()
		elif clip.is_playing or clip.is_triggered:
			self._track.stop_all_clips()
		else:
			self._mode.loop_starting(self)
			slot.fire()

	def _record(self):
		length = self._mode.record_length()
		if length is None:
			self._clip_slot.fire()
			return
		try:
			self._clip_slot.fire(record_length = length)
		except TypeError:
			logger.error("This version of Live can't record a fixed length. Recording until pressed.")
			self._clip_slot.fire()

	def _held(self, *a):
		if self._erase_on_hold:
			self._erase_on_hold = False
			self._scheduler(0, self._erase)

	def _erase(self):
		if self._valid() and self._clip_slot.has_clip:
			self._clip_slot.set_fire_button_state(False)
			self._clip_slot.delete_clip()

	def _clear(self):
		self._clear_clip()
		if self._clip_slot is not None and liveobj_valid(self._clip_slot):
			if self._clip_slot.has_clip_has_listener(self._update_clip):
				self._clip_slot.remove_has_clip_listener(self._update_clip)
			if self._clip_slot.is_triggered_has_listener(self._update_led):
				self._clip_slot.remove_is_triggered_listener(self._update_led)
		self._clip_slot = None
		self._track = None

	def _clear_clip(self):
		if self._clip is not None and liveobj_valid(self._clip):
			if self._clip.playing_status_has_listener(self._update_led):
				self._clip.remove_playing_status_listener(self._update_led)
			if self._clip.is_recording_has_listener(self._update_led):
				self._clip.remove_is_recording_listener(self._update_led)
		self._clip = None

	def _update_clip(self):
		self._clear_clip()
		if self._valid() and self._clip_slot.has_clip:
			self._clip = self._clip_slot.clip
			self._clip.add_playing_status_listener(self._update_led)
			self._clip.add_is_recording_listener(self._update_led)
		self._update_led()

	def _update_led(self):
		led = self._footswitch.led_value()
		if not self._valid():
			self._leds.off(led)
		elif self._clip is None or not liveobj_valid(self._clip):
			if self._clip_slot.is_triggered:
				self._leds.blink_on(led, FAST_BLINK)
			else:
				self._leds.off(led)
		elif self._clip.is_recording or self._clip.is_triggered:
			self._leds.blink_on(led, FAST_BLINK)
		elif self._clip.is_playing:
			self._leds.on(led)
		else:
			self._leds.blink_on(led)
