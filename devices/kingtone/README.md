# Kingtone

A Max for Live audio effect modelled on the Analogman King of Tone, a dual
overdrive built on the Marshall Bluesbreaker circuit. Drop `Kingtone.amxd`
on a track in Live 12.

Like the pedal, it has two sides in series: CH 1 feeds CH 2. Each side has:

| Control  | What it does |
|----------|--------------|
| On       | The side's footswitch. Behind the button is a hidden 0 to 127 parameter that turns the side on at 64 and up, so rack macros map onto it with a full 0 to 127 range. True bypass, with a short crossfade so it doesn't click. |
| Mode     | The pedal's internal DIP switch: **Boost** (no diodes), **OD** (diodes in the op-amp feedback loop, the stock setting) or **Dist** (diodes to ground). |
| Volume   | Audio-taper output level. Noon is about unity with Drive at 0; full up is about +16 dB. |
| Drive    | The 100 k audio-taper gain pot in the op-amp feedback: +1.7 dB to +25 dB in the mids. |
| Tone     | Treble shelf around 1 kHz: about -7 dB at 8 kHz fully down, flat at noon, +8 dB fully up. |
| Presence | The pedal's internal trimmer: extra top end above about 3 kHz. Noon is the reference; fully down is about -4 dB and fully up +4 dB at 8 kHz. |

CH 1 starts on in OD; CH 2 starts off.

## What it models

Each side is one non-inverting op-amp clipping stage followed by tone,
presence and volume. The stages map onto `kingtone.genexpr`:

1. **Non-inverting drive stage.** Gain is `1 + Rf / Rg`, with Rf the Drive
   pot plus 1 k and Rg 4.7 k in series with a cap, so the gain only applies
   above about 340 Hz. Below that the stage is unity gain: the bass goes
   through clean, and the mids get pushed. A cap across the feedback leg
   rolls the top end off as Drive goes up (about 19 kHz at minimum to
   5 kHz at maximum).
2. **Clipping, by mode.**
   - *OD:* silicon diodes sit across the feedback leg. They cap the
     voltage across it at about 0.55 V, but a non-inverting stage always
     outputs its input plus that voltage, so the dry signal rides on top of
     the clipped part. That is why the pedal stays touch-sensitive and
     "amp-like" even with Drive up.
   - *Dist:* the diodes move to ground after the stage, so the whole
     signal, dry part included, is clipped at about 0.5 V. More
     compression and more gain, as on the pedal.
   - *Boost:* no diodes; only the 9 V op-amp rails limit the swing.

   The diode curve is `x / sqrt(1 + x²)` with first-order antiderivative
   anti-aliasing.
3. **Tone, Presence and Volume**, then the output coupling cap.

Levels are treated as volts with 0 dBFS = 1 V peak, so a guitar recorded
around -12 dBFS lands in the range the real diodes see.

This is a behavioural model of the published King of Tone and Bluesbreaker
topology, not a component-level simulation: the circuit-analysis sites
were unreachable while building it, so the corner frequencies and gains
are set from that topology and checked with `reference.py`.

## Aliasing

The device runs at the session's sample rate. Anti-aliasing cuts aliasing
by about 4 to 5 dB against plain clipping. At full Drive, a 100 mV note at
1.5 kHz aliases 54 to 60 dB below the note, but very loud high notes do
worse (a 0.5 V 5 kHz sine at full Drive gets to about 22 dB below). At
typical guitar levels this is well under the distortion itself.

## Files

- `kingtone.genexpr`: the DSP, written once as a template for one side of
  one channel. `build.py` expands it for sides a and b and for left and
  right, and embeds it in the device's `gen~`.
- `reference.py`: a Python mirror of the DSP. `python3 reference.py`
  first runs the expanded gen~ code itself in Python and checks it
  matches the model sample for sample, then prints frequency responses,
  the clipping curve of each mode, the Volume law and an aliasing check.
- `build.py`: regenerates `Kingtone.maxpat` and `Kingtone.amxd` from
  `kingtone.genexpr`. Run it after changing the DSP.
- `Kingtone.amxd`: the device. `Kingtone.maxpat` is the same patcher as
  plain JSON, for diffs, or to paste into a new Max Audio Effect if the
  `.amxd` ever fails to load.
