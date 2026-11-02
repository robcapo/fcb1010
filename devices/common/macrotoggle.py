"""MacroToggle: an on/off button that a rack macro can drive over 0-127.

	python3 macrotoggle.py

writes MacroToggle.maxpat, a standalone abstraction to load in a
bpatcher. Device build scripts import patcher() instead and embed a copy
per button, each with its own parameter name.

Inside, the Live parameter is a hidden live.text with an integer value
from 0 to 127, so a macro maps onto it with a full 0-127 Min/Max. That
value is scaled to 0-1 and split at the midpoint, so 0-63 sends 0 and
64-127 sends 1 out of the outlet. The button you see is a second
live.text, in Toggle mode like a live.toggle, that isn't a parameter. It
lights from that same 0/1, and clicking it sets the parameter to 0 or
127. A number into the inlet sets the parameter too.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
APPVERSION = {"major": 8, "minor": 6, "revision": 5, "architecture": "x64", "modernui": 1}
SIZE = [16, 16]


def box(id, maxclass, rect, numinlets, numoutlets, outlettype=None, **attrs):
	b = {
		"id": id,
		"maxclass": maxclass,
		"numinlets": numinlets,
		"numoutlets": numoutlets,
		"patching_rect": rect,
	}
	if outlettype is not None:
		b["outlettype"] = outlettype
	b.update(attrs)
	return {"box": b}


def line(src, outlet, dst, inlet):
	return {"patchline": {"source": [src, outlet], "destination": [dst, inlet]}}


def patcher(longname="On", shortname="On", varname="on", initial=0):
	"""The toggle's patcher. Its Live parameter is the box "obj-param"."""
	boxes = [
		box("obj-in", "inlet", [20, 20, 30, 30], 0, 1, [""], comment="0-127 sets the toggle"),
		box("obj-param", "live.text", [20, 70, 40, 20], 1, 2, ["", ""],
			parameter_enable=1, mode=1, text=longname, texton=longname, varname=varname,
			saved_attribute_attributes={"valueof": {
				"parameter_longname": longname,
				"parameter_shortname": shortname,
				"parameter_type": 1,
				"parameter_mmin": 0,
				"parameter_mmax": 127,
				"parameter_initial": [initial],
				"parameter_initial_enable": 1,
			}}),
		box("obj-scale", "newobj", [20, 110, 110, 22], 6, 1, [""], text="scale 0 127 0. 1."),
		box("obj-split", "newobj", [20, 140, 80, 22], 3, 2, ["", ""], text="split 0. 0.5"),
		box("obj-off", "message", [20, 170, 30, 22], 2, 1, [""], text="0"),
		box("obj-on", "message", [80, 170, 30, 22], 2, 1, [""], text="1"),
		box("obj-out", "outlet", [20, 290, 30, 30], 1, 0, comment="0 off, 1 on"),
		box("obj-set", "newobj", [160, 170, 70, 22], 1, 1, [""], text="prepend set"),
		box("obj-button", "live.text", [160, 210, 16, 16], 1, 2, ["", ""],
			parameter_enable=0, mode=1, text="", texton="",
			presentation=1, presentation_rect=[0, 0] + SIZE),
		box("obj-times", "newobj", [160, 250, 40, 22], 2, 1, ["int"], text="* 127"),
	]
	lines = [
		line("obj-in", 0, "obj-param", 0),
		line("obj-param", 0, "obj-scale", 0),
		line("obj-scale", 0, "obj-split", 0),
		line("obj-split", 0, "obj-off", 0),
		line("obj-split", 1, "obj-on", 0),
		line("obj-off", 0, "obj-out", 0),
		line("obj-on", 0, "obj-out", 0),
		line("obj-off", 0, "obj-set", 0),
		line("obj-on", 0, "obj-set", 0),
		line("obj-set", 0, "obj-button", 0),
		line("obj-button", 0, "obj-times", 0),
		line("obj-times", 0, "obj-param", 0),
	]
	return {
		"fileversion": 1,
		"appversion": APPVERSION,
		"classnamespace": "box",
		"rect": [100, 100, 320, 340],
		"openinpresentation": 1,
		"boxes": boxes,
		"lines": lines,
		"parameters": {"obj-param": [longname, shortname, 0], "inherited_shortname": 1},
		"autosave": 0,
	}


def bpatcher(id, rect, presentation_rect, **names):
	"""A bpatcher box embedding a copy of the toggle, sized to the button."""
	return box(id, "bpatcher", rect + SIZE, 1, 1, [""],
		embed=1, patcher=patcher(**names), presentation=1,
		presentation_rect=presentation_rect + SIZE, offset=[0.0, 0.0],
		bgmode=0, border=0, clickthrough=0, enablehscroll=0, enablevscroll=0,
		lockeddragscroll=0, viewvisibility=1)


def main():
	with open(os.path.join(HERE, "MacroToggle.maxpat"), "w") as f:
		f.write(json.dumps({"patcher": patcher()}, indent="\t") + "\n")


if __name__ == "__main__":
	main()
