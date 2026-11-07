# TreadCraft

TreadCraft is a Windows desktop app for building treadmill workouts from individual segments and repeatable blocks. Workouts are saved as editable JSON and can be converted to QZ (qdomyos-zwift) XML using the Python exporter.

## Run on Windows

Use Python 3.9 or later with Tkinter. From the project folder in PowerShell, run:

```powershell
py -m tkinter
py app.py
```

The first command opens a Tkinter test window. Close it before launching the app. If your installation uses the `python` command, substitute it for `py` throughout this guide.

## Create a workout

1. Enter a **Workout name**.
2. In **Add or Edit Segment**, choose a segment type and give it a name. Set it by **Time** (minutes) or **Distance** (km or m), then enter speed (km/h) and incline (%).
3. Click **Add Standalone** to add a single segment. For repeated intervals, enter a block name and repetition count, click **Add Block**, select the block, and use **Add Segment** to add each interval or recovery.
4. Review the order under **Workout Structure**. Click **Save Workout** and save the file as `workout.json`. Use **Open Workout** to edit it later.

## Export for QZ

The XML exporter is available as a Python module. With `workout.json` in the project folder, run this in PowerShell:

```powershell
py -c "import json; from pathlib import Path; from qz_xml_export import export_workout; result = export_workout(json.loads(Path('workout.json').read_bytes())); Path('workout-qz.xml').write_text(result.xml, encoding='utf-8')"
```

Load `workout-qz.xml` in QZ as a training program. The exporter checks the Commercial LE profile and rejects incompatible workouts, such as segments with negative incline. The XML format has been checked against the QZ parser. Import on a real device and treadmill behavior still need verification.

## Run the tests

```powershell
py -B -m unittest
```

The full suite expects the original local files `3x3000mt.json` and `Allenamento_test.json` in the project folder. They are ignored by Git and are absent from a fresh clone, so tests that read them will fail there.
