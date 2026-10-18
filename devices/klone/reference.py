"""Python mirror of klone.genexpr, for checking the DSP without Max.

Run it directly to print frequency responses, clipping levels and an
aliasing check:

	python3 reference.py

Keep it in step with klone.genexpr: every stage here maps one to one onto
a line of the gen~ code.
"""

import math

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


def main():
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
