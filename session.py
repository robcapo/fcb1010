from .led import LEDController
from .events import FootSwitchEventBus, FootSwitch, EventType, bottom_row, top_row
from functools import partial
from typing import Callable
import Live
import logging


logger = logging.getLogger(__name__)

class Session:
	def __init__(self, leds: LEDController, events: FootSwitchEventBus):
		self._leds = leds
		self._events = events
		self._tracks = {}
		self._song = Live.Application.get_application().get_document()
		self._song.add_tracks_listener(self._update_tracks)
		self._update_tracks()

	def __del__(self):
		self._song.remove_tracks_listener(self._update_tracks)

	def _update_tracks(self):
		if len(self._song.tracks) > len(self._tracks):
			for track in self._song.tracks:
				if track._live_ptr not in self._tracks:
					logger.info("Adding new track {} with name {}".format(track._live_ptr, track.name))
					self._tracks[track._live_ptr] = Track(track, self._leds, self._events)
		else:
			tracks = {t._live_ptr: t for t in self._song.tracks}
			for track_ptr in list(self._tracks.keys()):
				if track_ptr not in tracks:
					logger.info("Removing track")
					del self._tracks[track_ptr]


class Track:
	def __init__(self, track, leds: LEDController, events: FootSwitchEventBus):
		self._track = track
		self._devices = {}
		self._patch = None
		self._leds = leds
		self._events = events
		self._controlling = False
		self._track.add_name_listener(self._update_name)
		self._update_name()

	def _update_name(self):
		if "fcb" in self._track.name and not self._controlling:
			logger.info("Controlling track {}".format(self._track.name))
			self._controlling = True
			self._track.add_devices_listener(self._update_devices)
			self._update_devices()
		if "fcb" not in self._track.name and self._controlling:
			logger.info("Releasing track {}".format(self._track.name))
			self._controlling = False
			self._track.remove_devices_listener(self._update_devices)
			self._devices = {}

	def _update_devices(self):
		footswitches = [fs for fs in bottom_row()]
		fs_ind = 0
		self._devices = []
		self._radio = None
		for device in self._track.devices:
			logger.info("Adding new device {} with name {}".format(device._live_ptr, device.name))
			self._devices.append(Stomp(footswitches[fs_ind], device, self._leds, self._events))

			fs_ind += 1
			if fs_ind == len(footswitches):
				break

		for device in self._track.devices:
			if "fcbradio" in device.name:
				if isinstance(device, Live.RackDevice.RackDevice):
					if device.can_have_chains:
						self.radio = Radio(device.chains[0].devices, self._leds, self._events)
					else:
						logger.warning("Cannot control radio device {} because it does not have chains".format(device.name))
				else:
					logger.warning("Cannot control radio device {} because it is not a rack".format(device.name))


class Stomp:
	def __init__(self, footswitch: FootSwitch, device: Live.Device.Device, leds: LEDController, events: FootSwitchEventBus):
		self._footswitch = footswitch
		for p in device.parameters:
			if p.name == "Device On":
				self._on = p
		self._led = DeviceEnabledLED(device, partial(leds.on, footswitch.led_value()), partial(leds.off, footswitch.led_value()))
		events.get_notifier(footswitch).set_callback(EventType.PRESS, self._toggle)

	def _toggle(self, *a):
		if self._on.value == 1.0:
			self._on.value = 0.0
		else:
			self._on.value = 1.0

class Radio:
	"""Group of footswitches"""
	def __init__(self, devices, leds: LEDController, events: FootSwitchEventBus):
		if len(devices) > 5:
			logger.warning("Radio can only control 5 devices from top row. Ignoring the rest.")

		self._leds = []
		self._ons = []
		footswitches = top_row()
		fs_ind = 0
		for device in devices:
			self._leds.append(DeviceEnabledLED(
				device, 
				partial(leds.on, footswitches[fs_ind].led_value()),
				partial(leds.off, footswitches[fs_ind].led_value()),
			))
			for p in device.parameters:
				if p.name == "Device On":
					self._ons.append(p)
			events.get_notifier(footswitches[fs_ind]).set_callback(EventType.PRESS, partial(self.activate, fs_ind))
			fs_ind += 1
			if fs_ind == len(footswitches):
				break

	def activate(self, ind, *a):
		for i, on in enumerate(self._ons):
			if i == ind:
				on.value = 1.0
			else:
				on.value = 0.0

class DeviceEnabledLED:
	def __init__(self, device, on_cb: Callable, off_cb: Callable):
		self._device = device
		self._on = on_cb
		self._off = off_cb
		self._device.add_is_active_listener(self._update_state)
		self._update_state()

	def __del__(self):
		logger.info("Removing is_active listener because device was deleted")
		self._device.remove_is_active_listener(self._update_state)

	def _update_state(self):
		if self._device.is_active:
			self._on()
		else:
			self._off()
