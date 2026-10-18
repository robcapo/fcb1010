"""Build Klone.maxpat and Klone.amxd from klone.genexpr.

	python3 build.py

The device is a plugin~ -> gen~ -> plugout~ chain with three live.dial
knobs (Gain, Treble, Output) feeding the gen~ Params. The gen~ code is
embedded in the patch, so the .amxd has no external dependencies.
"""

import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
APPVERSION = {"major": 8, "minor": 6, "revision": 5, "architecture": "x64", "modernui": 1}

KNOBS = [
	# (long name, gen~ Param, presentation x)
	("Gain", "p_gain", 8),
	("Treble", "p_treble", 62),
	("Output", "p_output", 116),
]


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


def gen_patcher(code):
	boxes = [
		box("obj-1", "newobj", [20, 20, 30, 22], 0, 1, [""], text="in 1"),
		box("obj-2", "newobj", [400, 20, 30, 22], 0, 1, [""], text="in 2"),
		box("obj-3", "codebox", [20, 60, 600, 700], 2, 2, ["", ""],
			code=code, fontface=0, fontname="<Monospaced>", fontsize=12),
		box("obj-4", "newobj", [20, 780, 37, 22], 1, 0, text="out 1"),
		box("obj-5", "newobj", [400, 780, 37, 22], 1, 0, text="out 2"),
	]
	lines = [
		line("obj-1", 0, "obj-3", 0),
		line("obj-2", 0, "obj-3", 1),
		line("obj-3", 0, "obj-4", 0),
		line("obj-3", 1, "obj-5", 0),
	]
	return {
		"fileversion": 1,
		"appversion": APPVERSION,
		"classnamespace": "dsp.gen",
		"rect": [100, 100, 660, 840],
		"boxes": boxes,
		"lines": lines,
	}


def device_patcher(code):
	boxes = [
		box("obj-plugin", "newobj", [20, 20, 53, 22], 1, 2, ["signal", "signal"], text="plugin~"),
		box("obj-gen", "newobj", [20, 200, 110, 22], 2, 2, ["signal", "signal"],
			text="gen~ @title klone", patcher=gen_patcher(code)),
		box("obj-plugout", "newobj", [20, 260, 60, 22], 2, 0, text="plugout~"),
		box("obj-title", "comment", [300, 20, 120, 20], 1, 0,
			text="KLONE", presentation=1, presentation_rect=[8, 4, 150, 20],
			fontsize=13, fontface=1),
	]
	lines = [
		line("obj-plugin", 0, "obj-gen", 0),
		line("obj-plugin", 1, "obj-gen", 1),
		line("obj-gen", 0, "obj-plugout", 0),
		line("obj-gen", 1, "obj-plugout", 1),
	]
	parameters = {}
	for i, (name, param, px) in enumerate(KNOBS):
		dial = f"obj-dial-{i}"
		prepend = f"obj-prepend-{i}"
		x = 160 + i * 110
		boxes.append(box(dial, "live.dial", [x, 60, 44, 48], 1, 2, ["", "float"],
			parameter_enable=1, presentation=1, presentation_rect=[px, 40, 44, 48],
			varname=name,
			saved_attribute_attributes={"valueof": {
				"parameter_longname": name,
				"parameter_shortname": name,
				"parameter_type": 0,
				"parameter_mmin": 0.0,
				"parameter_mmax": 10.0,
				"parameter_initial": [5.0],
				"parameter_initial_enable": 1,
				"parameter_unitstyle": 1,
			}}))
		boxes.append(box(prepend, "newobj", [x, 130, 100, 22], 1, 1, [""],
			text=f"prepend {param}"))
		lines.append(line(dial, 0, prepend, 0))
		lines.append(line(prepend, 0, "obj-gen", 0))
		parameters[dial] = [name, name, 0]
	parameters["inherited_shortname"] = 1
	return {
		"patcher": {
			"fileversion": 1,
			"appversion": APPVERSION,
			"classnamespace": "box",
			"rect": [100, 100, 640, 480],
			"openinpresentation": 1,
			"default_fontsize": 10.0,
			"default_fontname": "Arial Bold",
			"gridsize": [8.0, 8.0],
			"devicewidth": 170.0,
			"description": "Klon Centaur style overdrive",
			"boxes": boxes,
			"lines": lines,
			"parameters": parameters,
			"dependency_cache": [],
			"autosave": 0,
		}
	}


def chunk(tag, payload):
	return tag + struct.pack("<I", len(payload)) + payload


def amxd(patch_json):
	# Live's device container: an "ampf" header naming the device kind
	# ("aaaa" is an audio effect), a 4-byte meta chunk, then the patcher
	# JSON in a "ptch" chunk.
	body = patch_json.encode("utf-8") + b"\n\x00"
	return chunk(b"ampf", b"aaaa") + chunk(b"meta", b"\x00\x00\x00\x00") + chunk(b"ptch", body)


def main():
	with open(os.path.join(HERE, "klone.genexpr")) as f:
		code = f.read()
	patch_json = json.dumps(device_patcher(code), indent="\t")
	with open(os.path.join(HERE, "Klone.maxpat"), "w") as f:
		f.write(patch_json + "\n")
	with open(os.path.join(HERE, "Klone.amxd"), "wb") as f:
		f.write(amxd(patch_json))


if __name__ == "__main__":
	main()
