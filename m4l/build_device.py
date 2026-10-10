"""
Builds the FCB Looper Max for Live device from fcb_looper.genexpr.

	python3 m4l/build_device.py

Writes "FCB Looper.maxpat" (the device's patcher) and "FCB Looper.amxd"
(the same patcher, packaged as a Max for Live audio effect) next to this
script.
"""
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "FCB Looper"
LOOP_MS = 60000 # longest loop, per loop

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

def param(longname, kind, mmax = None, enum = None):
	attrs = {
		"parameter_longname": longname,
		"parameter_shortname": longname,
		"parameter_type": kind,
	}
	if mmax is not None:
		attrs["parameter_mmin"] = 0
		attrs["parameter_mmax"] = mmax
	if enum is not None:
		attrs["parameter_enum"] = enum
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
	for i in range(3):
		gbox("in-{}".format(i + 1), "newobj", [20 + 120 * i, 20, 40, 22], "in {}".format(i + 1), outlets = 1)
		lines.append({"patchline": {"source": ["in-{}".format(i + 1), 0], "destination": ["code", i]}})
	gbox("code", "codebox", [20, 60, 600, 500], inlets = 3, outlets = 5, code = code, fontface = 0, fontname = "<Monospaced>", fontsize = 12)
	for i in range(5):
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
	with open(os.path.join(HERE, "fcb_looper.genexpr")) as f:
		code = f.read()

	plugin = box("newobj", [20, 20, 60, 22], "plugin~", inlets = 2, outlets = 2, outlettype = ["signal", "signal"])
	bar = box("newobj", [200, 20, 140, 22], "phasor~ 1n @lock 1", inlets = 2, outlets = 1, outlettype = ["signal"])
	gen = box("newobj", [20, 200, 300, 22], "gen~", inlets = 3, outlets = 5,
		outlettype = ["signal"] * 5, patcher = gen_patcher(code))
	plugout = box("newobj", [20, 260, 60, 22], "plugout~", inlets = 2)
	line(plugin, 0, gen, 0)
	line(plugin, 1, gen, 1)
	line(bar, 0, gen, 2)
	line(gen, 0, plugout, 0)
	line(gen, 1, plugout, 1)

	# Commands from the control script, one target per loop
	for i in range(3):
		x = 380 + 110 * i
		name = "target{}".format(i + 1)
		num = box("live.numbox", [x, 20, 44, 15], inlets = 1, outlets = 2, outlettype = ["", "float"],
			presentation = 1, presentation_rect = [10 + 50 * i, 10, 44, 15], **param(name, 1, mmax = 5))
		msg = box("newobj", [x, 60, 90, 22], "prepend tgt{}".format(i + 1), outlets = 1)
		line(num, 0, msg, 0)
		line(msg, 0, gen, 0)

	sync = box("live.toggle", [710, 20, 15, 15], inlets = 1, outlets = 1,
		presentation = 1, presentation_rect = [10, 40, 15, 15], **param("sync", 2, enum = ["off", "on"]))
	sync_msg = box("newobj", [710, 60, 100, 22], "prepend sync_on", outlets = 1)
	line(sync, 0, sync_msg, 0)
	line(sync_msg, 0, gen, 0)

	autostop = box("live.numbox", [830, 20, 44, 15], inlets = 1, outlets = 2, outlettype = ["", "float"],
		presentation = 1, presentation_rect = [60, 40, 44, 15], **param("autostop", 1, mmax = 8))
	autostop_msg = box("newobj", [830, 60, 130, 22], "prepend autostop_bars", outlets = 1)
	line(autostop, 0, autostop_msg, 0)
	line(autostop_msg, 0, gen, 0)

	# Status of each loop, for the control script and LEDs
	for i in range(3):
		x = 20 + 110 * i
		snap = box("newobj", [x, 320, 80, 22], "snapshot~ 10", inlets = 2, outlets = 1, outlettype = ["float"])
		change = box("newobj", [x, 360, 50, 22], "change", inlets = 1, outlets = 3, outlettype = ["", "int", "int"])
		num = box("live.numbox", [x, 400, 44, 15], inlets = 1, outlets = 2, outlettype = ["", "float"],
			presentation = 1, presentation_rect = [10 + 50 * i, 70, 44, 15], **param("status{}".format(i + 1), 1, mmax = 5))
		line(gen, 2 + i, snap, 0)
		line(snap, 0, change, 0)
		line(change, 0, num, 0)

	for i in range(3):
		box("newobj", [380 + 160 * i, 320, 150, 22], "buffer~ fcbloop{} {} 2".format(i + 1, LOOP_MS),
			inlets = 1, outlets = 2, outlettype = ["float", "bang"])

	patcher = {
		"patcher": {
			"fileversion": 1,
			"appversion": {"major": 8, "minor": 5, "revision": 0, "architecture": "x64", "modernui": 1},
			"classnamespace": "box",
			"rect": [100, 100, 1000, 500],
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
