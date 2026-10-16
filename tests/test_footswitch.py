import pytest

from fcb1010.footswitch import (
	FootSwitch, EventType, Layout, FootSwitchEventBus, Notifier, value_to_switch)

CC = 0xB0


class Scheduler:
	"""Same timing as ableton.v2: a delay of N runs on the N+1th tick"""
	def __init__(self):
		self.messages = []

	def __call__(self, delay, cb):
		self.messages.append([delay, cb])

	def tick(self, n=1):
		for _ in range(n):
			due = [m for m in self.messages if m[0] == 0]
			self.messages = [m for m in self.messages if m[0] != 0]
			for m in self.messages:
				m[0] -= 1
			for _, cb in due:
				cb()


@pytest.fixture
def scheduler():
	return Scheduler()


@pytest.fixture
def events():
	return []


def make_bus(scheduler, events, switch=FootSwitch.ONE, types=tuple(EventType)):
	bus = FootSwitchEventBus(scheduler)
	layout = Layout()
	for t in types:
		layout.listen(switch, t, events.append)
	bus.install(layout)
	return bus, layout


def down(bus, value=1):
	bus.midi_callback(CC, 104, value)


def up(bus, value=1):
	bus.midi_callback(CC, 105, value)


def test_press_fires_on_release_without_double_press(scheduler, events):
	bus, _ = make_bus(scheduler, events, types=(EventType.DOWN, EventType.UP, EventType.PRESS))
	down(bus)
	assert events == [EventType.DOWN]
	up(bus)
	assert events == [EventType.DOWN, EventType.UP, EventType.PRESS]


def test_press_waits_for_double_press_window(scheduler, events):
	bus, _ = make_bus(scheduler, events, types=(EventType.PRESS, EventType.DOUBLE_PRESS))
	down(bus)
	up(bus)
	scheduler.tick(Notifier.DOUBLE_PRESS_TICKS)
	assert events == []
	scheduler.tick()
	assert events == [EventType.PRESS]


def test_double_press(scheduler, events):
	bus, _ = make_bus(scheduler, events, types=(EventType.PRESS, EventType.DOUBLE_PRESS))
	down(bus)
	up(bus)
	scheduler.tick(2)
	down(bus)
	up(bus)
	scheduler.tick(20)
	assert events == [EventType.DOUBLE_PRESS]


def test_long_press_fires_while_held_and_suppresses_press(scheduler, events):
	bus, _ = make_bus(scheduler, events, types=(EventType.PRESS, EventType.LONG_PRESS, EventType.DOUBLE_PRESS))
	down(bus)
	scheduler.tick(Notifier.LONG_PRESS_TICKS)
	assert events == []
	scheduler.tick()
	assert events == [EventType.LONG_PRESS]
	up(bus)
	scheduler.tick(20)
	assert events == [EventType.LONG_PRESS]


def test_quick_release_cancels_long_press(scheduler, events):
	bus, _ = make_bus(scheduler, events, types=(EventType.PRESS, EventType.LONG_PRESS))
	down(bus)
	scheduler.tick(2)
	up(bus)
	scheduler.tick(20)
	assert events == [EventType.PRESS]


def test_second_press_after_window_is_two_presses(scheduler, events):
	bus, _ = make_bus(scheduler, events, types=(EventType.PRESS, EventType.DOUBLE_PRESS))
	for _ in range(2):
		down(bus)
		up(bus)
		scheduler.tick(Notifier.DOUBLE_PRESS_TICKS + 1)
	assert events == [EventType.PRESS, EventType.PRESS]


def test_uninstall_removes_callbacks(scheduler, events):
	bus, layout = make_bus(scheduler, events)
	bus.uninstall(layout)
	down(bus)
	up(bus)
	scheduler.tick(20)
	assert events == []


def test_switches_are_independent(scheduler, events):
	bus, _ = make_bus(scheduler, events, switch=FootSwitch.TEN, types=(EventType.PRESS,))
	down(bus, 1)
	up(bus, 1)
	assert events == []
	down(bus, 0)
	up(bus, 0)
	assert events == [EventType.PRESS]


def test_unknown_values_and_messages_are_ignored(scheduler, events):
	bus, _ = make_bus(scheduler, events)
	down(bus, 99)
	bus.midi_callback(0x90, 104, 1)
	bus.midi_callback(CC, 50, 1)
	assert events == []


def test_expression_pedals(scheduler):
	bus = FootSwitchEventBus(scheduler)
	left, right = [], []
	layout = Layout()
	layout.set_left_expression_callback(left.append)
	layout.set_right_expression_callback(right.append)
	bus.install(layout)
	bus.midi_callback(CC, 102, 10)
	bus.midi_callback(CC, 103, 20)
	assert (left, right) == ([10], [20])
	bus.uninstall(layout)
	bus.midi_callback(CC, 102, 30)
	assert left == [10]


def test_exception_in_callback_does_not_break_the_bus(scheduler, events):
	bus = FootSwitchEventBus(scheduler)
	layout = Layout()
	layout.listen(FootSwitch.ONE, EventType.DOWN, lambda e: 1 / 0)
	layout.listen(FootSwitch.ONE, EventType.PRESS, events.append)
	bus.install(layout)
	down(bus)
	up(bus)
	assert events == [EventType.PRESS]


def test_value_to_switch():
	assert value_to_switch(0) is FootSwitch.TEN
	assert value_to_switch(10) is FootSwitch.UP
	assert value_to_switch(11) is FootSwitch.DOWN
	assert value_to_switch(12) is None


def test_layout_union_overrides_matching_events():
	a, b = Layout(), Layout()
	a.listen(FootSwitch.ONE, EventType.PRESS, "a-press")
	a.listen(FootSwitch.ONE, EventType.DOWN, "a-down")
	b.listen(FootSwitch.ONE, EventType.PRESS, "b-press")
	a.union_with(b)
	assert a.get_callbacks()[FootSwitch.ONE] == {EventType.PRESS: "b-press", EventType.DOWN: "a-down"}
