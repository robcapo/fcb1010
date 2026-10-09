import logging

logger = logging.getLogger(__name__)

TENS_CC = 109
ONES_CC = 110

# Values 0-25 are A-Z, anything above turns the digit off
OFF_VALUE = 26

class Display:
	"""
	Controls the 10's and 1's digits of the seven segment display.
	Each digit can show a letter A-Z or be off.
	"""
	def __init__(self, send_cc):
		self._send_cc = send_cc

	def show(self, text):
		"""
		Shows up to two characters, right aligned. Anything that isn't
		a letter (e.g. a space) turns that digit off.
		"""
		text = text.upper().rjust(2)[-2:]
		self._send_cc(TENS_CC, _char_value(text[0]))
		self._send_cc(ONES_CC, _char_value(text[1]))

	def clear(self):
		self.show("")

def _char_value(char):
	if "A" <= char <= "Z":
		return ord(char) - ord("A")
	return OFF_VALUE
