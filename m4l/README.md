# FCB Looper

A Max for Live audio effect with three Boomerang style loops. It keeps its
own sample accurate clock, so loops don't use clips or the song's transport.
The board's BR mode drives it.

## Setup

1. Drag `FCB Looper.amxd` onto the `lp1` track. BR mode creates that track
   next to your `#fcb` track, set to monitor input from it.
2. If Live won't load the `.amxd`, build it by hand instead:
   1. Make a new Max Audio Effect.
   2. In Max, use File > Open to open `FCB Looper.maxpat`, then select all and copy.
   3. Paste into the new device's patcher, and save the device as `FCB Looper.amxd`.

The device only outputs the loops. The `#fcb` track still plays your dry signal.

## Changing it

The audio engine is `fcb_looper.genexpr`, which runs in the device's `gen~`.
After editing it, run `python3 m4l/build_device.py` to rebuild the
`.maxpat` and `.amxd`.

The control script talks to the device through its parameters:

- `target1`-`target3`: what a loop should do next. 0 is stop, 1 record,
  2 play, 3 overdub, 4 erase and 5 nothing. A loop only reacts when its
  value changes.
- `status1`-`status3`, set by the device: 0 empty, 1 stopped, 2 recording,
  3 playing, 4 overdubbing, 5 waiting to record.
- `sync`: when on, loops follow the song's bars. When off, the first loop
  recorded is the master that the other loops sync to.
- `autostop`: with sync on, finish recording after this many bars (0 is off).

Each loop can be up to 60 seconds long.
