# Tests

```
pip install pytest
python -m pytest
```

These run without Ableton. `tests/fakes/` stands in for Live's `Live` module and
the `ableton.v2` framework, and `harness.py` drives the script like the pedal
would: footswitch and expression CCs in, scheduler ticks, and the LED and
display CCs the script sends back.

The fakes copy the Live behaviours that have caused bugs here:

- adding a listener twice, or removing one that isn't connected, raises
- using an object after it's deleted (track, device, clip) raises
- changing the set from inside a listener raises, like Live's
  "Changes cannot be triggered by notifications"
- parameter values and tempo outside their range raise

Every test that connects the surface also disconnects it and fails if any
listener is left on the set, or if any exception was raised inside a Live
callback.

The fakes are an approximation of Live, so a passing run here doesn't prove a
change works in Live itself. Anything about how Live really behaves (routing
names, clip recording, timing) still needs checking in Live.
