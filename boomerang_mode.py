from .board import Mode
from .led import LEDController, FAST_BLINK
from .footswitch import FootSwitch, Layout, EventType
from .session_mode import TracksController, MONITORING_IN
from .transport import Metronome
from ableton.v2.base import liveobj_valid
from functools import partial
from time import time
import math
import logging
import Live

logger = logging.getLogger(__name__)

# Bar lengths for auto stop on pedals 7-10
AUTO_STOP_BARS = [1, 2, 4, 8]

class BoomerangMode(Mode):
	"""
	Mode that works like a Boomerang III phrase sampler. Like session mode,
	it makes sure the set track has 3 tracks to its right (after any session
	mode tracks), each monitoring input from the set track:

	[#fcb] [ch1] ... [ch4] [lp1] [lp2] [lp3]

	Each lp track gets a Looper device, which is the loop. If this version
	of Live can't add devices from a script, drop a Looper on each lp track.

	[1-3]: Loop 1-3. Press to record, press again to stop recording and
	       play, press while playing to stop, press while stopped to play.
	       Pressing an overdubbing loop also stops it. Hold to erase the loop.
	       If another loop is recording, it's as if its pedal was pressed first.
	[4]: Stack. Toggles overdub. While it's on, the leftmost playing loop
	     overdubs, and moves to the next one if that loop stops. If a loop
	     is recording, it's as if its pedal was pressed first, so the
	     recording ends and the loop starts playing (and overdubbing).
	[5]: Tap Tempo | hold to toggle metronome
	[6]: Sync. When on, loops start and stop on the 1 of a bar and
	     follow the song tempo. When off, the first loop recorded sets the
	     song's tempo, and starts the song when it's done recording. Other
	     loops then start with it and are a multiple of its length.
	     Erasing every loop resets this.
	[7-10]: Auto stop after 1, 2, 4 or 8 bars: recording stops and the
	        loop starts playing. Turning one on turns on sync. Press the
	        lit one to turn auto stop off. Turning off sync turns them off.

	LEDs for 1-3: off when empty, fast blink while recording or
	overdubbing, on while playing, slow blink when stopped.
	"""
	display_text = "BR"

	def __init__(self, leds: LEDController, scheduler):
		super(BoomerangMode, self).__init__(leds)
		self._leds = leds
		self._scheduler = scheduler
		self._song = Live.Application.get_application().get_document()
		self._track_generation = 0

		self._sync = False
		self._auto_stop = None # index into AUTO_STOP_BARS, or None
		self._stack = False
		# With sync off, the first loop sets the tempo and the grid. These
		# are the loop that's recording it, and the loop's length in bars.
		self._grid_loop = None
		self._grid_loop_started = None
		self._grid_bars = None

		self._loops = [
			LoopController(FootSwitch.ONE, leds, scheduler, self),
			LoopController(FootSwitch.TWO, leds, scheduler, self),
			LoopController(FootSwitch.THREE, leds, scheduler, self),
		]
		self._tracks_controller = TracksController(
			self._loops, scheduler, prefix = "lp", monitoring = MONITORING_IN, arm = False)
		self._metronome = Metronome(FootSwitch.FIVE, leds)
		self._update_settings_leds()

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
		self._tracks_controller.set_main_track(None)
		self._metronome.disconnect()

	def auto_stop_beats(self):
		"""Length in beats that new recordings should stop at, or None to record until pressed"""
		if not self._sync or self._auto_stop is None:
			return None
		return AUTO_STOP_BARS[self._auto_stop] * self.beats_per_bar()

	def beats_per_bar(self):
		return self._song.signature_numerator * 4.0 / self._song.signature_denominator

	def start_transport(self):
		"""The Looper only responds to the API while the song is playing"""
		if self._sets_grid() or self._grid_loop is not None:
			# The first loop's Looper starts the song itself, so beat 1 is the loop's start
			return
		if not self._song.is_playing:
			self._song.continue_playing()

	def looper_settings(self):
		"""Quantization, Tempo Control and Song Control for the Loopers"""
		if self._sync:
			return ["1 bar"], ["follow song tempo"], ["none"]
		if self._grid_bars is not None:
			return [_bars_item(b) for b in (8, 4, 2, 1) if self._grid_bars % b == 0], ["follow song tempo"], ["none"]
		if self._sets_grid() or self._grid_loop is not None:
			return ["none"], ["set & follow song tempo"], ["start song"]
		return ["none"], ["none"], ["none"]

	def recording_started(self, loop):
		if self._sets_grid():
			self._grid_loop = loop
			self._grid_loop_started = time()
			if self._song.is_playing:
				self._song.stop_playing()
			self._apply_sync()

	def recording_finished(self, loop):
		if loop is self._grid_loop:
			# Give the Looper a moment to set the tempo
			self._scheduler(2, partial(self._set_grid, loop, time() - self._grid_loop_started))

	def grid_pending(self):
		"""Whether the first loop just finished, and the grid isn't set up yet"""
		return self._grid_loop is not None and not self._grid_loop.is_recording()

	def loop_erased(self):
		if not any(l.has_loop() for l in self._loops):
			self._grid_loop = None
			self._grid_bars = None
			self._apply_sync()

	def _sets_grid(self):
		"""Whether the next recording will set the tempo and grid"""
		return (not self._sync and self._grid_bars is None and self._grid_loop is None
			and not any(l.has_loop() for l in self._loops))

	def _set_grid(self, loop, seconds):
		if loop is not self._grid_loop:
			return
		bars = seconds * self._song.tempo / 60.0 / self.beats_per_bar()
		self._grid_bars = max(1, int(round(bars)))
		self._grid_loop = None
		logger.info("First loop is {} bars ({} at {} bpm)".format(self._grid_bars, bars, self._song.tempo))
		self._apply_sync()

	def state_changed(self):
		# Live doesn't allow changing a parameter from inside a notification
		self._scheduler(0, self._update_overdub)

	def finish_recording(self, pressed = None):
		"""
		Acts as if the pedal of a loop that's recording was pressed first,
		which stops recording and starts playing it.
		"""
		for loop in self._loops:
			if loop is not pressed and loop.is_recording():
				loop.press()

	def _toggle_stack(self, *a):
		self.finish_recording()
		self._stack = not self._stack
		self._update_overdub()
		self._update_settings_leds()

	def _update_overdub(self):
		"""With stack on, makes the leftmost playing loop the only one overdubbing"""
		target = None
		if self._stack:
			target = next((l for l in self._loops if l.is_playing()), None)
		for loop in self._loops:
			if loop is target:
				if not loop.is_overdubbing():
					loop.overdub()
			else:
				loop.end_overdub()

	def _toggle_sync(self, *a):
		self._sync = not self._sync
		if not self._sync:
			self._auto_stop = None
		self._apply_sync()

	def _select_auto_stop(self, ind, *a):
		if self._auto_stop == ind:
			self._auto_stop = None
		else:
			self._auto_stop = ind
			if not self._sync:
				self._sync = True
		self._apply_sync()

	def _apply_sync(self):
		for loop in self._loops:
			loop.apply_settings()
		self._update_settings_leds()

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


def _bars_item(bars):
	return "1 bar" if bars == 1 else "{} bars".format(bars)


class Looper:
	"""
	Wraps one of Live's Looper devices. Uses the LooperDevice functions when
	this version of Live has them, otherwise the device's State parameter.
	"""
	STOPPED = 0
	RECORDING = 1
	PLAYING = 2
	OVERDUBBING = 3

	def __init__(self, device):
		self.device = device
		self._params = {p.name: p for p in device.parameters}
		self.state_param = self._params.get("State")

	def state(self):
		if self.state_param is None:
			return self.STOPPED
		return int(self.state_param.value)

	def loop_length(self):
		"""Length of the loop, or 0 if it's empty or this version of Live can't tell"""
		return getattr(self.device, "loop_length", 0) or 0

	def record(self):
		self._transition("record", self.RECORDING)

	def overdub(self):
		self._transition("overdub", self.OVERDUBBING)

	def play(self):
		self._transition("play", self.PLAYING)

	def stop(self):
		self._transition("stop", self.STOPPED)

	def clear(self):
		if hasattr(self.device, "clear"):
			self.device.clear()
		else:
			logger.error("This version of Live can't clear a Looper from a script")

	def configure(self, quantization, tempo_control, song_control):
		self._set_item("Quantization", quantization)
		self._set_item("Tempo Control", tempo_control)
		self._set_item("Song Control", song_control)
		# The #fcb track already monitors the input, so only play the loop
		self._set_item("Monitor", ["never"])

	def _transition(self, fn, state):
		if hasattr(self.device, fn):
			getattr(self.device, fn)()
		elif self.state_param is not None:
			self.state_param.value = state

	def _set_item(self, name, choices):
		param = self._params.get(name)
		if param is None or not param.is_quantized:
			logger.info("Looper has no {} chooser".format(name))
			return
		items = [str(i).lower() for i in param.value_items]
		for choice in choices:
			if choice in items:
				value = param.min + items.index(choice)
				if param.value != value:
					param.value = value
				return
		logger.info("Looper {} has none of {} in {}".format(name, choices, items))


class LoopController:
	"""
	Controls one loop, which is the Looper device on its track
	"""
	def __init__(self, footswitch: FootSwitch, leds: LEDController, scheduler, mode: BoomerangMode):
		self._footswitch = footswitch
		self._leds = leds
		self._scheduler = scheduler
		self._mode = mode
		self._song = Live.Application.get_application().get_document()
		self._track = None
		self._looper = None
		# The Looper doesn't say whether it's empty, so keep track of it
		self._has_loop = False
		# Whether holding the current press should erase the loop. Only
		# true if the loop already had something in it when it was pressed.
		self._erase_on_hold = False
		# Song time (in beats) to switch from recording to playing, for auto stop
		self._auto_stop_at = None

	def set_track(self, track: Live.Track.Track):
		self._clear()
		self._track = track
		if self._track is not None:
			self._track.add_devices_listener(self._find_looper)
		self._find_looper()

	def get_layout(self):
		l = Layout()
		l.listen(self._footswitch, EventType.DOWN, self._footswitch_down)
		l.listen(self._footswitch, EventType.LONG_PRESS, self._held)
		return l

	def has_loop(self):
		return self.has_looper() and self._has_loop

	def has_looper(self):
		return self._looper is not None and liveobj_valid(self._looper.device)

	def is_recording(self):
		return self.has_looper() and self._looper.state() == Looper.RECORDING

	def is_playing(self):
		"""Whether the loop is playing, including overdubbing"""
		return self.has_looper() and self._looper.state() in (Looper.PLAYING, Looper.OVERDUBBING)

	def is_overdubbing(self):
		return self.has_looper() and self._looper.state() == Looper.OVERDUBBING

	def overdub(self):
		if not self.has_looper():
			return
		self._mode.start_transport()
		self._cancel_auto_stop()
		self._has_loop = True
		self._looper.overdub()

	def end_overdub(self):
		if self.is_overdubbing():
			self._looper.play()

	def apply_settings(self):
		if self.has_looper():
			self._looper.configure(*self._mode.looper_settings())

	def _footswitch_down(self, *a):
		self._mode.finish_recording(self)
		if self._mode.grid_pending():
			# Wait until the first loop has set the grid, so this one syncs to it
			self._scheduler(3, self.press)
		else:
			self.press()

	def press(self):
		self._erase_on_hold = False
		if not self.has_looper():
			logger.info("No Looper on {}".format(self._track.name if liveobj_valid(self._track) else None))
			return
		self._mode.start_transport()
		state = self._looper.state()
		if state == Looper.RECORDING:
			# Ends the recording and starts playing the loop
			self._cancel_auto_stop()
			self._looper.play()
			self._mode.recording_finished(self)
		elif not self._has_loop:
			self._record()
		elif state in (Looper.PLAYING, Looper.OVERDUBBING):
			self._erase_on_hold = True
			self._looper.stop()
		else:
			self._erase_on_hold = True
			self._looper.play()

	def _record(self):
		self._mode.recording_started(self)
		self._has_loop = True
		beats = self._mode.auto_stop_beats()
		if beats is not None:
			# Sync is on, so recording starts on the next bar
			bar = self._mode.beats_per_bar()
			start = math.ceil((self._song.current_song_time - 0.01) / bar) * bar
			self._auto_stop_at = start + beats
			if not self._song.current_song_time_has_listener(self._check_auto_stop):
				self._song.add_current_song_time_listener(self._check_auto_stop)
		self._looper.record()

	def _check_auto_stop(self):
		if self._auto_stop_at is None:
			return
		if not self.has_looper() or self._looper.state() != Looper.RECORDING:
			if self.has_looper() and self._looper.state() == Looper.STOPPED:
				# Still waiting for the bar to start recording
				return
			self._cancel_auto_stop()
			return
		# Ask for play a beat early. The Looper is quantized to the bar, so
		# it switches exactly on the bar line.
		early = min(1.0, self._mode.beats_per_bar() / 2)
		if self._song.current_song_time >= self._auto_stop_at - early:
			self._cancel_auto_stop()
			self._looper.play()
			self._mode.recording_finished(self)

	def _cancel_auto_stop(self):
		self._auto_stop_at = None
		if self._song.current_song_time_has_listener(self._check_auto_stop):
			self._song.remove_current_song_time_listener(self._check_auto_stop)

	def _held(self, *a):
		if self._erase_on_hold:
			self._erase_on_hold = False
			self._erase()

	def _erase(self):
		if not self.has_looper():
			return
		self._cancel_auto_stop()
		self._looper.stop()
		self._looper.clear()
		self._has_loop = False
		self._update_led()
		self._mode.loop_erased()

	def _find_looper(self):
		looper = None
		if self._track is not None and liveobj_valid(self._track):
			looper = next((d for d in self._track.devices if d.class_name == "Looper"), None)
			if looper is None and hasattr(self._track, "insert_device"):
				# Adding a device modifies the song, so do it outside of any notification
				self._scheduler(0, self._insert_looper)
		if self._looper is not None and looper is not None and self._looper.device == looper:
			return
		self._clear_looper()
		if looper is not None:
			self._looper = Looper(looper)
			if self._looper.state_param is not None:
				self._looper.state_param.add_value_listener(self._state_changed)
			self._has_loop = self._looper.state() != Looper.STOPPED or self._looper.loop_length() > 0
			self.apply_settings()
		self._update_led()

	def _insert_looper(self):
		if self._track is None or not liveobj_valid(self._track) or self.has_looper():
			return
		try:
			self._track.insert_device("Looper")
		except Exception as e:
			logger.error("Couldn't add a Looper to {}: {}".format(self._track.name, e))

	def _state_changed(self):
		if self.has_looper() and self._looper.state() != Looper.STOPPED:
			self._has_loop = True
		self._update_led()
		self._mode.state_changed()

	def _clear(self):
		self._cancel_auto_stop()
		self._clear_looper()
		if self._track is not None and liveobj_valid(self._track):
			if self._track.devices_has_listener(self._find_looper):
				self._track.remove_devices_listener(self._find_looper)
		self._track = None
		self._update_led()

	def _clear_looper(self):
		if self._looper is not None and self._looper.state_param is not None and liveobj_valid(self._looper.state_param):
			if self._looper.state_param.value_has_listener(self._state_changed):
				self._looper.state_param.remove_value_listener(self._state_changed)
		self._looper = None
		self._has_loop = False

	def _update_led(self):
		led = self._footswitch.led_value()
		if not self.has_looper() or not self._has_loop:
			self._leds.off(led)
			return
		state = self._looper.state()
		if state in (Looper.RECORDING, Looper.OVERDUBBING):
			self._leds.blink_on(led, FAST_BLINK)
		elif state == Looper.PLAYING:
			self._leds.on(led)
		else:
			self._leds.blink_on(led)
