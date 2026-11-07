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

Try the included [3 × 3000 m workout](examples/3x3000mt.json) with **Open Workout**.

## Export for QZ

The XML exporter is available as a Python module. With `workout.json` in the project folder, run this in PowerShell:

```powershell
py -c "import json; from pathlib import Path; from qz_xml_export import export_workout; result = export_workout(json.loads(Path('workout.json').read_bytes())); Path('workout-qz.xml').write_text(result.xml, encoding='utf-8')"
```

To export the example instead, replace `workout.json` in the command with `examples/3x3000mt.json`.

Load `workout-qz.xml` in QZ as a training program. The exporter checks the Commercial LE profile and rejects incompatible workouts, such as segments with negative incline.

Distance-based segments retain their `distance` in kilometers as the end criterion. The exporter also adds an estimated `duration` for the QZ preview, calculated from the distance and target speed and rounded to the nearest second. For example, a 3 km repeat at 14 km/h has `distance="3"` and `duration="00:12:51"`. If the estimate falls outside QZ's duration range after rounding, the exporter keeps the distance and emits a warning.

The example XML with both attributes was loaded and displayed in the QZ preview on a phone. Segment transitions and speed control on a connected treadmill remain to be verified.

## Run the tests

```powershell
py -B -m unittest
```

Run the command from the project folder. The example and the synthetic legacy fixture are included in the repository.
