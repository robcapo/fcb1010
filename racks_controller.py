from .led import LEDController
from .footswitch import FootSwitch, Layout, EventType, bottom_row, top_row
from .effects_mode import DeviceEnabledLED
from .board import Mode

from functools import partial
import logging


logger = logging.getLogger(__name__)


class RacksControllerMode(Mode):
	"""
	Mode designed to control a track with 5 audio racks that follow
	a certain configuration. Specifically, the racks will use special
	tokens in their Macro names to program the board.

	The top row will activate 1 of the 5 racks, and the bottom row will
	be based on the Macros of the currently active rack. Macros are
	programmed as follows.

	Macro name must include a spec in the form:
	#<event><action>

	event takes the form:
	s<pedal number><press event>

	pedal number is 1-5
	press event is:
	p: Press
	2: Double Press
	h: Hold
	d: Down
	u: Up

	actions include:
	t: toggle
	t<min>-<max>: toggle between min and max values
	s<val>: set to a specific value
	el: assign to left expression pedal
	er: assign to right expression pedal

	So of a macro name might be:
	Wah Amount #s5hel

	This would assign Wah Amount to the left
	expression pedal when stomp 5 is held.
	"""
	def __init__(self, leds: LEDController):
		super(RacksControllerMode, self).__init__(leds)
		self._leds = leds
		self._track = None
		self._racks = []
		self._rack_ind = None
		self._stomps = [RackMacroStomp(fs, leds) for fs in bottom_row()]
		self._patches = PatchSelector(top_row(), leds, self._set_rack)

	def get_layout(self):
		l = Layout()
		for s in self._stomps: l.union_with(s.get_layout())
		l.union_with(self._patches.get_layout())
		return l

	def set_layout_changed_callback(self, cb):
		self._layout_changed_callback = cb

	def set_track(self, track):
		self._clear_devices()
		self._track = track
		self._track.add_devices_listener(self._update_devices)
		self._update_devices()

	def _update_devices(self):
		if self._track is None:
			return

		self._clear_devices()
		
		for device in self._track.devices:
			device.add_name_listener(self._update_devices)
			if "#rack" in device.name:
				self._racks.append(device)

		self._patches.set_devices(self._racks)
		self._patches.set_device_ind(0)

	def _clear_devices(self):
		if self._track is None:
			return

		for device in self._racks:
			if device.name_has_listener(self._update_devices):
				device.remove_name_listener(self._update_devices)

		self._clear_rack()
		self._racks = []


	def _set_rack(self, rack_ind):
		self._clear_rack()
		self._rack_ind = rack_ind
		self._racks[rack_ind].add_parameters_listener(self._update_parameters)
		self._update_parameters()

	def _update_parameters(self):
		for stomp in self._stomps:
			stomp.set_rack(self._racks[self._rack_ind])
		for param in self._racks[self._rack_ind].parameters:
			param.add_name_listener(self._update_stomps)
		self._layout_changed_callback()

	def _update_stomps(self):
		for s in self._stomps: s.update_parameters()
		self._layout_changed_callback()

	def _clear_rack(self):
		logger.info("Rack ind {} racks {}".format(self._rack_ind, self._racks))
		if self._rack_ind is None:
			return

		if self._racks[self._rack_ind].parameters_has_listener(self._update_parameters):
			self._racks[self._rack_ind].remove_parameters_listener(self._update_parameters)

		for param in self._racks[self._rack_ind].parameters:
			if param.name_has_listener(self._update_stomps):
				param.remove_name_listener(self._update_stomps)

		self._rack_ind = None

class PatchSelector:
	def __init__(self, footswitches, leds: LEDController, callback = None):
		self._footswitches = footswitches
		self._leds = [DeviceEnabledLED(fs, leds) for fs in footswitches]
		self._indexes = {fs: i for i, fs in enumerate(footswitches)}
		self._ons = {}
		self._callback = callback

	def get_layout(self):
		layout = Layout()
		for footswitch in self._footswitches:
			layout.listen(footswitch, EventType.PRESS, partial(self._pressed, footswitch))
		return layout

	def set_devices(self, devices):		
		self.clear()

		if len(devices) > len(self._footswitches):
			logger.warning(
				"Patch can only control {} devices but received {}. Ignoring the rest."
					.format(len(self._footswitches), len(devices)))

		for footswitch, led, device in zip(self._footswitches, self._leds, devices):
			led.listen_to_device(device)
			for p in device.parameters:
				if p.name == "Device On":
					self._ons[footswitch] = p

	def set_device_ind(self, device_ind):
		if device_ind >= len(self._footswitches):
			return
		self._pressed(self._footswitches[device_ind])

	def clear(self):
		self._ons = {}
		for led in self._leds:
			led.clear()

	def _pressed(self, footswitch, *a):
		if footswitch not in self._ons:
			return
		for fs, on in self._ons.items():
			if fs == footswitch:
				on.value = 1.0
				self._callback(self._indexes[fs])
			else:
				on.value = 0.0

class RackMacroStomp:
	"""
	A controller for a single footswitch. This footswitch
	may do multiple things for different macros. e.g. it
	may toggle one macro and assign another macro to an
	expression pedal. 
	"""

	_event_map = {
		"u": EventType.UP,
		"d": EventType.DOWN,
		"p": EventType.PRESS,
		"2": EventType.DOUBLE_PRESS,
		"h": EventType.LONG_PRESS
	}

	def __init__(self, footswitch, leds: LEDController):
		self._footswitch = footswitch
		self._led = RackMacroLED(footswitch, leds)
		self._rack = None
		self._event_actions = {}

	def get_layout(self):
		def execute_all(actions, *a):
			for action in actions:
				action.execute()

		l = Layout()
		for event, actions in self._event_actions.items():
			l.listen(self._footswitch, event, partial(execute_all, actions))
		return l

	def set_rack(self, rack):
		self._rack = rack
		self.update_parameters()

	def update_parameters(self):
		self._event_actions = {}
		for param in self._rack.parameters:
			self._parse_event_actions(param)

	def _parse_event_actions(self, param):
		for tok in param.name.split():
			if not tok.startswith("#s{}".format(self._footswitch.value)):
				continue
			if len(tok) < 5:
				continue
			if tok[3:4] not in self._event_map:
				continue

			event = self._event_map[tok[3:4]]
			action_spec = tok[4:]

			action = Action()

			if action_spec == "t":
				action = Toggle(param)
				self._led.watch_parameter(param, (param.min + param.max) / 2)
			elif action_spec.startswith("t"):
				min_max = action_spec[1:].split("-")
				if len(min_max) != 2:
					continue
				if not min_max[0].isnumeric():
					continue
				if not min_max[1].isnumeric():
					continue

				action = Toggle(param, float(min_max[0]), float(min_max[1]))
				self._led.watch_parameter(param, (float(min_max[0]) + float(min_max[1])) / 2)
			elif action_spec.startswith("s"):
				if not action_spec[1:].isnumeric():
					continue
				action = SetValue(param, float(action_spec[1:]))
			else:
				continue

			if event not in self._event_actions:
				self._event_actions[event] = []
			self._event_actions[event].append(action)


class Action:
	def execute(self):
		pass

class SetValue(Action):
	def __init__(self, param, value):
		self._param = param
		self._value = value

	def execute(self):
		self._param.value = self._value

class Toggle(Action):
	def __init__(self, param, lo = None, hi = None):
		self._param = param
		self._min = lo if lo is not None else param.min
		self._max = hi if hi is not None else param.max

	def execute(self):
		if self._param.value < (self._min + self._max) / 2:
			self._param.value = self._max
		else:
			self._param.value = self._min


class RackMacroLED:
	"""
	Controls an LED based on a Macro. If the Macro value is above
	a certain threshold the LED will be on.
	"""
	def __init__(self, footswitch: FootSwitch, leds: LEDController):
		self._on = partial(leds.on, footswitch.led_value())
		self._off = partial(leds.off, footswitch.led_value())
		self._parameter = None
		self._threshold = 0
		self._is_on = False

	def watch_parameter(self, parameter, threshold):
		self.clear_parameter()
		self._parameter = parameter
		self._threshold = threshold
		self._parameter.add_value_listener(self._update)
		self._update()

	def clear_parameter(self):
		if self._parameter is None:
			return

		if self._parameter.value_has_listener(self._update):
			self._parameter.remove_value_listener(self._update)

		self._parameter = None
		self._off()

	def _update(self):
		if self._parameter.value > self._threshold and not self._is_on:
			self._on()
			self._is_on = True
		elif self._parameter.value <= self._threshold and self._is_on:
			self._off()
			self._is_on = False