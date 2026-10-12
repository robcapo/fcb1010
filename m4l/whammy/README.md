# FCB Whammy

A Max for Live audio effect modeled on the DigiTech Whammy. A treadle
parameter sweeps the pitch between two intervals, and a mode menu picks the
preset, like the knob on the pedal.

## Presets

| Mode | Heel | Toe | Signal |
|---|---|---|---|
| 2 Oct Up | 0 | +24 | shifted only |
| Oct Up | 0 | +12 | shifted only |
| 5th Up | 0 | +7 | shifted only |
| 4th Up | 0 | +5 | shifted only |
| 2nd Down | 0 | -2 | shifted only |
| 4th Down | 0 | -5 | shifted only |
| 5th Down | 0 | -7 | shifted only |
| Oct Down | 0 | -12 | shifted only |
| 2 Oct Down | 0 | -24 | shifted only |
| Dive Bomb | 0 | -36 | shifted only |
| Deep Detune | ±25 cents | | dry + two detuned voices |
| Shallow Detune | ±10 cents | | dry + two detuned voices |
| Oct Dn/Oct Up | -12 | +12 | dry + shifted |
| 5th Dn/4th Dn | -7 | -5 | dry + shifted |
| 4th Dn/3rd Dn | -5 | -4 | dry + shifted |
| 5th Up/7th Up | +7 | +10 | dry + shifted |
| 5th Up/6th Up | +7 | +9 | dry + shifted |
| 4th Up/5th Up | +5 | +7 | dry + shifted |
| 3rd Up/4th Up | +4 | +5 | dry + shifted |
| b3rd Up/3rd Up | +3 | +4 | dry + shifted |
| 2nd Up/3rd Up | +2 | +4 | dry + shifted |

Intervals are in semitones. The treadle does nothing in the detune presets.

## Setup

1. Drag `FCB Whammy.amxd` onto your guitar track.
2. If Live won't load the `.amxd`, build it by hand instead:
   1. Make a new Max Audio Effect.
   2. In Max, use File > Open to open `FCB Whammy.maxpat`, then select all and copy.
   3. Paste into the new device's patcher, and save the device as `FCB Whammy.amxd`.

## Controlling it from the FCB1010

The device has three parameters: `Mode`, `Treadle` (0 heel down to 127 toe
down) and `Active`.

In the board's FX (racks) mode, put the device in one of the track's racks
and map its parameters to macros, then name the macros so the board picks
them up. For example:

- `Whammy #s5hel` puts `Treadle` on the left expression pedal while stomp 5
  is held. Use `#s5per` to assign it with a press, on the right pedal.
- `Whammy On #s4pt` toggles `Active` with stomp 4.

To switch presets from the board, put a Whammy set to each preset you
want in its own rack and pick them with the top row.

Outside FX mode you can also MIDI map `Treadle` to an expression pedal in
Live like any other parameter.

## Changing it

The audio engine is `fcb_whammy.genexpr`, which runs in the device's `gen~`.
After editing it, run `python3 m4l/whammy/build_device.py` to rebuild the
`.maxpat` and `.amxd`. The preset table lives in the genexpr, and the names
in the mode menu live in `MODES` in the build script, in the same order.

The shifter mixes left and right and treats them as one mono voice, which
suits a guitar. It's a two grain shifter that lines each new grain up with
the one that's playing, so it adds latency: up to about 20ms, plus up to
30ms more while shifting up. Whammy presets fade
to the untouched input when the treadle is at the heel.
