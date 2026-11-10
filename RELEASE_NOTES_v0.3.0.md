# TreadCraft v0.3.0 · Windows Portable

Draft for the first portable Windows x64 release.

TreadCraft now comes as a portable ZIP with Python and Tcl/Tk included. The workout editor also brings **Speed** and **Incline** closer to the other segment fields and places **Block name** and **Repetitions** on one line.

**Save Workout** suggests a JSON filename based on the workout title. When an opened workout has a blank, missing, or default title, TreadCraft displays the filename without its extension.

## Download and run

Download the Windows x64 portable ZIP from the GitHub release assets when it is published. Choose **Extract All**, open the extracted `TreadCraft` folder, and launch `TreadCraft.exe`. Keep `_internal` beside the executable. No installer or Python installation is required. The executable is unsigned, and Windows may display a SmartScreen warning. See the [README](README.md) for checksum verification and source launch instructions.

## Verification

- Portable build source: `56ab024bcfd7d17725896341a81728aa5540da99`. The source suite passed **73 tests**.
- The updated portable ZIP passed the user's test on a Windows tablet without Python. Earlier tablet testing explicitly covered startup, the logo, saving and reopening JSON, and exporting all eight XML rows of the 3 × 3000 m sample.
- The updated ZIP was built with Python 3.12.10 x64 and PyInstaller 6.22.3. Two builds of the earlier WIN-04 candidate produced identical ZIPs on the same PC.
- Portable ZIP SHA-256: `c779dfdc9e425626510439f11b8e376c5733061075094ce17196e28f491efe69`.

## QZ and Commercial LE

Exported XML can be transferred separately and opened manually in QZ Android. Direct delivery from TreadCraft to QZ via Wi-Fi remains planned. The preliminary Commercial LE profile blocks negative incline in QZ export. Connection, speed and incline response, interval transitions, pause, resume, and stop still require testing with the treadmill connected. Saving a new XML file requires a destination that supports hard links.
