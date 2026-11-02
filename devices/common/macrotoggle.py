"""MacroToggle: an on/off button that a rack macro can drive over 0-127.

	python3 macrotoggle.py

writes MacroToggle.maxpat, a standalone abstraction to load in a
bpatcher. Device build scripts import parts() instead and place the
toggle's objects straight into the device patcher, one set per button
with its own parameter name. (Wrapped in a bpatcher inside the device,
the button wasn't clickable in Live.)

Inside, the Live parameter is a live.numbox with an integer value from
0 to 127, so a macro maps onto it with a full 0-127 Min/Max. That value
is scaled to 0-1 and split at the midpoint, so 0-63 sends 0 and 64-127
sends 1 out of the outlet. The button you see is a live.text in Toggle
mode that lights from that 0/1; clicking it sets the parameter to 0 or
127. A number into the inlet sets the parameter too.

live.toggle and live.text can't be the parameter: both hold only 0 or 1
(sent 127, they store 1), and both light for any value above 0. So in a
device, the see-through numbox goes over the button's label, where Map
mode and right-click can reach it (see handle_rect).
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
APPVERSION = {"major": 8, "minor": 6, "revision": 5, "architecture": "x64", "modernui": 1}
SIZE = [16, 16]
CLEAR = [0.0, 0.0, 0.0, 0.0]
NUMBOX_COLOURS = ["activebgcolor", "bgcolor", "bordercolor", "focusbordercolor", "textcolor",
	"activeslidercolor", "slidercolor", "tricolor", "activetricolor", "tricolor2", "activetricolor2"]


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


def parts(prefix="", origin=(0, 0), longname="On", shortname="On", varname="on", initial=0,
		presentation_rect=(0, 0), handle_rect=None):
	"""The toggle's boxes and lines, with ids prefixed and positions offset.

	Returns (boxes, lines, param, outs, button): param is the Live
	parameter's box id, outs are the ids of the "0" and "1" messages that
	carry the output, and button is the visible button's box id.

	handle_rect, [x, y, w, h] in the device's presentation, is where the
	0-127 parameter sits on the panel, see-through, so Live's Map mode and
	right-click Map to Macro can reach it. Put it over the button's label,
	not the button: on top of the button it would take the button's clicks.
	"""
	ox, oy = origin

	def at(x, y, w, h):
		return [ox + x, oy + y, w, h]

	p = lambda name: prefix + name  # noqa: E731
	boxes = [
		# A live.numbox, not a live.text: a Toggle-mode live.text sent 127
		# stores 1, which reads as off.
		box(p("obj-param"), "live.numbox", at(20, 70, 44, 15), 1, 2, ["", "float"],
			parameter_enable=1, varname=varname,
			**({} if handle_rect is None else dict(
				presentation=1, presentation_rect=list(handle_rect),
				**{k: CLEAR for k in NUMBOX_COLOURS})),
			saved_attribute_attributes={"valueof": {
				"parameter_longname": longname,
				"parameter_shortname": shortname,
				"parameter_type": 1,
				"parameter_mmin": 0,
				"parameter_mmax": 127,
				"parameter_initial": [initial],
				"parameter_initial_enable": 1,
			}}),
		box(p("obj-scale"), "newobj", at(20, 110, 110, 22), 6, 1, [""], text="scale 0 127 0. 1."),
		box(p("obj-split"), "newobj", at(20, 140, 80, 22), 3, 2, ["", ""], text="split 0. 0.5"),
		box(p("obj-off"), "message", at(20, 170, 30, 22), 2, 1, [""], text="0"),
		box(p("obj-on"), "message", at(80, 170, 30, 22), 2, 1, [""], text="1"),
		box(p("obj-set"), "newobj", at(160, 170, 70, 22), 1, 1, [""], text="prepend set"),
		# The visible button is a parameter too, only so that Live draws it
		# lit when on (with parameters off it never lit). Hidden from Live
		# (parameter_invisible 2): it isn't automatable, mappable or saved.
		box(p("obj-button"), "live.text", at(160, 210, 16, 16), 1, 2, ["", ""],
			parameter_enable=1, mode=1, text="", texton="", varname=varname + "_button",
			presentation=1, presentation_rect=list(presentation_rect) + SIZE,
			saved_attribute_attributes={"valueof": {
				"parameter_longname": longname + " Button",
				"parameter_shortname": shortname,
				"parameter_type": 2,
				"parameter_enum": ["off", "on"],
				"parameter_mmax": 1,
				"parameter_invisible": 2,
			}}),
		box(p("obj-times"), "newobj", at(160, 250, 40, 22), 2, 1, ["int"], text="* 127"),
		# Trace in the Max Console while the button's behaviour is checked.
		box(p("obj-print-click"), "newobj", at(240, 250, 120, 22), 1, 0, text=f"print {varname}-click"),
		box(p("obj-print-param"), "newobj", at(240, 70, 120, 22), 1, 0, text=f"print {varname}-param"),
		box(p("obj-print-out"), "newobj", at(240, 170, 120, 22), 1, 0, text=f"print {varname}-out"),
	]
	lines = [
		line(p("obj-param"), 0, p("obj-scale"), 0),
		line(p("obj-scale"), 0, p("obj-split"), 0),
		line(p("obj-split"), 0, p("obj-off"), 0),
		line(p("obj-split"), 1, p("obj-on"), 0),
		line(p("obj-off"), 0, p("obj-set"), 0),
		line(p("obj-on"), 0, p("obj-set"), 0),
		line(p("obj-set"), 0, p("obj-button"), 0),
		line(p("obj-button"), 0, p("obj-times"), 0),
		line(p("obj-times"), 0, p("obj-param"), 0),
		line(p("obj-button"), 0, p("obj-print-click"), 0),
		line(p("obj-param"), 0, p("obj-print-param"), 0),
		line(p("obj-off"), 0, p("obj-print-out"), 0),
		line(p("obj-on"), 0, p("obj-print-out"), 0),
	]
	return boxes, lines, p("obj-param"), [p("obj-off"), p("obj-on")], p("obj-button")


def patcher(**names):
	"""The standalone abstraction: parts() plus an inlet and an outlet."""
	boxes, lines, param, outs, button = parts(**names)
	boxes.append(box("obj-in", "inlet", [20, 20, 30, 30], 0, 1, [""], comment="0-127 sets the toggle"))
	boxes.append(box("obj-out", "outlet", [20, 290, 30, 30], 1, 0, comment="0 off, 1 on"))
	lines.append(line("obj-in", 0, param, 0))
	lines.extend(line(o, 0, "obj-out", 0) for o in outs)
	longname = names.get("longname", "On")
	return {
		"fileversion": 1,
		"appversion": APPVERSION,
		"classnamespace": "box",
		"rect": [100, 100, 320, 340],
		"openinpresentation": 1,
		"boxes": boxes,
		"lines": lines,
		"parameters": {
			"obj-param": [longname, names.get("shortname", "On"), 0],
			"obj-button": [longname + " Button", names.get("shortname", "On"), 0],
			"inherited_shortname": 1,
		},
		"autosave": 0,
	}


def main():
	with open(os.path.join(HERE, "MacroToggle.maxpat"), "w") as f:
		f.write(json.dumps({"patcher": patcher()}, indent="\t") + "\n")


if __name__ == "__main__":
	main()
