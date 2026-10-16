"""
A fake of the parts of Ableton's `ableton.v2` framework the script uses,
installed as `sys.modules["ableton.v2..."]` by conftest.py.

Scheduling follows ableton.v2's ControlSurface: schedule_message(0, cb)
runs on the next update_display tick, and a delay of N runs N ticks later.
Live calls update_display roughly every 100ms.
"""
from contextlib import contextmanager
import types

from . import live


def liveobj_valid(obj):
	return obj is not None and not getattr(obj, "_deleted", False)


class ControlSurface:
	def __init__(self, c_instance, *a, **k):
		self._c_instance = c_instance
		self._scheduled = []
		self._midi_listeners = []

	@contextmanager
	def component_guard(self):
		yield

	def schedule_message(self, delay_in_ticks, callback, parameter=None):
		assert delay_in_ticks >= 0
		self._scheduled.append([delay_in_ticks, callback, parameter])

	def update_display(self):
		"""One tick of Live's main loop: run scheduled messages that are due"""
		due = []
		for message in list(self._scheduled):
			if message[0] == 0:
				self._scheduled.remove(message)
				due.append(message)
			else:
				message[0] -= 1
		for _, callback, parameter in due:
			try:
				if parameter is None:
					callback()
				else:
					callback(parameter)
			except Exception as e:
				live.errors.append(e)

	def add_received_midi_listener(self, cb):
		if cb in self._midi_listeners:
			raise RuntimeError("Listener already connected")
		self._midi_listeners.append(cb)

	def remove_received_midi_listener(self, cb):
		self._midi_listeners.remove(cb)

	def received_midi_has_listener(self, cb):
		return cb in self._midi_listeners

	def receive_midi(self, midi_bytes):
		for cb in list(self._midi_listeners):
			cb(*midi_bytes)

	def build_midi_map(self, midi_map_handle):
		pass

	def disconnect(self):
		self._scheduled = []


def build_modules():
	"""The modules to install under these names in sys.modules"""
	ableton = types.ModuleType("ableton")
	v2 = types.ModuleType("ableton.v2")
	base = types.ModuleType("ableton.v2.base")
	control_surface = types.ModuleType("ableton.v2.control_surface")
	base.liveobj_valid = liveobj_valid
	control_surface.ControlSurface = ControlSurface
	ableton.v2 = v2
	v2.base = base
	v2.control_surface = control_surface
	return {
		"ableton": ableton,
		"ableton.v2": v2,
		"ableton.v2.base": base,
		"ableton.v2.control_surface": control_surface,
	}
