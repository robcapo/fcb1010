from fcb1010.led import LEDController, ON_CC, OFF_CC, SLOW_BLINK
from fcb1010.display import Display

from test_footswitch import Scheduler


def make_leds(active=True):
	sent = []
	scheduler = Scheduler()
	leds = LEDController(lambda cc, value: sent.append((cc, value)), scheduler, active)
	return leds, sent, scheduler


def test_on_off():
	leds, sent, _ = make_leds()
	leds.on(3)
	leds.off(3)
	assert sent == [(ON_CC, 3), (OFF_CC, 3)]


def test_inactive_controller_remembers_and_redraws_on_activate():
	leds, sent, _ = make_leds(active=False)
	leds.on(1)
	leds.off(2)
	leds.on(2)
	assert sent == []
	leds.activate()
	assert sorted(sent) == [(ON_CC, 1), (ON_CC, 2)]


def test_copy_starts_inactive_with_leds_off():
	leds, sent, _ = make_leds()
	copy = leds.copy([1, 2])
	assert sent == []
	copy.activate()
	assert sorted(sent) == [(OFF_CC, 1), (OFF_CC, 2)]


def test_blink_alternates_until_another_command():
	leds, sent, scheduler = make_leds()
	leds.blink_on(4)
	scheduler.tick(SLOW_BLINK * 3)
	assert {(ON_CC, 4), (OFF_CC, 4)} <= set(sent)
	leds.off(4)
	del sent[:]
	scheduler.tick(SLOW_BLINK * 3)
	assert sent == []


def test_deactivate_stops_blinking_and_activate_resumes_it():
	leds, sent, scheduler = make_leds()
	leds.blink_on(4)
	leds.deactivate()
	scheduler.tick(SLOW_BLINK * 2)
	del sent[:]
	scheduler.tick(SLOW_BLINK * 3)
	assert sent == []
	leds.activate()
	scheduler.tick(SLOW_BLINK * 3)
	assert {(ON_CC, 4), (OFF_CC, 4)} <= set(sent)


def test_display_letters_and_blanks():
	sent = []
	display = Display(lambda cc, value: sent.append((cc, value)))
	display.show("fx")
	display.show("A")
	display.clear()
	assert sent == [(109, 5), (110, 23), (109, 26), (110, 0), (109, 26), (110, 26)]
