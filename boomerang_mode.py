from .board import Mode
from .led import LEDController, FAST_BLINK
from .footswitch import FootSwitch, Layout, EventType
from .session_mode import TracksController, MONITORING_IN
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
	Mode that works like a Boomerang III phrase sampler, using the
	FCB Looper Max for Live device (see m4l/). Like session mode, it makes
	sure the set track has a track to its right (after any session mode
	tracks), monitoring input from the set track:

	[#fcb] [ch1] ... [ch4] [lp1]

	Drop FCB Looper on lp1. It holds all three loops and keeps their timing,
	so they don't need clips or the song's transport.

	[1-3]: Loop 1-3. Press to record, press again to stop recording and
	       play, press while playing or overdubbing to stop, press while
	       stopped to play. Hold to erase the loop. If another loop is
	       recording, it's as if its pedal was pressed first.
	[4]: Stack. Toggles overdub. While it's on, the leftmost playing loop
	     overdubs, and moves to the next one if that loop stops. If a loop
	     is recording, it's as if its pedal was pressed first, so the
	     recording ends and the loop starts playing (and overdubbing).
	[5]: Tap Tempo | hold to toggle metronome
	[6]: Sync. When on, loops start and stop on the 1 of a bar of the song.
	     When off, the first loop recorded is the master: the other loops
	     start when it comes around to its start, and are a multiple of
	     its length. Erasing every loop resets this.
	[7-10]: Auto stop after 1, 2, 4 or 8 bars: recording stops and the
	        loop starts playing. Turning one on turns on sync. Press the
	        lit one to turn auto stop off. Turning off sync turns them off.

	LEDs for 1-3: off when empty, fast blink while recording, waiting to
	record or overdubbing, on while playing, slow blink when stopped.
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

		self._loops = [
			LoopController(FootSwitch.ONE, 1, leds, self),
			LoopController(FootSwitch.TWO, 2, leds, self),
			LoopController(FootSwitch.THREE, 3, leds, self),
		]
		self._device = DeviceController(self._loops, self)
		self._tracks_controller = TracksController(
			[self._device], scheduler, prefix = "lp", monitoring = MONITORING_IN, arm = False)
		self._metronome = Metronome(FootSwitch.FIVE, leds)
		self._update_settings_leds()

	def set_track(self, track: Live.Track.Track):
		# Setting up the loop track modifies the song, which Live doesn't
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
		for loop in self._loops: l.union_with(loop.get_layout())
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

	def device_settings(self):
		"""Values for the device's sync and autostop parameters"""
		bars = 0
		if self._sync and self._auto_stop is not None:
			bars = AUTO_STOP_BARS[self._auto_stop]
		return (1 if self._sync else 0), bars

	def start_transport(self):
		"""With sync on, loops follow the song's bars, so the song needs to play"""
		if self._sync and not self._song.is_playing:
			self._song.continue_playing()

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
		self._apply_settings()

	def _select_auto_stop(self, ind, *a):
		if self._auto_stop == ind:
			self._auto_stop = None
		else:
			self._auto_stop = ind
			if not self._sync:
				self._sync = True
		self._apply_settings()

	def _apply_settings(self):
		self._device.apply_settings()
		self.start_transport()
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


# Loop status, from the device's status parameters
EMPTY = 0
STOPPED = 1
RECORDING = 2
PLAYING = 3
OVERDUBBING = 4
WAITING = 5 # waiting for the master or the bar to start recording

# Commands, for the device's target parameters
STOP = 0
RECORD = 1
PLAY = 2
OVERDUB = 3
ERASE = 4
NOTHING = 5


class DeviceController:
	"""
	Finds the FCB Looper device on the loop track and hands it to the loops
	"""
	def __init__(self, loops, mode: BoomerangMode):
		self._loops = loops
		self._mode = mode
		self._track = None
		self._device = None
		self._params = {}

	def set_track(self, track: Live.Track.Track):
		if self._track is not None and liveobj_valid(self._track):
			if self._track.devices_has_listener(self._find_device):
				self._track.remove_devices_listener(self._find_device)
		self._track = track
		if self._track is not None:
			self._track.add_devices_listener(self._find_device)
		self._find_device()

	def apply_settings(self):
		if not self._valid():
			return
		sync, bars = self._mode.device_settings()
		for name, value in (("sync", sync), ("autostop", bars)):
			p = self._params.get(name)
			if p is not None and p.value != value:
				p.value = value

	def _valid(self):
		return self._device is not None and liveobj_valid(self._device)

	def _find_device(self):
		device = None
		if self._track is not None and liveobj_valid(self._track):
			for d in self._track.devices:
				names = set(p.name for p in d.parameters)
				if {"target1", "status1", "sync"} <= names:
					device = d
					break
		if self._valid() and device is not None and device == self._device:
			return
		self._device = device
		self._params = {p.name: p for p in device.parameters} if device is not None else {}
		if device is None and self._track is not None:
			logger.info("No FCB Looper on {}".format(self._track.name if liveobj_valid(self._track) else None))
		for loop in self._loops:
			loop.set_params(self._params.get("target{}".format(loop.number)), self._params.get("status{}".format(loop.number)))
		self.apply_settings()


class LoopController:
	"""
	Controls one of the device's loops
	"""
	def __init__(self, footswitch: FootSwitch, number, leds: LEDController, mode: BoomerangMode):
		self.number = number
		self._footswitch = footswitch
		self._leds = leds
		self._mode = mode
		self._target = None
		self._status = None
		# Whether holding the current press should erase the loop. Only
		# true if the loop already had something in it when it was pressed.
		self._erase_on_hold = False

	def set_params(self, target, status):
		if self._status is not None and liveobj_valid(self._status):
			if self._status.value_has_listener(self._status_changed):
				self._status.remove_value_listener(self._status_changed)
		self._target = target
		self._status = status
		if self._status is not None:
			self._status.add_value_listener(self._status_changed)
		self._update_led()

	def get_layout(self):
		l = Layout()
		l.listen(self._footswitch, EventType.DOWN, self._footswitch_down)
		l.listen(self._footswitch, EventType.LONG_PRESS, self._held)
		return l

	def status(self):
		if not self._valid():
			return EMPTY
		return int(self._status.value)

	def is_recording(self):
		return self.status() == RECORDING

	def is_playing(self):
		"""Whether the loop is playing, including overdubbing"""
		return self.status() in (PLAYING, OVERDUBBING)

	def is_overdubbing(self):
		return self.status() == OVERDUBBING

	def overdub(self):
		self._send(OVERDUB)

	def end_overdub(self):
		if self.is_overdubbing():
			self._send(PLAY)

	def _valid(self):
		return (self._target is not None and liveobj_valid(self._target)
			and self._status is not None and liveobj_valid(self._status))

	def _send(self, command):
		if not self._valid():
			return
		# The device only reacts to a change, so step through NOTHING to repeat a command
		if self._target.value == command:
			self._target.value = NOTHING
		self._target.value = command

	def _footswitch_down(self, *a):
		self._mode.finish_recording(self)
		self.press()

	def press(self):
		self._erase_on_hold = False
		if not self._valid():
			logger.info("No FCB Looper for loop {}".format(self.number))
			return
		self._mode.start_transport()
		status = self.status()
		if status == RECORDING:
			# Finishes the recording and starts playing the loop
			self._send(PLAY)
		elif status == WAITING:
			self._send(STOP)
		elif status == EMPTY:
			self._send(RECORD)
		elif status in (PLAYING, OVERDUBBING):
			self._erase_on_hold = True
			self._send(STOP)
		else:
			self._erase_on_hold = True
			self._send(PLAY)

	def _held(self, *a):
		if self._erase_on_hold:
			self._erase_on_hold = False
			self._send(ERASE)

	def _status_changed(self):
		self._update_led()
		self._mode.state_changed()

	def _update_led(self):
		led = self._footswitch.led_value()
		status = self.status()
		if status == EMPTY:
			self._leds.off(led)
		elif status in (RECORDING, WAITING, OVERDUBBING):
			self._leds.blink_on(led, FAST_BLINK)
		elif status == PLAYING:
			self._leds.on(led)
		else:
			self._leds.blink_on(led)
