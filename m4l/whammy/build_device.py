"""
Builds the FCB Whammy Max for Live device from fcb_whammy.genexpr.

	python3 m4l/whammy/build_device.py

Writes "FCB Whammy.maxpat" (the device's patcher) and "FCB Whammy.amxd"
(the same patcher, packaged as a Max for Live audio effect) next to this
script.
"""
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "FCB Whammy"

# In the order of the mode numbers in fcb_whammy.genexpr
MODES = [
	"2 Oct Up", "Oct Up", "5th Up", "4th Up", "2nd Down", "4th Down",
	"5th Down", "Oct Down", "2 Oct Down", "Dive Bomb",
	"Deep Detune", "Shallow Detune",
	"Oct Dn/Oct Up", "5th Dn/4th Dn", "4th Dn/3rd Dn", "5th Up/7th Up",
	"5th Up/6th Up", "4th Up/5th Up", "3rd Up/4th Up", "b3rd Up/3rd Up",
	"2nd Up/3rd Up",
]

_boxes = []
_lines = []

def box(maxclass, rect, text = None, inlets = 1, outlets = 0, outlettype = None, **extra):
	ident = "obj-{}".format(len(_boxes) + 1)
	b = {
		"id": ident,
		"maxclass": maxclass,
		"numinlets": inlets,
		"numoutlets": outlets,
		"patching_rect": rect,
	}
	if outlets:
		b["outlettype"] = outlettype or [""] * outlets
	if text is not None:
		b["text"] = text
	b.update(extra)
	_boxes.append({"box": b})
	return ident

def line(src, src_outlet, dst, dst_inlet):
	_lines.append({"patchline": {"source": [src, src_outlet], "destination": [dst, dst_inlet]}})

def param(longname, kind, initial, mmax = None, enum = None, unitstyle = None):
	attrs = {
		"parameter_longname": longname,
		"parameter_shortname": longname,
		"parameter_type": kind,
		"parameter_initial_enable": 1,
		"parameter_initial": [initial],
	}
	if mmax is not None:
		attrs["parameter_mmin"] = 0
		attrs["parameter_mmax"] = mmax
	if enum is not None:
		attrs["parameter_enum"] = enum
	if unitstyle is not None:
		attrs["parameter_unitstyle"] = unitstyle
	return {"varname": longname, "saved_attribute_attributes": {"valueof": attrs}}

def gen_patcher(code):
	boxes = []
	lines = []
	def gbox(ident, maxclass, rect, text = None, inlets = 0, outlets = 0, **extra):
		b = {"id": ident, "maxclass": maxclass, "numinlets": inlets, "numoutlets": outlets, "patching_rect": rect}
		if outlets:
			b["outlettype"] = [""] * outlets
		if text is not None:
			b["text"] = text
		b.update(extra)
		boxes.append({"box": b})
	for i in range(2):
		gbox("in-{}".format(i + 1), "newobj", [20 + 120 * i, 20, 40, 22], "in {}".format(i + 1), outlets = 1)
		lines.append({"patchline": {"source": ["in-{}".format(i + 1), 0], "destination": ["code", i]}})
	gbox("code", "codebox", [20, 60, 600, 500], inlets = 2, outlets = 2, code = code, fontface = 0, fontname = "<Monospaced>", fontsize = 12)
	for i in range(2):
		gbox("out-{}".format(i + 1), "newobj", [20 + 120 * i, 580, 45, 22], "out {}".format(i + 1), inlets = 1)
		lines.append({"patchline": {"source": ["code", i], "destination": ["out-{}".format(i + 1), 0]}})
	return {
		"fileversion": 1,
		"appversion": {"major": 8, "minor": 5, "revision": 0, "architecture": "x64", "modernui": 1},
		"classnamespace": "dsp.gen",
		"rect": [100, 100, 700, 650],
		"boxes": boxes,
		"lines": lines,
	}

def build():
	with open(os.path.join(HERE, "fcb_whammy.genexpr")) as f:
		code = f.read()

	plugin = box("newobj", [20, 20, 60, 22], "plugin~", inlets = 2, outlets = 2, outlettype = ["signal", "signal"])
	gen = box("newobj", [20, 200, 300, 22], "gen~", inlets = 2, outlets = 2,
		outlettype = ["signal", "signal"], patcher = gen_patcher(code))
	plugout = box("newobj", [20, 260, 60, 22], "plugout~", inlets = 2)
	line(plugin, 0, gen, 0)
	line(plugin, 1, gen, 1)
	line(gen, 0, plugout, 0)
	line(gen, 1, plugout, 1)

	mode = box("live.menu", [200, 20, 100, 15], inlets = 1, outlets = 3, outlettype = ["", "", "float"],
		presentation = 1, presentation_rect = [8, 24, 100, 15], **param("Mode", 2, 1, mmax = len(MODES) - 1, enum = MODES))
	mode_msg = box("newobj", [200, 60, 90, 22], "prepend mode", outlets = 1)
	line(mode, 0, mode_msg, 0)
	line(mode_msg, 0, gen, 0)

	treadle = box("live.dial", [320, 20, 44, 48], inlets = 1, outlets = 2, outlettype = ["", "float"],
		presentation = 1, presentation_rect = [116, 8, 44, 48], **param("Treadle", 0, 0, mmax = 127))
	treadle_msg = box("newobj", [320, 80, 100, 22], "prepend treadle", outlets = 1)
	line(treadle, 0, treadle_msg, 0)
	line(treadle_msg, 0, gen, 0)

	active = box("live.toggle", [440, 20, 15, 15], inlets = 1, outlets = 1,
		presentation = 1, presentation_rect = [8, 48, 15, 15], **param("Active", 2, 1, enum = ["off", "on"]))
	active_msg = box("newobj", [440, 60, 70, 22], "prepend on", outlets = 1)
	line(active, 0, active_msg, 0)
	line(active_msg, 0, gen, 0)

	box("comment", [200, 0, 60, 18], "Mode", presentation = 1, presentation_rect = [8, 6, 60, 18])
	box("comment", [460, 18, 50, 18], "Active", presentation = 1, presentation_rect = [26, 46, 50, 18])

	patcher = {
		"patcher": {
			"fileversion": 1,
			"appversion": {"major": 8, "minor": 5, "revision": 0, "architecture": "x64", "modernui": 1},
			"classnamespace": "box",
			"rect": [100, 100, 700, 400],
			"openinpresentation": 1,
			"devicewidth": 170.0,
			"boxes": _boxes,
			"lines": _lines,
		}
	}
	text = json.dumps(patcher, indent = "\t")

	with open(os.path.join(HERE, NAME + ".maxpat"), "w") as f:
		f.write(text)

	# A .amxd is the patcher JSON with a small header. "aaaa" marks an audio effect.
	data = text.encode("utf-8") + b"\n\x00"
	with open(os.path.join(HERE, NAME + ".amxd"), "wb") as f:
		f.write(b"ampf" + struct.pack("<I", 4) + b"aaaa")
		f.write(b"meta" + struct.pack("<I", 4) + b"\x00\x00\x00\x00")
		f.write(b"ptch" + struct.pack("<I", len(data)) + data)

if __name__ == "__main__":
	build()
