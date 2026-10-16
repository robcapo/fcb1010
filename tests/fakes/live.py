"""
A fake of the parts of Live's Python API (the `Live` module) that the
script uses. It is installed as `sys.modules["Live"]` by conftest.py.

It mimics the behaviours of the real API that have caused bugs before:
- add/remove listener raise if the listener is already / not connected
- touching a deleted object raises
- changing the set from inside a listener notification raises
  ("Changes cannot be triggered by notifications")
- parameters and tempo reject out of range values

Exceptions raised inside listeners are recorded in `errors` rather than
propagated, like Live logs them, and the test fixtures fail on them.
"""
import itertools
import types

_ptrs = itertools.count(1)
_notify_depth = 0
_MISSING = object()

# Exceptions raised by listeners or scheduled callbacks
errors = []


def _check_not_notifying(what):
	if _notify_depth > 0:
		raise RuntimeError(
			"Changes cannot be triggered by notifications. You will need to defer your response. ({})".format(what))


class LiveObject:
	"""
	Base for Live objects. Observable properties (listed in _observable) get
	add_<prop>_listener / remove_<prop>_listener / <prop>_has_listener.
	"""
	_observable = ()

	def __init__(self, **values):
		object.__setattr__(self, "_deleted", False)
		object.__setattr__(self, "_live_ptr", next(_ptrs))
		object.__setattr__(self, "_listeners", {name: [] for name in self._observable})
		object.__setattr__(self, "_values", dict(values))

	def __getattribute__(self, name):
		if not name.startswith("_") and object.__getattribute__(self, "_deleted"):
			raise RuntimeError("Object of type {} has been deleted".format(type(self).__name__))
		return object.__getattribute__(self, name)

	def __getattr__(self, name):
		listeners = object.__getattribute__(self, "_listeners")
		if name.startswith("add_") and name.endswith("_listener"):
			prop = name[len("add_"):-len("_listener")]
			if prop in listeners:
				return lambda cb: self._add_listener(prop, cb)
		if name.startswith("remove_") and name.endswith("_listener"):
			prop = name[len("remove_"):-len("_listener")]
			if prop in listeners:
				return lambda cb: self._remove_listener(prop, cb)
		if name.endswith("_has_listener"):
			prop = name[:-len("_has_listener")]
			if prop in listeners:
				return lambda cb: cb in listeners[prop]
		values = object.__getattribute__(self, "_values")
		if name in values:
			return values[name]
		raise AttributeError("{} has no attribute {}".format(type(self).__name__, name))

	def __setattr__(self, name, value):
		if name in self._values or name in self._observable:
			self._set_value(name, value)
		else:
			object.__setattr__(self, name, value)

	def _set_value(self, name, value, check=True):
		"""Change a property and notify its listeners, as if Live changed it"""
		if check:
			_check_not_notifying("setting {}.{}".format(type(self).__name__, name))
		validate = getattr(self, "_validate_" + name, None)
		if validate is not None:
			value = validate(value)
		old = self._values.get(name, _MISSING)
		self._values[name] = value
		if old is _MISSING or old != value:
			self._notify(name)
			after = getattr(self, "_after_set_" + name, None)
			if after is not None:
				after()

	def _add_listener(self, prop, cb):
		if cb in self._listeners[prop]:
			raise RuntimeError("Listener already connected")
		self._listeners[prop].append(cb)

	def _remove_listener(self, prop, cb):
		if cb not in self._listeners[prop]:
			raise RuntimeError("Listener not connected")
		self._listeners[prop].remove(cb)

	def _notify(self, prop):
		global _notify_depth
		if prop not in self._listeners:
			return
		_notify_depth += 1
		try:
			for cb in list(self._listeners[prop]):
				try:
					cb()
				except Exception as e:
					errors.append(e)
		finally:
			_notify_depth -= 1

	def _listener_count(self):
		return sum(len(cbs) for cbs in self._listeners.values())

	def _children(self):
		return []

	def _delete(self):
		for child in self._children():
			child._delete()
		object.__setattr__(self, "_deleted", True)


class DeviceParameter(LiveObject):
	_observable = ("name", "value")

	def __init__(self, name, value=0.0, min=0.0, max=1.0, is_quantized=False, on_change=None):
		super().__init__(name=name, value=value, min=min, max=max, is_quantized=is_quantized)
		object.__setattr__(self, "_on_change", on_change)

	def _validate_value(self, value):
		if not self.min <= value <= self.max:
			raise RuntimeError("Invalid value {} for {} (range {}-{})".format(value, self.name, self.min, self.max))
		return value

	def _after_set_value(self):
		if self._on_change is not None:
			self._on_change()


class Chain(LiveObject):
	_observable = ("devices",)

	def __init__(self, devices=()):
		super().__init__(devices=tuple(devices))

	def _children(self):
		return list(self._values["devices"])


class Device(LiveObject):
	_observable = ("name", "parameters", "is_active")

	def __init__(self, name, class_name="AudioEffectGroupDevice", parameters=()):
		super().__init__(name=name, class_name=class_name, type=2, is_active=True)
		on = DeviceParameter("Device On", 1.0, 0.0, 1.0, True, on_change=self._update_active)
		self._values["parameters"] = (on,) + tuple(parameters)

	def parameter(self, name):
		for p in self.parameters:
			if p.name == name:
				return p
		raise KeyError(name)

	def _update_active(self):
		self._set_value("is_active", self.parameters[0].value > 0.5, check=False)

	def _children(self):
		return list(self._values["parameters"])


class RackDevice(Device):
	_observable = Device._observable + ("chains",)

	def __init__(self, name, macros=(), chain_devices=()):
		"""macros: names of the rack's macros (up to 8)"""
		params = [DeviceParameter(m, 0.0, 0.0, 127.0) for m in macros]
		super().__init__(name, "AudioEffectGroupDevice", params)
		self._values["can_have_chains"] = True
		self._values["chains"] = (Chain(chain_devices),)

	def macro(self, i):
		return self.parameters[i + 1]

	def _children(self):
		return super()._children() + list(self._values["chains"])


class Clip(LiveObject):
	_observable = ("playing_status", "name")

	def __init__(self, is_playing=False, is_recording=False):
		super().__init__(name="", is_playing=is_playing, is_recording=is_recording, playing_status=0)

	def _set_playing(self, playing, recording=False):
		self._values["is_playing"] = playing
		self._values["is_recording"] = recording
		self._set_value("playing_status", self._values["playing_status"] + 1, check=False)


class ClipSlot(LiveObject):
	_observable = ("has_clip",)

	def __init__(self, track):
		super().__init__(has_clip=False, clip=None)
		object.__setattr__(self, "_track", track)
		object.__setattr__(self, "fire_count", 0)
		object.__setattr__(self, "fire_button_state", False)

	def fire(self):
		object.__setattr__(self, "fire_count", self.fire_count + 1)
		if self.has_clip:
			self.clip._set_playing(True)
		elif self._track.arm:
			# Firing an empty slot on an armed track starts recording a new clip
			self._create_clip(is_playing=True, is_recording=True)

	def set_fire_button_state(self, state):
		object.__setattr__(self, "fire_button_state", state)

	def delete_clip(self):
		_check_not_notifying("delete_clip")
		if not self.has_clip:
			raise RuntimeError("No clip in slot")
		self.clip._delete()
		self._values["clip"] = None
		self._set_value("has_clip", False)

	def _create_clip(self, is_playing=False, is_recording=False):
		"""Test helper: put a clip in the slot, as if the user recorded one"""
		self._values["clip"] = Clip(is_playing, is_recording)
		self._set_value("has_clip", True, check=False)
		return self.clip

	def _children(self):
		return [self._values["clip"]] if self._values["clip"] is not None else []


class RoutingType:
	"""An input routing option. Routing to a track follows the track if it's renamed"""

	def __init__(self, name=None, track=None):
		self._name = name
		self.attached_object = track

	@property
	def display_name(self):
		return self.attached_object.name if self.attached_object is not None else self._name

	def __eq__(self, other):
		return isinstance(other, RoutingType) and self._name == other._name and self.attached_object is other.attached_object

	def __hash__(self):
		return hash((self._name, id(self.attached_object)))


EXT_IN = RoutingType("Ext. In")
RESAMPLING = RoutingType("Resampling")
NO_INPUT = RoutingType("No Input")


class Track(LiveObject):
	_observable = (
		"name", "color", "devices", "arm", "current_monitoring_state",
		"input_routing_type", "available_input_routing_types", "clip_slots",
	)

	def __init__(self, song, name, num_scenes=8):
		super().__init__(
			name=name, color=0, devices=(), arm=False, current_monitoring_state=1,
			input_routing_type=EXT_IN, available_input_routing_types=(EXT_IN,),
		)
		object.__setattr__(self, "_song", song)
		self._values["clip_slots"] = tuple(ClipSlot(self) for _ in range(num_scenes))

	def _validate_current_monitoring_state(self, value):
		if value not in (0, 1, 2):
			raise RuntimeError("Invalid monitoring state {}".format(value))
		return value

	def _validate_input_routing_type(self, value):
		if value not in self.available_input_routing_types:
			raise RuntimeError("Invalid input routing type {}".format(value.display_name))
		return value

	def _after_set_name(self):
		self._song._refresh_routing()

	def add_device(self, device, index=None):
		"""Test helper: the user adds a device to the track"""
		devices = list(self.devices)
		devices.insert(len(devices) if index is None else index, device)
		self._set_value("devices", tuple(devices))
		return device

	def delete_device(self, index):
		_check_not_notifying("delete_device")
		devices = list(self.devices)
		device = devices.pop(index)
		device._delete()
		self._set_value("devices", tuple(devices))

	def _children(self):
		return list(self._values["devices"]) + list(self._values["clip_slots"])


class Song(LiveObject):
	_observable = ("tracks", "tempo", "metronome", "is_playing")

	def __init__(self):
		super().__init__(tracks=(), tempo=120.0, metronome=False, is_playing=False)

	def _validate_tempo(self, value):
		if not 20.0 <= value <= 999.0:
			raise RuntimeError("Invalid tempo {}".format(value))
		return value

	def create_audio_track(self, index=-1):
		_check_not_notifying("create_audio_track")
		tracks = list(self.tracks)
		if index == -1:
			index = len(tracks)
		if not 0 <= index <= len(tracks):
			raise RuntimeError("Invalid track index {}".format(index))
		track = Track(self, "{}-Audio".format(index + 1))
		tracks.insert(index, track)
		self._set_value("tracks", tuple(tracks))
		self._refresh_routing()
		return track

	def delete_track(self, index):
		_check_not_notifying("delete_track")
		tracks = list(self.tracks)
		track = tracks.pop(index)
		track._delete()
		self._set_value("tracks", tuple(tracks))
		self._refresh_routing()

	def continue_playing(self):
		_check_not_notifying("continue_playing")
		self._set_value("is_playing", True)

	def add_track(self, name, index=-1):
		"""Test helper: the user adds an audio track with a name"""
		track = self.create_audio_track(index)
		track.name = name
		return track

	def _refresh_routing(self):
		for track in self._values["tracks"]:
			available = (EXT_IN, RESAMPLING) + tuple(
				RoutingType(track=t) for t in self._values["tracks"] if t is not track) + (NO_INPUT,)
			# Live notifies when other tracks are added, removed or renamed
			track._values["available_input_routing_types"] = available
			track._notify("available_input_routing_types")

	def _children(self):
		return list(self._values["tracks"])

	def _all_objects(self):
		"""Every live object in the set, for checking listeners"""
		found = []
		def walk(obj):
			found.append(obj)
			for child in obj._children():
				walk(child)
		walk(self)
		return found


class _Application:
	def __init__(self):
		self._document = Song()

	def get_document(self):
		return self._document


_application = _Application()


def reset():
	"""Start a new, empty set. Returns the new Song"""
	global _application, _notify_depth
	_application = _Application()
	_notify_depth = 0
	del errors[:]
	return _application.get_document()


def _get_application():
	return _application


def _forward_midi_cc(script_handle, midi_map_handle, channel, cc, *a):
	midi_map_handle.forwarded_ccs.add((channel, cc))
	return True


def build_module():
	"""Builds the module object installed as `Live`"""
	live = types.ModuleType("Live")
	live.Application = types.SimpleNamespace(get_application=_get_application, Application=_Application)
	live.Song = types.SimpleNamespace(Song=Song)
	live.Track = types.SimpleNamespace(Track=Track)
	live.Device = types.SimpleNamespace(Device=Device)
	live.DeviceParameter = types.SimpleNamespace(DeviceParameter=DeviceParameter)
	live.RackDevice = types.SimpleNamespace(RackDevice=RackDevice)
	live.Chain = types.SimpleNamespace(Chain=Chain)
	live.Clip = types.SimpleNamespace(Clip=Clip)
	live.ClipSlot = types.SimpleNamespace(ClipSlot=ClipSlot)
	live.MidiMap = types.SimpleNamespace(forward_midi_cc=_forward_midi_cc)
	return live
