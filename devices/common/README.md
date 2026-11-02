# Shared Max for Live parts

## MacroToggle

An on/off button for devices whose switches are driven by rack macros.

- **Macro input:** its Live parameter runs 0 to 127, so a rack macro maps
  onto it with a full 0 to 127 Min/Max. You can give two toggles
  different ranges on the same macro, so they switch at different points.
- **Output:** 0 for 0 to 63, 1 for 64 to 127, sent out of its outlet.
- **Looks:** a live.text in Toggle mode, like a live.toggle, lit only
  when the output is 1. (A plain live.toggle or live.text with a 0 to 127
  range lights for any value above 0.)
- **Click:** flips the output, by setting the parameter to 0 or 127.
- **Inlet:** a number from 0 to 127 sets it.

`MacroToggle.maxpat` is the abstraction on its own, for use in a
bpatcher in any device; give each copy its own parameter name. Device
build scripts use `macrotoggle.py` instead, which embeds a copy per
button with its name already set. Run `python3 macrotoggle.py` to
regenerate the `.maxpat`.
