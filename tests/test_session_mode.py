"""SessionMode, the LP mode: ch1-ch4 looper tracks next to the #fcb track"""
import pytest

from fcb1010.footswitch import FootSwitch

CHANNEL_SWITCHES = [FootSwitch.ONE, FootSwitch.TWO, FootSwitch.THREE, FootSwitch.FOUR]


@pytest.fixture
def main(song):
	song.add_track("Drums")
	track = song.add_track("Guitar #fcb")
	track.color = 5
	song.add_track("Bass")
	return track


def channels(song):
	return [t for t in song.tracks if t.name.startswith("ch")]


def session_rig(rig):
	rig.connect()
	rig.press(FootSwitch.DOWN)
	assert rig.display() == "LP"
	return rig


def test_creates_channel_tracks_next_to_main_track(rig, song, main):
	session_rig(rig)
	assert [t.name for t in song.tracks] == ["Drums", "Guitar #fcb", "ch1", "ch2", "ch3", "ch4", "Bass"]
	for ch in channels(song):
		assert ch.arm is True
		assert ch.current_monitoring_state == 2
		assert ch.color == 5
		assert ch.input_routing_type.attached_object is main


def test_reuses_existing_channel_tracks(rig, song, main):
	session_rig(rig)
	rig.disconnect()
	rig.connect()
	rig.tick()
	assert len(channels(song)) == 4


def test_renaming_main_track_keeps_routing(rig, song, main):
	session_rig(rig)
	main.name = "Lead #fcb"
	rig.tick(2)
	for ch in channels(song):
		assert ch.input_routing_type.display_name == "Lead #fcb"


def test_footswitch_fires_its_channel(rig, song, main):
	session_rig(rig)
	for i, fs in enumerate(CHANNEL_SWITCHES):
		rig.press(fs)
		assert channels(song)[i].clip_slots[0].fire_count == 1


def test_led_blinks_for_stopped_clip_and_is_on_while_playing(rig, song, main):
	session_rig(rig)
	slot = channels(song)[0].clip_slots[0]
	assert rig.led(FootSwitch.ONE) is False
	clip = slot._create_clip(is_playing=False)
	assert rig.led_states(FootSwitch.ONE) == {True, False}
	clip._set_playing(True)
	assert rig.led_states(FootSwitch.ONE) == {True}
	clip._set_playing(False)
	assert rig.led_states(FootSwitch.ONE) == {True, False}


def test_recording_a_clip_lights_the_led(rig, song, main):
	session_rig(rig)
	rig.press(FootSwitch.TWO)
	assert channels(song)[1].clip_slots[0].has_clip
	assert rig.led_states(FootSwitch.TWO) == {True}


def test_double_press_deletes_clip(rig, song, main):
	session_rig(rig)
	slot = channels(song)[2].clip_slots[0]
	slot._create_clip(is_playing=True)
	rig.double_press(FootSwitch.THREE)
	assert not slot.has_clip
	assert rig.led_states(FootSwitch.THREE) == {False}


def test_deleting_a_channel_track(rig, song, main):
	session_rig(rig)
	song.delete_track(2)
	rig.tick(2)
	rig.press(FootSwitch.ONE)
	rig.double_press(FootSwitch.ONE)


def test_deleting_main_track(rig, song, main):
	session_rig(rig)
	song.delete_track(1)
	rig.tick(2)
	for fs in CHANNEL_SWITCHES:
		rig.press(fs)


def test_hold_five_toggles_metronome_and_starts_playback(rig, song, main):
	session_rig(rig)
	rig.long_press(FootSwitch.FIVE)
	assert song.metronome is True
	assert song.is_playing is True
	assert rig.led(FootSwitch.FIVE) is True
	rig.long_press(FootSwitch.FIVE)
	assert song.metronome is False
	assert rig.led(FootSwitch.FIVE) is False


def test_tap_tempo(rig, song, main):
	session_rig(rig)
	for _ in range(4):
		rig.down(FootSwitch.FIVE)
		rig.up(FootSwitch.FIVE)
		rig.clock += 0.5
	assert song.tempo == pytest.approx(120.0)


def test_tap_tempo_clamps_to_live_range(rig, song, main):
	session_rig(rig)
	for _ in range(3):
		rig.down(FootSwitch.FIVE)
		rig.up(FootSwitch.FIVE)
		rig.clock += 0.01
	assert song.tempo == 999.0


def test_works_without_main_track_until_one_appears(rig, song):
	session_rig(rig)
	rig.press(FootSwitch.ONE)
	main = song.add_track("Guitar #fcb")
	rig.tick(2)
	assert [t.name for t in song.tracks] == ["Guitar #fcb", "ch1", "ch2", "ch3", "ch4"]
