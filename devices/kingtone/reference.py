"""Python mirror of kingtone.genexpr, for checking the DSP without Max.

Run it directly to check that the gen~ code build.py ships matches this
model sample for sample, then print frequency responses, clipping curves
and an aliasing check:

	python3 reference.py

Keep it in step with kingtone.genexpr: every stage here maps one to one
onto a line of the gen~ code.
"""

import math
import os
import re
import sys

import numpy as np

MODES = {"boost": 0, "od": 1, "dist": 2}


class Lp1:
	"""One-pole TPT lowpass."""

	def __init__(self, sr):
		self.sr = sr
		self.z = 0.0

	def __call__(self, x, fc):
		g = math.tan(math.pi * fc / self.sr)
		v = (x - self.z) * g / (1 + g)
		y = v + self.z
		self.z = y + v
		return y


class Adaa:
	"""x / sqrt(1 + x^2) with first-order antiderivative anti-aliasing."""

	def __init__(self):
		self.u1 = 0.0

	def __call__(self, x, vf):
		u = x / vf
		y = (u + self.u1) / (math.sqrt(1 + u * u) + math.sqrt(1 + self.u1 * self.u1))
		self.u1 = u
		return y * vf


def audio_taper(t):
	return (30 ** t - 1) / 29


class Side:
	"""One side of the pedal, for one audio channel, with settled knobs."""

	def __init__(self, sr, mode="od", drive=5, tone=5, volume=5, presence=5):
		self.lp = [Lp1(sr) for _ in range(6)]
		self.od = Adaa()
		self.ds = Adaa()
		self.mode = MODES[mode]
		self.rf = 1000 + 100000 * audio_taper(drive / 10)
		self.fc_pre = 20000 / (1 + self.rf / 36000)
		self.tone_amp = 10 ** ((-14 + 1.7 * tone) / 20)
		self.pres_amp = 10 ** (0.9 * presence / 20)
		self.vol = 6.5 * audio_taper(volume / 10)

	def __call__(self, dry):
		lp = self.lp
		x = dry - lp[0](dry, 16)
		fb = self.rf / 4700 * (x - lp[1](x, 340))
		fb = lp[2](fb, self.fc_pre)
		# All three modes run every sample, as in the gen~ code, so the
		# anti-aliasing states stay in step.
		od = x + self.od(fb, 0.55)
		ds = self.ds(x + fb, 0.5)
		u = (x + fb) / 3.8
		bs = 3.8 * u / math.sqrt(1 + u * u)
		y = (bs, od, ds)[self.mode]
		lo = lp[3](y, 1000)
		y = lo + self.tone_amp * (y - lo)
		lo = lp[4](y, 3200)
		y = (lo + self.pres_amp * (y - lo)) * self.vol
		return y - lp[5](y, 8)


def process(x, sr=48000, a=None, b=None):
	"""Run a mono signal through side a then side b. None means bypassed."""
	sides = [Side(sr, **knobs) for knobs in (a, b) if knobs is not None]
	out = np.empty(len(x))
	for i, s in enumerate(x):
		s = float(s)
		for side in sides:
			s = side(s)
		out[i] = s
	return out


def tone_gain_db(freq, amp, sr=48000, **sides):
	"""Steady-state fundamental gain in dB and output peak for a sine."""
	n = int(sr * 0.25)
	t = np.arange(n) / sr
	y = process(amp * np.sin(2 * np.pi * freq * t), sr=sr, **sides)
	tail = y[n // 2:]
	tt = t[n // 2:]
	c = np.sum(tail * np.cos(2 * np.pi * freq * tt)) * 2 / len(tail)
	s = np.sum(tail * np.sin(2 * np.pi * freq * tt)) * 2 / len(tail)
	return 20 * math.log10(max(math.hypot(c, s), 1e-12) / amp), np.max(np.abs(tail))


class GenCodebox:
	"""Runs the shipped codebox code (build.render of kingtone.genexpr) in Python.

	Handles the subset of GenExpr the device uses: Param and History
	declarations, plain assignments, comparisons and a few math operators.
	Assignments take effect immediately, as in a gen~ codebox.
	"""

	def __init__(self, code, sr=48000, **params):
		code = re.sub(r"//[^\n]*", "", code)
		self.env = {
			"pi": math.pi, "samplerate": sr, "exp": math.exp, "pow": math.pow,
			"tan": math.tan, "sqrt": math.sqrt, "dbtoa": lambda db: 10 ** (db / 20),
		}
		body = []
		for stmt in (t.strip() for t in code.split(";")):
			if not stmt:
				continue
			decl = re.fullmatch(r"(Param|History)\s+(\w+)\(([^,)]*)[^)]*\)", stmt)
			if decl:
				self.env[decl.group(2)] = float(decl.group(3))
			elif re.match(r"(Param|History)\b", stmt):
				raise ValueError(f"unparsed declaration: {stmt}")
			else:
				body.append(stmt)
		for name, value in params.items():
			assert name in self.env, f"unknown param {name}"
			self.env[name] = float(value)
		self.body = compile("\n".join(body), "codebox", "exec")

	def __call__(self, in1, in2):
		env = self.env
		env["in1"], env["in2"] = in1, in2
		exec(self.body, env)
		return env["out1"], env["out2"]


def gen_params(a, b):
	params = {}
	for side, knobs in (("a", a), ("b", b)):
		params[f"{side}_on"] = 0 if knobs is None else 127
		for name, value in (knobs or {}).items():
			params[f"{side}_{name}"] = MODES[value] if name == "mode" else value
	return params


def check_codebox(sr=48000):
	"""Compare the shipped gen~ code against the Python model, sample by sample."""
	sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
	import build
	code = build.load_code()
	rng = np.random.default_rng(1)
	n = sr // 2
	x = 0.3 * np.sin(2 * np.pi * 220 * np.arange(n) / sr) + 0.05 * rng.standard_normal(n)
	cases = [
		({"mode": "od", "drive": 0, "tone": 5, "volume": 5, "presence": 5}, None),
		({"mode": "od", "drive": 10, "tone": 2, "volume": 3, "presence": 0}, None),
		(None, {"mode": "dist", "drive": 7, "tone": 8, "volume": 4, "presence": 10}),
		({"mode": "boost", "drive": 6, "tone": 6, "volume": 6, "presence": 3},
			{"mode": "od", "drive": 4, "tone": 5, "volume": 5, "presence": 5}),
		(None, None),
	]
	worst = 0.0
	for a, b in cases:
		box = GenCodebox(code, sr, **gen_params(a, b))
		got = np.array([box(float(s), float(-s)) for s in x])
		want = process(x, sr=sr, a=a, b=b)
		tail = slice(n // 2, None)
		assert np.all(np.isfinite(got))
		assert np.max(np.abs(got[tail, 1] + got[tail, 0])) < 1e-9, "channels differ"
		assert np.max(np.abs(want[tail])) > 0.05, f"model output is near silent at {a}, {b}"
		err = np.max(np.abs(got[tail, 0] - want[tail])) / np.max(np.abs(want[tail]))
		worst = max(worst, err)
	print(f"Shipped gen~ code matches the Python model to {worst:.1e} (relative)")

	# The On toggles run 0-127 and switch a side on at 64 and up.
	for value, on in ((63, False), (64, True)):
		box = GenCodebox(code, sr, a_on=value, b_on=0, a_drive=10)
		got = np.array([box(float(s), float(s))[0] for s in x])
		changed = np.max(np.abs(got[n // 2:] - x[n // 2:])) > 0.01
		assert changed == on, f"On at {value} should be {'on' if on else 'off'}"
	print("On switches at 64")
	# The knob smoothers start a little off the settled values; 1e-4 allows
	# for what is left of that after a quarter second.
	assert worst < 1e-4


def main():
	check_codebox()

	freqs = [50, 100, 200, 400, 800, 1000, 2000, 4000, 8000]
	header = "        " + " ".join(f"{f:>6}" for f in freqs)

	print("\nSmall-signal response (10 mV), one side in OD, tone/volume/presence 5, dB:")
	print("drive" + header[5:])
	for drive in (0, 2, 5, 8, 10):
		row = [tone_gain_db(f, 0.01, a={"drive": drive})[0] for f in freqs]
		print(f"{drive:>5}   " + " ".join(f"{v:6.1f}" for v in row))

	print("\nTone sweep at drive 0, small signal, dB:")
	print("tone " + header[5:])
	for tone in (0, 5, 10):
		row = [tone_gain_db(f, 0.01, a={"drive": 0, "tone": tone})[0] for f in freqs]
		print(f"{tone:>5}   " + " ".join(f"{v:6.1f}" for v in row))

	print("\nPresence sweep at drive 0, tone 5, small signal, dB:")
	print("pres " + header[5:])
	for pres in (0, 5, 10):
		row = [tone_gain_db(f, 0.01, a={"drive": 0, "presence": pres})[0] for f in freqs]
		print(f"{pres:>5}   " + " ".join(f"{v:6.1f}" for v in row))

	print("\n1 kHz gain (dB) against input level, drive 10, volume 5:")
	levels = [0.01, 0.03, 0.1, 0.3, 1.0]
	print("mode   " + " ".join(f"{a * 1000:>6.0f}mV" for a in levels))
	for mode in ("boost", "od", "dist"):
		row = [tone_gain_db(1000, a, a={"mode": mode, "drive": 10})[0] for a in levels]
		print(f"{mode:<6} " + " ".join(f"{v:8.1f}" for v in row))

	print("\nVolume knob, drive 0, OD (1 kHz, 10 mV), dB:")
	for volume in (0, 2.5, 5, 7.5, 10):
		print(f"  volume {volume:>4}: {tone_gain_db(1000, 0.01, a={'drive': 0, 'volume': volume})[0]:6.1f}")

	# Aliasing: a 5 kHz tone driven hard. Harmonics land on multiples of
	# 5 kHz; anything else above the noise floor is aliasing.
	sr = 48000
	t = np.arange(sr) / sr
	for mode in ("od", "dist"):
		y = process(0.5 * np.sin(2 * np.pi * 5000 * t), sr=sr, a={"mode": mode, "drive": 10})[sr // 2:]
		assert np.all(np.isfinite(y))
		spec = np.abs(np.fft.rfft(y * np.hanning(len(y))))
		spec_db = 20 * np.log10(spec / spec.max() + 1e-12)
		bins = np.fft.rfftfreq(len(y), 1 / sr)
		harmonic = np.zeros_like(bins, dtype=bool)
		for k in range(1, 5):
			harmonic |= np.abs(bins - 5000 * k) < 30
		print(f"Worst alias, 5 kHz at drive 10 in {mode}: {spec_db[~harmonic].max():.1f} dB below the fundamental")


if __name__ == "__main__":
	main()
