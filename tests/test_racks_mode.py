"""RacksControllerMode, the FX mode: top row picks a #rack, bottom row runs its macros"""
import pytest

from fcb1010.footswitch import FootSwitch
from fakes.live import RackDevice, Device


def rack(name, *macros):
	return RackDevice(name, macros=macros)


@pytest.fixture
def track(song):
	return song.add_track("Guitar #fcb")


@pytest.fixture
def racks(track):
	clean = track.add_device(rack("Clean #rack", "Boost #s1pt", "Wah #s5hel", "Level #s2ps100"))
	drive = track.add_device(rack("Drive #rack", "Gain #s1pt20-90"))
	return clean, drive


def test_first_rack_selected_on_connect(rig, racks):
	clean, drive = racks
	rig.connect()
	rig.tick()
	assert clean.parameter("Device On").value == 1.0
	assert drive.parameter("Device On").value == 0.0
	assert rig.led(FootSwitch.SIX) is True
	assert rig.led(FootSwitch.SEVEN) is False


def test_top_row_switches_patch(rig, racks):
	clean, drive = racks
	rig.connect()
	rig.press(FootSwitch.SEVEN)
	assert clean.parameter("Device On").value == 0.0
	assert drive.parameter("Device On").value == 1.0
	assert (rig.led(FootSwitch.SIX), rig.led(FootSwitch.SEVEN)) == (False, True)


def test_switch_without_a_rack_does_nothing(rig, racks):
	clean, _ = racks
	rig.connect()
	rig.press(FootSwitch.TEN)
	assert clean.parameter("Device On").value == 1.0


def test_press_toggles_macro_and_led_follows(rig, racks):
	clean, _ = racks
	rig.connect()
	boost = clean.macro(0)
	rig.press(FootSwitch.ONE)
	assert boost.value == 127.0
	assert rig.led(FootSwitch.ONE) is True
	rig.press(FootSwitch.ONE)
	assert boost.value == 0.0
	assert rig.led(FootSwitch.ONE) is False


def test_led_follows_macro_changed_in_live(rig, racks):
	clean, _ = racks
	rig.connect()
	clean.macro(0).value = 100.0
	assert rig.led(FootSwitch.ONE) is True


def test_toggle_with_range(rig, racks):
	_, drive = racks
	rig.connect()
	rig.press(FootSwitch.SEVEN)
	rig.press(FootSwitch.ONE)
	assert drive.macro(0).value == 90.0
	rig.press(FootSwitch.ONE)
	assert drive.macro(0).value == 20.0


def test_set_value(rig, racks):
	clean, _ = racks
	rig.connect()
	rig.press(FootSwitch.TWO)
	assert clean.macro(2).value == 100.0


def test_hold_assigns_expression_pedal(rig, racks):
	clean, _ = racks
	rig.connect()
	wah = clean.macro(1)
	rig.expression("left", 127)
	assert wah.value == 0.0
	rig.long_press(FootSwitch.FIVE)
	rig.expression("left", 127)
	assert wah.value == 127.0
	rig.expression("left", 0)
	assert wah.value == 0.0
	rig.expression("right", 127)
	assert wah.value == 0.0


def test_switching_patch_clears_expression(rig, racks):
	clean, _ = racks
	rig.connect()
	rig.long_press(FootSwitch.FIVE)
	rig.press(FootSwitch.SEVEN)
	rig.press(FootSwitch.SIX)
	rig.expression("left", 127)
	assert clean.macro(1).value == 0.0


def test_renaming_macro_unassigns_expression(rig, racks):
	clean, _ = racks
	rig.connect()
	wah = clean.macro(1)
	rig.long_press(FootSwitch.FIVE)
	wah.name = "Wah"
	rig.expression("left", 127)
	assert wah.value == 0.0


def test_renaming_macro_reprograms_switch(rig, racks):
	clean, _ = racks
	rig.connect()
	clean.macro(0).name = "Boost #s3pt"
	rig.press(FootSwitch.ONE)
	assert clean.macro(0).value == 0.0
	rig.press(FootSwitch.THREE)
	assert clean.macro(0).value == 127.0


def test_stays_on_selected_patch_when_devices_change(rig, track, racks):
	_, drive = racks
	rig.connect()
	rig.press(FootSwitch.SEVEN)
	track.add_device(Device("EQ Eight", "Eq8"), 0)
	rig.tick()
	assert drive.parameter("Device On").value == 1.0
	assert rig.led(FootSwitch.SEVEN) is True
	rig.press(FootSwitch.ONE)
	assert drive.macro(0).value == 90.0


def test_deleting_the_selected_rack(rig, track, racks):
	clean, drive = racks
	rig.connect()
	rig.press(FootSwitch.SEVEN)
	track.delete_device(1)
	rig.tick()
	assert clean.parameter("Device On").value == 1.0
	rig.press(FootSwitch.ONE)
	assert clean.macro(0).value == 127.0
	assert rig.led(FootSwitch.SEVEN) is False


def test_renaming_rack_removes_it(rig, racks):
	clean, drive = racks
	rig.connect()
	clean.name = "Clean"
	rig.tick()
	assert drive.parameter("Device On").value == 1.0
	rig.press(FootSwitch.ONE)
	assert drive.macro(0).value == 90.0


def test_switching_mode_and_back_keeps_working(rig, racks):
	clean, _ = racks
	rig.connect()
	rig.press(FootSwitch.DOWN)
	rig.press(FootSwitch.ONE)
	assert clean.macro(0).value == 0.0
	rig.press(FootSwitch.UP)
	rig.press(FootSwitch.ONE)
	assert clean.macro(0).value == 127.0
	assert rig.led(FootSwitch.ONE) is True


def test_bad_macro_specs_are_ignored(rig, track):
	r = track.add_device(rack("Odd #rack", "#s1 #s1x #s1ta-b #s1sx #s9pt #s1p"))
	rig.connect()
	rig.press(FootSwitch.ONE)
	assert r.macro(0).value == 0.0


def test_quantized_macro_rounds_expression(rig, track):
	r = track.add_device(rack("Steps #rack", "Mode #s1pel"))
	rig.connect()
	mode = r.macro(0)
	object.__setattr__(mode, "_values", dict(mode._values, is_quantized=True, max=3.0))
	rig.press(FootSwitch.ONE)
	rig.expression("left", 70)
	assert mode.value == 2


def test_deleting_track_mid_use(rig, song, racks):
	rig.connect()
	rig.long_press(FootSwitch.FIVE)
	song.delete_track(0)
	rig.tick()
	rig.expression("left", 100)
	rig.press(FootSwitch.ONE)
	rig.press(FootSwitch.SEVEN)
