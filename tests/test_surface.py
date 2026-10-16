from fcb1010.footswitch import FootSwitch

from harness import DOWN_CC, UP_CC, LEFT_EXPRESSION_CC, RIGHT_EXPRESSION_CC

MODE_LEDS = [20, 21]


def test_forwards_only_the_pedal_ccs(rig):
	rig.connect()
	assert rig.midi_map.forwarded_ccs == {
		(0, c) for c in (DOWN_CC, UP_CC, LEFT_EXPRESSION_CC, RIGHT_EXPRESSION_CC)}


def test_starts_in_racks_mode(rig):
	rig.connect()
	assert rig.display() == "FX"
	assert [rig.led_value(v) for v in MODE_LEDS] == [True, False]


def test_up_and_down_switch_modes(rig):
	rig.connect()
	rig.press(FootSwitch.DOWN)
	assert rig.display() == "LP"
	assert [rig.led_value(v) for v in MODE_LEDS] == [False, True]
	rig.press(FootSwitch.DOWN)
	assert rig.display() == "FX"
	rig.press(FootSwitch.UP)
	assert rig.display() == "LP"


def test_connect_and_disconnect_with_empty_set(rig):
	rig.connect()
	rig.tick(5)
	rig.disconnect()
	assert rig.display() == ""


def test_footswitches_without_a_track_do_nothing(rig):
	rig.connect()
	for mode in range(2):
		for fs in FootSwitch:
			if fs not in (FootSwitch.UP, FootSwitch.DOWN):
				rig.press(fs)
				rig.long_press(fs)
				rig.double_press(fs)
		rig.expression("left", 64)
		rig.expression("right", 64)
		rig.press(FootSwitch.DOWN)


def test_picks_up_fcb_track_added_or_renamed_later(rig, song):
	rig.connect()
	other = song.add_track("Bass")
	rig.tick()
	assert rig.surface._board._current_track is None
	other.name = "Bass #fcb"
	rig.tick()
	assert rig.surface._board._current_track is other


def test_uses_first_fcb_track(rig, song):
	song.add_track("Vox")
	first = song.add_track("Guitar #fcb")
	song.add_track("Keys #fcb")
	rig.connect()
	assert rig.surface._board._current_track is first


def test_deleting_the_fcb_track(rig, song):
	song.add_track("Guitar #fcb")
	rig.connect()
	rig.tick(2)
	song.delete_track(0)
	rig.tick(5)
	assert rig.surface._board._current_track is None
	for fs in (FootSwitch.ONE, FootSwitch.SIX):
		rig.press(fs)
	rig.press(FootSwitch.DOWN)
	rig.press(FootSwitch.ONE)
