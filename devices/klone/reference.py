"""Python mirror of klone.genexpr, for checking the DSP without Max.

Run it directly to check that the gen~ code build.py ships matches this
model sample for sample, then print frequency responses, clipping levels
and an aliasing check:

	python3 reference.py

Keep it in step with klone.genexpr: every stage here maps one to one onto
a line of the gen~ code.
"""

import math
import os
import re
import sys

import numpy as np


class Lp1:
	"""One-pole TPT lowpass (lp1 in the gen code)."""

	def __init__(self, sr):
		self.sr = sr
		self.z = 0.0

	def __call__(self, x, fc):
		g = math.tan(math.pi * fc / self.sr)
		v = (x - self.z) * g / (1 + g)
		y = v + self.z
		self.z = y + v
		return y


class Diodes:
	"""Germanium diode pair with first-order ADAA (diodes in the gen code)."""

	def __init__(self):
		self.u1 = 0.0

	def __call__(self, x, vf):
		u = x / vf
		y = (u + self.u1) / (math.sqrt(1 + u * u) + math.sqrt(1 + self.u1 * self.u1))
		self.u1 = u
		return y * vf


def audio_taper(t):
	return (30 ** t - 1) / 29


class Channel:
	def __init__(self, sr):
		self.lp = [Lp1(sr) for _ in range(6)]
		self.diodes = Diodes()

	def __call__(self, x, gain_t, treble_db, out_amp):
		lp = self.lp
		xin = x - lp[0](x, 16)
		taper = audio_taper(gain_t)
		hp = xin - lp[1](xin, 400)
		pre = xin + 120 * taper * hp
		pre = lp[2](pre, 12000 / (1 + 3 * taper))
		dirty = self.diodes(pre, 0.35)
		clean = xin * (1 - 0.9 * gain_t)
		summed = lp[3](clean + 2 * dirty, 6500)
		lo = lp[4](summed, 1200)
		toned = lo + 10 ** (treble_db / 20) * (summed - lo)
		y = toned * out_amp
		return y - lp[5](y, 8)


def process(x, gain=5, treble=5, output=5, sr=48000):
	"""Run a mono signal through one channel with settled knob values."""
	ch = Channel(sr)
	gain_t = gain / 10
	treble_db = (treble - 5) * 2.4
	out_amp = 2.2 * audio_taper(output / 10)
	return np.array([ch(float(s), gain_t, treble_db, out_amp) for s in x])


def tone_gain_db(freq, amp, sr=48000, **knobs):
	"""Steady-state gain in dB for a sine at freq with peak amp."""
	n = int(sr * 0.25)
	t = np.arange(n) / sr
	y = process(amp * np.sin(2 * np.pi * freq * t), sr=sr, **knobs)
	tail = y[n // 2:]
	ref = amp * np.sin(2 * np.pi * freq * t[n // 2:])
	# Fundamental amplitude by projection onto sin/cos.
	c = np.sum(tail * np.cos(2 * np.pi * freq * t[n // 2:])) * 2 / len(tail)
	s = np.sum(tail * np.sin(2 * np.pi * freq * t[n // 2:])) * 2 / len(tail)
	return 20 * math.log10(max(math.hypot(c, s), 1e-12) / amp), np.max(np.abs(tail)), ref


class GenCodebox:
	"""Runs the shipped codebox code (build.render of klone.genexpr) in Python.

	Handles the subset of GenExpr the device uses: Param and History
	declarations, plain assignments, and a few math operators. Assignments
	take effect immediately, as in a gen~ codebox.
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
			else:
				body.append(stmt)
		for name, value in params.items():
			self.env["p_" + name] = float(value)
		self.body = compile("\n".join(body), "codebox", "exec")

	def __call__(self, in1, in2):
		env = self.env
		env["in1"], env["in2"] = in1, in2
		exec(self.body, env)
		return env["out1"], env["out2"]


def check_codebox(sr=48000):
	"""Compare the shipped gen~ code against the Python model, sample by sample."""
	sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
	import build
	code = build.load_code()
	rng = np.random.default_rng(1)
	n = sr // 2
	x = 0.3 * np.sin(2 * np.pi * 220 * np.arange(n) / sr) + 0.05 * rng.standard_normal(n)
	worst = 0.0
	for knobs in ({"gain": 0, "treble": 5, "output": 5}, {"gain": 7, "treble": 2, "output": 8}, {"gain": 10, "treble": 10, "output": 3}):
		box = GenCodebox(code, sr, **knobs)
		got = np.array([box(float(s), float(-s)) for s in x])
		want = process(x, sr=sr, **knobs)
		tail = slice(n // 2, None)
		assert np.all(np.isfinite(got))
		assert np.max(np.abs(got[tail, 1] + got[tail, 0])) < 1e-9, "channels differ"
		err = np.max(np.abs(got[tail, 0] - want[tail])) / np.max(np.abs(want[tail]))
		assert np.max(np.abs(want[tail])) > 0.05, f"model output is near silent at {knobs}"
		worst = max(worst, err)
	print(f"Shipped gen~ code matches the Python model to {worst:.1e} (relative)")
	# The knob smoothers start a little off the settled values; 1e-4 allows
	# for what is left of that after a quarter second.
	assert worst < 1e-4


def main():
	check_codebox()

	freqs = [50, 100, 200, 400, 800, 1000, 1500, 2000, 4000, 8000]
	print("Small-signal response (10 mV), output 5, treble 5, dB:")
	print("gain   " + " ".join(f"{f:>6}" for f in freqs))
	for gain in (0, 2, 5, 8, 10):
		row = [tone_gain_db(f, 0.01, gain=gain)[0] for f in freqs]
		print(f"{gain:>4}   " + " ".join(f"{v:6.1f}" for v in row))

	print("\nTreble sweep at gain 0, small signal, dB:")
	for treble in (0, 5, 10):
		row = [tone_gain_db(f, 0.01, gain=0, treble=treble)[0] for f in freqs]
		print(f"{treble:>4}   " + " ".join(f"{v:6.1f}" for v in row))

	print("\nPeak output for a 300 mV 1 kHz input (output 5):")
	for gain in (0, 2, 5, 8, 10):
		_, peak, _ = tone_gain_db(1000, 0.3, gain=gain)
		print(f"  gain {gain:>2}: {peak:.3f}")

	print("\nOutput knob, clean boost at gain 0 (1 kHz, 10 mV), dB:")
	for output in (0, 2.5, 5, 7.5, 10):
		print(f"  output {output:>4}: {tone_gain_db(1000, 0.01, gain=0, output=output)[0]:6.1f}")

	# Aliasing: a 5 kHz tone driven hard. Harmonics land on multiples of
	# 5 kHz; anything else above the noise floor is aliasing.
	sr = 48000
	n = sr
	t = np.arange(n) / sr
	y = process(0.5 * np.sin(2 * np.pi * 5000 * t), gain=10, sr=sr)[n // 2:]
	spec = np.abs(np.fft.rfft(y * np.hanning(len(y))))
	spec_db = 20 * np.log10(spec / spec.max() + 1e-12)
	bins = np.fft.rfftfreq(len(y), 1 / sr)
	harmonic = np.zeros_like(bins, dtype=bool)
	for k in range(1, 5):
		harmonic |= np.abs(bins - 5000 * k) < 30
	print(f"\nWorst alias, 5 kHz at gain 10: {spec_db[~harmonic].max():.1f} dB below the fundamental")

	assert np.all(np.isfinite(y))


if __name__ == "__main__":
	main()
