# TreadCraft

TreadCraft is a Windows desktop app for building treadmill workouts from individual segments and repeatable blocks. Workouts are saved as editable JSON and can be converted to QZ (qdomyos-zwift) XML using the Python exporter.

## Run on Windows

Use Python 3.12 with Tkinter, the configuration tested on Windows. In the Python installer, keep the Tcl/Tk option enabled. Download the repository source as a ZIP and extract it, or clone the repository. Open PowerShell in the folder containing `app.py` and run:

```powershell
py -3.12 -m tkinter
py -3.12 app.py
```

The first command opens a Tkinter test window. Close it before launching the app. If you use `python` instead of the Windows launcher, check that `python --version` reports 3.12 and replace `py -3.12` with `python` throughout this guide.

## Create a workout

1. Enter a **Workout name**.
2. In **Add or Edit Segment**, choose a segment type and give it a name. Set it by **Time** (minutes) or **Distance** (km or m), then enter speed (km/h) and incline (%).
3. Use **Add Segment** to insert at the top level when nothing is selected, or immediately after a selected top-level segment. For repeated intervals, use **Add Block**, then select the block or one of its segments to add each interval or recovery to that block. Click a blank area of the workout list or press **Esc** to clear the selection and return to top-level insertion.
4. To edit a segment, select it under **Workout Structure**, click **Edit Segment**, change its values, then click **Update Segment**. Drag segments to reorder them.
5. Click **Save Workout** and save the file as `workout.json`. Use **Open Workout** to edit it later.

Try the included [3 × 3000 m workout](examples/3x3000mt.json) with **Open Workout**.

## Export for QZ

1. Open a workout in TreadCraft with **Open Workout**. To try the export, use [examples/3x3000mt.json](examples/3x3000mt.json).
2. Click **Export to QZ XML**. Review the row counts, scheduled duration, estimated duration for distance segments, and compatibility warnings. The example shows 8 rows, including 5 timed and 3 distance segments.
3. Click **Export**, choose a destination for the XML file, and save it. Transfer the file to your Android device and open it in QZ as a training program to review the preview.

The exporter checks a preliminary Commercial LE profile and blocks incompatible workouts, such as segments with negative incline. Saving a new XML file requires a destination that supports hard links. If the destination does not support them, choose another folder.

For command-line use, the XML exporter is also available as a Python module. With `workout.json` in the project folder, run this in PowerShell:

```powershell
py -3.12 -c "import json; from pathlib import Path; from qz_xml_export import export_workout; result = export_workout(json.loads(Path('workout.json').read_bytes())); Path('workout-qz.xml').write_text(result.xml, encoding='utf-8')"
```

To export the example instead, replace `workout.json` in the command with `examples/3x3000mt.json`.

Distance-based segments retain their `distance` in kilometers as the end criterion. The exporter also adds an estimated `duration` for the QZ preview, calculated from the distance and target speed and rounded to the nearest second. For example, a 3 km repeat at 14 km/h has `distance="3"` and `duration="00:12:51"`. If the estimate falls outside QZ's duration range after rounding, the exporter keeps the distance and emits a warning.

The example XML was loaded and displayed in QZ Android without a treadmill connected. Connection to the Commercial LE, actual speed reporting, automatic speed changes, time and distance transitions, and pause, resume, and stop behavior still need verification on the treadmill.

## Run the tests

```powershell
py -3.12 -B -m unittest
```

Run the command from the project folder. The example and the synthetic legacy fixture are included in the repository.
