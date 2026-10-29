"""Build Kingtone.maxpat and Kingtone.amxd from kingtone.genexpr.

	python3 build.py

The device is a plugin~ -> gen~ -> plugout~ chain. Each of the pedal's two
sides gets an on/off toggle, a Boost/OD/Dist mode tab and Volume, Drive,
Tone and Presence dials, all feeding the gen~ Params. The gen~ code is
embedded in the patch, so the .amxd has no external dependencies.
"""

import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
APPVERSION = {"major": 8, "minor": 6, "revision": 5, "architecture": "x64", "modernui": 1}

SIDES = ["a", "b"]

# Presentation layout: one column per side, side a (Ch 1) on the left.
COLUMN_X = [8, 164]
COLUMN_LABEL = ["CH 1", "CH 2"]
# (long name suffix, gen~ Param suffix, presentation offset x, y)
DIALS = [
	("Volume", "volume", 0, 44),
	("Drive", "drive", 48, 44),
	("Tone", "tone", 96, 44),
	("Presence", "presence", 0, 100),
]
MODES = ["Boost", "OD", "Dist"]


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
			text="gen~ @title kingtone", patcher=gen_patcher(code)),
		box("obj-plugout", "newobj", [20, 260, 60, 22], 2, 0, text="plugout~"),
		box("obj-title", "comment", [300, 20, 120, 20], 1, 0,
			text="KINGTONE", presentation=1, presentation_rect=[64, 120, 96, 20],
			fontsize=11, fontface=1),
	]
	lines = [
		line("obj-plugin", 0, "obj-gen", 0),
		line("obj-plugin", 1, "obj-gen", 1),
		line("obj-gen", 0, "obj-plugout", 0),
		line("obj-gen", 1, "obj-plugout", 1),
	]
	parameters = {}
	n = 0

	def control(maxclass, name, param, rect, size, numoutlets, outlettype, valueof, via=None, **attrs):
		nonlocal n
		# Live finds a parameter's object by its scripting name, so keep it
		# to one plain word: "ch1_drive", not the "CH 1 Drive" long name.
		varname = name.lower().replace("ch ", "ch").replace(" ", "_")
		obj = f"obj-ctl-{n}"
		prepend = f"obj-prepend-{n}"
		x = 160 + (n % 6) * 110
		y = 60 + (n // 6) * 120
		n += 1
		boxes.append(box(obj, maxclass, [x, y] + size, 1, numoutlets, outlettype,
			parameter_enable=1, presentation=1, presentation_rect=rect + size,
			varname=varname, saved_attribute_attributes={"valueof": valueof}, **attrs))
		boxes.append(box(prepend, "newobj", [x, y + 70, 100, 22], 1, 1, [""],
			text=f"prepend {param}"))
		if via is None:
			lines.append(line(obj, 0, prepend, 0))
		else:
			# An object between the control and gen~, such as ">= 64".
			boxes.append(box(f"obj-via-{n - 1}", "newobj", [x, y + 35, 60, 22], 2, 1, ["int"], text=via))
			lines.append(line(obj, 0, f"obj-via-{n - 1}", 0))
			lines.append(line(f"obj-via-{n - 1}", 0, prepend, 0))
		lines.append(line(prepend, 0, "obj-gen", 0))
		parameters[obj] = [name, valueof["parameter_shortname"], 0]
		return obj

	for i, side in enumerate(SIDES):
		cx = COLUMN_X[i]
		label = COLUMN_LABEL[i]
		boxes.append(box(f"obj-label-{i}", "comment", [300 + i * 60, 20, 50, 20], 1, 0,
			text=label, presentation=1, presentation_rect=[cx + 20, 2, 50, 18],
			fontsize=11, fontface=1))
		# The footswitch is a 0-127 parameter, so a rack macro can map onto it
		# with a usable Min/Max: 64 and up is on. The toggle beside it is only
		# the button you click; it sends 0 or 127 and shows the state.
		on = control("live.numbox", f"{label} On", f"{side}_on", [cx + 104, 3], [36, 15], 2, ["", "float"], {
			"parameter_longname": f"{label} On",
			"parameter_shortname": "On",
			"parameter_type": 1,
			"parameter_mmin": 0,
			"parameter_mmax": 127,
			"parameter_initial": [127 if i == 0 else 0],
			"parameter_initial_enable": 1,
			"parameter_modmode": 0,
		}, via=">= 64")
		via = "obj-via-" + on.split("-")[-1]
		button = f"obj-onbutton-{i}"
		boxes.append(box(button, "live.toggle", [40 + i * 60, 400, 16, 16], 1, 1, [""],
			parameter_enable=0, presentation=1, presentation_rect=[cx, 4, 16, 16]))
		boxes.append(box(f"obj-onscale-{i}", "newobj", [40 + i * 60, 430, 40, 22], 2, 1, ["int"], text="* 127"))
		boxes.append(box(f"obj-onset-{i}", "newobj", [40 + i * 60, 370, 70, 22], 1, 1, [""], text="prepend set"))
		lines.append(line(button, 0, f"obj-onscale-{i}", 0))
		lines.append(line(f"obj-onscale-{i}", 0, on, 0))
		lines.append(line(via, 0, f"obj-onset-{i}", 0))
		lines.append(line(f"obj-onset-{i}", 0, button, 0))
		control("live.tab", f"{label} Mode", f"{side}_mode", [cx, 22], [140, 18], 3, ["", "", "float"], {
			"parameter_longname": f"{label} Mode",
			"parameter_shortname": "Mode",
			"parameter_type": 2,
			"parameter_enum": MODES,
			"parameter_mmax": 2,
			"parameter_initial": [1],
			"parameter_initial_enable": 1,
			"parameter_unitstyle": 9,
		}, num_lines_patching=1, num_lines_presentation=1)
		for name, suffix, dx, dy in DIALS:
			control("live.dial", f"{label} {name}", f"{side}_{suffix}", [cx + dx, dy], [44, 48], 2, ["", "float"], {
				"parameter_longname": f"{label} {name}",
				"parameter_shortname": name,
				"parameter_type": 0,
				"parameter_mmin": 0.0,
				"parameter_mmax": 10.0,
				"parameter_initial": [5.0],
				"parameter_initial_enable": 1,
				"parameter_unitstyle": 1,
			})
	# One bank per side, in the order Live and Push show them.
	longnames = [v[0] for k, v in parameters.items()]
	parameters["parameterbanks"] = {
		str(i): {"index": i, "name": label, "parameters": ([n for n in longnames if n.startswith(label)] + ["-"] * 8)[:8]}
		for i, label in enumerate(COLUMN_LABEL)
	}
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
			"devicewidth": 312.0,
			"description": "King of Tone style dual overdrive",
			"boxes": boxes,
			"lines": lines,
			"parameters": parameters,
			"dependency_cache": [],
			"latency": 0,
			"is_mpe": 0,
			"minimum_live_version": "",
			"minimum_max_version": "",
			"platform_compatibility": 0,
			"autosave": 0,
		}
	}


def chunk(tag, payload):
	return tag + struct.pack("<I", len(payload)) + payload


def amxd(patch_json):
	# Live's device container: an "ampf" header naming the device kind
	# ("aaaa" is an audio effect), a 4-byte meta chunk, then the patcher
	# JSON in a "ptch" chunk. Devices saved by Max carry 1 in the meta
	# chunk (7 when frozen), so this does too.
	body = patch_json.encode("utf-8") + b"\x00"
	return chunk(b"ampf", b"aaaa") + chunk(b"meta", struct.pack("<I", 1)) + chunk(b"ptch", body)


def expand_sides(template, sides=SIDES):
	"""Copy each SIDE block once per side, replacing $ with the side letter."""
	parts = template.split("// SIDE BEGIN\n")
	out = [parts[0]]
	for part in parts[1:]:
		block, rest = part.split("// SIDE END\n")
		for side in sides:
			out.append(block.replace("$", side))
		out.append(rest)
	return "".join(out)


def render(template, channels=2):
	"""Expand kingtone.genexpr's $ (side) and @ (channel) templates."""
	template = expand_sides(template)
	head, rest = template.split("// CHANNEL BEGIN\n")
	block, tail = rest.split("// CHANNEL END\n")
	out = []
	for text in head.splitlines(keepends=True):
		if "@" in text and not text.lstrip().startswith("//"):
			out.extend(text.replace("@", str(c)) for c in range(1, channels + 1))
		else:
			out.append(text)
	for c in range(1, channels + 1):
		out.append(f"// Channel {c}\n")
		out.append(block.replace("@", str(c)))
		out.append("\n")
	out.append(tail)
	return "".join(out).rstrip("\n") + "\n"


def load_code():
	with open(os.path.join(HERE, "kingtone.genexpr")) as f:
		return render(f.read())


def main():
	code = load_code()
	patch_json = json.dumps(device_patcher(code), indent="\t")
	with open(os.path.join(HERE, "Kingtone.maxpat"), "w") as f:
		f.write(patch_json + "\n")
	with open(os.path.join(HERE, "Kingtone.amxd"), "wb") as f:
		f.write(amxd(patch_json))


if __name__ == "__main__":
	main()
