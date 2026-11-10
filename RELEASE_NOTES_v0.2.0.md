# TreadCraft v0.2.0 · Brand & UI Redesign

Draft for the Windows source release.

TreadCraft has a refreshed look and a more compact editor. The workout table sits beside the segment and block editors, with the main commands and totals visible above them. Repetition counts and numeric columns are easier to scan. The QZ preview opens over the main window and returns focus when it closes.

## Getting started

Use Windows and Python 3.12 with Tkinter. Extract the source ZIP or clone the repository. Open PowerShell in the folder containing `app.py` and run `py -3.12 app.py`. See the [README](README.md) for the Tkinter check and export instructions.

## Verification

The UI baseline at commit `8f5dc09` passed all **72 automated tests** from a clean copy on Windows with Python 3.12.10. Manual Windows checks covered display scaling at 100%, 125%, 150% and 175%. The pre-release GUI check used simulated 175% Tkinter scaling. The [3 × 3000 m sample](examples/3x3000mt.json) exported all **eight expected QZ XML rows**, and its source JSON stayed unchanged.

## QZ and Commercial LE

TreadCraft exports a file for manual import into QZ. The sample was transferred separately over local Wi-Fi and opened in QZ Android 2.20.29, where all eight rows appeared in the preview without a treadmill connected. Direct Wi-Fi delivery from TreadCraft is planned for a future version.

The Commercial LE profile is preliminary and blocks negative incline in the QZ export. Connection, live speed reporting, automatic speed changes, incline response, timed and distance transitions, pause, resume, and stop still require testing with the treadmill connected. Saving a new XML requires a destination that supports hard links.
