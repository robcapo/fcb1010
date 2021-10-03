from .led import LEDController
from .footswitch import FootSwitchEventType, FootSwitch, EventType, Layout, numbered_footswitches, bottom_row, top_row
from .board import Mode
from functools import partial
from ableton.v2.base import liveobj_valid
import Live
import sys
import logging


logger = logging.getLogger(__name__)

class EffectsMode(Mode):
	"""
	Mode for messing with tone

	[1]: Stomp
	[2]: Stomp
	[3]: Stomp
	[4]: Stomp
	[5]: Stomp
	[6-10]: OneHotRack links to first rack device with #1hot in name
	"""
	def __init__(self, leds: LEDController):
		super(EffectsMode, self).__init__(leds)
		self._leds = leds
		self._stomps = [Stomp(fs, leds) for fs in bottom_row()]
		self._patch = OneHotRack(top_row(), leds)
		self._track = None

	def get_layout(self):
		l = Layout()
		for s in self._stomps: l.union_with(s.get_layout())
		l.union_with(self._patch.get_layout())
		return l

	def set_track(self, track: Live.Track.Track):
		if track != self._track:
			self.clear()
		self._track = track
		self._track.add_devices_listener(self._update_devices)
		self._update_devices()

	def clear(self, track: Live.Track.Track = None):
		if self._track is None:
			return
		if track is not None and track != self._track:
			return
		try:
			if self._track.devices_has_listener(self._update_devices):
				self._track.remove_devices_listener(self._update_devices)
		except:
			logger.warning("Failed to remove devices listener. Track must be deleted")
		
		for stomp in self._stomps: stomp.clear()
		self._patch.clear()
		self._track = None

	def _update_devices(self):
		try:
			for stomp, device in zip(self._stomps, filter(self.non_looper, self._track.devices)):
				logger.info("Adding new {} device with class {} and name {}".format(device.type, device.class_name, device.name))
				stomp.listen_to_device(device)
			for device in self._track.devices:
				if "#1hot" in device.name:
					self._patch.listen_to_rack(device)
					break
		except:
			logger.info("Failed to update devices, is track gone? {}".format(sys.exc_info()[1]))

	def non_looper(self, device):
		return device.class_name != "Looper"


class Stomp:
	def __init__(self, footswitch: FootSwitch, leds: LEDController):
		self._led = DeviceEnabledLED(footswitch, leds)
		self._footswitch = footswitch
		self._on_param = None

	def get_layout(self):
		l = Layout()
		l.listen(self._footswitch, EventType.PRESS, self._toggle)
		return l

	def listen_to_device(self, device: Live.Device.Device):
		self._led.listen_to_device(device)
		for p in device.parameters:
			if p.name == "Device On":
				self._on_param = p

	def clear(self):
		self._led.clear()
		self._on_param = None
		
	def _toggle(self, *a):
		if self._on_param is not None:
			if self._on_param.value == 1.0:
				self._on_param.value = 0.0
			else:
				self._on_param.value = 1.0

class OneHotRack:
	"""Rack of effects where only one is active at a time"""
	def __init__(self, footswitches, leds: LEDController):
		self._footswitches = footswitches
		self._leds = [DeviceEnabledLED(fs, leds) for fs in footswitches]
		self._ons = {}

	def get_layout(self):
		layout = Layout()
		for footswitch in self._footswitches:
			layout.listen(footswitch, EventType.PRESS, partial(self.pressed, footswitch))
		return layout

	def listen_to_rack(self, rack):		
		self.clear()
		if not isinstance(rack, Live.RackDevice.RackDevice):
			logger.warning("Cannot control non-rack device: {}".format(rack.name))
			return

		if not rack.can_have_chains:
			logger.warning("Cannot control rack {} because it can't have chains".format(rack.name))
			return

		devices = rack.chains[0].devices

		if len(devices) > len(self._footswitches):
			logger.warning(
				"OneHotRack can only control {} devices but rack has {}. Ignoring the rest."
					.format(len(self._footswitches), len(devices)))

		for footswitch, led, device in zip(self._footswitches, self._leds, devices):
			led.listen_to_device(device)
			for p in device.parameters:
				if p.name == "Device On":
					self._ons[footswitch] = p


	def clear(self):
		self._ons = {}
		for led in self._leds:
			led.clear()

	def pressed(self, footswitch, *a):
		if footswitch not in self._ons:
			return
		for fs, on in self._ons.items():
			if fs == footswitch:
				on.value = 1.0
			else:
				on.value = 0.0

class DeviceEnabledLED:
	def __init__(self, footswitch: FootSwitch, leds: LEDController):
		self._on = partial(leds.on, footswitch.led_value())
		self._off = partial(leds.off, footswitch.led_value())
		self._device = None
		self._footswitch = footswitch

	def listen_to_device(self, device):
		if self._device != device:
			self.clear()
		self._device = device
		self._device.add_is_active_listener(self._update_state)
		self._update_state()

	def clear(self):
		if self._device is not None:
			if liveobj_valid(self._device):
				self._device.remove_is_active_listener(self._update_state)
			self._device = None
		self._update_state()

	def _update_state(self):
		if self._device is not None and self._device.is_active:
			self._on()
		else:
			self._off()
