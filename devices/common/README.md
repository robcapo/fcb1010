# Shared Max for Live parts

## MacroToggle

An on/off button for devices whose switches are driven by rack macros.

- **Macro input:** its Live parameter runs 0 to 127, so a rack macro maps
  onto it with a full 0 to 127 Min/Max. You can give two toggles
  different ranges on the same macro, so they switch at different points.
- **Output:** 0 for 0 to 63, 1 for 64 to 127, sent out of its outlet.
- **Looks:** a live.text in Toggle mode, like a live.toggle, lit only
  when the output is 1.
- **Click:** flips the output, by setting the parameter to 0 or 127.
- **Mapping:** the 0 to 127 parameter is a see-through live.numbox placed
  over the button's label (Kingtone: the "CH 1" / "CH 2" text). Right-click
  the label, or click it in the rack's Map mode, to map a macro. It can't
  share the button's spot: on top it would take the button's clicks, and
  set to ignore clicks it can't be mapped either. (A live.toggle or
  live.text can't be the parameter: they only hold 0 or 1, and light for
  any value above 0.)
- **Inlet:** a number from 0 to 127 sets it.

`MacroToggle.maxpat` is the abstraction on its own, for a bpatcher in
your own patches; give each copy its own parameter name. Inside a device
built by these scripts, a bpatcher copy wasn't clickable in Live, so
device build scripts call `macrotoggle.parts()` instead, which places the
toggle's objects straight into the device patch with the name already
set. Run `python3 macrotoggle.py` to regenerate the `.maxpat`.
