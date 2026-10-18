# Klone

A Max for Live audio effect modelled on the Klon Centaur overdrive. Drop
`Klone.amxd` on a track in Live 12. It has the pedal's three knobs, each
running 0 to 10 like the pedal's markings:

| Knob   | What it does |
|--------|--------------|
| Gain   | Dual-gang control: turns up the clipping stage while turning down the clean path that is blended back in. |
| Treble | Active high shelf around 1.2 kHz, ±12 dB, flat at noon. |
| Output | Audio-taper volume. Noon is about unity at Gain 0; full up is about +16 dB of clean boost. |

## What it models

The Centaur's sound comes from a few circuit traits, each of which has a
stage in `klone.genexpr`:

1. **Clean and dirty paths summed.** The input buffer feeds both a
   clipping stage and a clean path. The dual-gang Gain pot raises one while
   lowering the other, but the clean path never goes fully silent, which
   is why the pedal stays "transparent" and keeps some of the guitar's low end even
   at high gain.
2. **Mid-focused clipping stage.** The op-amp gain is applied above about
   400 Hz, and its feedback capacitor pulls the top end in as gain rises
   (12 kHz at Gain 0 down to 3 kHz at Gain 10). That gives the dirty path
   its mid hump, centred near 1 kHz. Mid-band gain runs from 0 dB to about
   +42 dB.
3. **Germanium diodes to ground.** A pair of 1N34A diodes after the op-amp
   clip softly at about 0.3 V. They are modelled with a smooth
   `x / sqrt(1 + x²)` curve and first-order antiderivative anti-aliasing,
   which cuts aliasing by about 15 dB against plain clipping.
4. **18 V headroom.** The real pedal runs its op-amps from a charge pump,
   so nothing but the diodes clips. The model has no other clipping stage.
5. **Summing amp, Treble and Output.** The summing amp rolls off fizz
   above 6.5 kHz, then the treble shelf and the output volume follow.

Levels are treated as volts with 0 dBFS = 1 V peak, so a guitar recorded
around -12 dBFS lands in the range the real diodes see.

This is a behavioural model built from the published circuit analysis,
not a component-level simulation. The cutoffs and gains are tuned by ear
and by the measurements in `reference.py`.

## Files

- `klone.genexpr`: the DSP, embedded in the device's `gen~`.
- `reference.py`: a Python mirror of the DSP. `python3 reference.py`
  prints the frequency response at several Gain and Treble settings,
  clipping levels, the Output law and an aliasing check.
- `build.py`: regenerates `Klone.maxpat` and `Klone.amxd` from
  `klone.genexpr`. Run it after changing the DSP.
- `Klone.amxd`: the device. `Klone.maxpat` is the same patcher as plain
  JSON, for diffs, or to paste into a new Max Audio Effect if the `.amxd`
  ever fails to load.
