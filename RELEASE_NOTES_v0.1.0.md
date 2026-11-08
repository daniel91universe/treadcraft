# TreadCraft v0.1.0

Draft for the first Windows source release. TreadCraft lets you build treadmill workouts from timed or distance-based segments, group them into repeat blocks, and reorder segments by dragging. Save workouts as editable JSON and reopen them later.

Use **Export to QZ XML** to review row counts, scheduled durations, distance estimates, and compatibility warnings before saving. The included [3 × 3000 m example](examples/3x3000mt.json) produces eight XML rows.

## Getting started

Use Windows and Python 3.12 with Tkinter enabled. Extract the source ZIP or clone the repository, then open PowerShell in the folder containing `app.py`. Run `py -3.12 -m tkinter` to check Tkinter, close the test window, and run `py -3.12 app.py`. See the [README](README.md) for editing and export instructions.

## Compatibility and limitations

The example XML has been opened and previewed in QZ Android without a treadmill connected. Commercial LE compatibility is preliminary. The current profile blocks negative incline. Saving a new XML file requires a destination that supports hard links.

Hardware tests remain open for connecting to the Commercial LE, reading actual speed, applying automatic speed changes, completing timed and distance segments (including each 3 km repeat), and pausing, resuming, and stopping the workout.
