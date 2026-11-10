# TreadCraft

TreadCraft is a Windows desktop app for building treadmill workouts from individual segments and repeatable blocks. Save workouts as editable JSON, export them as QZ (qdomyos-zwift) XML, or send them directly to QZ Android over local Wi-Fi.

![TreadCraft on Windows showing the 3 × 3000 m workout, with the workout table on the left and the segment and block editors on the right](docs/images/treadcraft-v0.3.0-windows.PNG)

The v0.2.0 redesign adds the TreadCraft branding and a compact layout. The main commands and workout totals stay above the scrollable editor. The window sets its minimum width at startup based on the space needed for the table headings and editor at the current display scaling.

See the [changelog](CHANGELOG.md) and the [draft v0.4.0 release notes](RELEASE_NOTES_v0.4.0.md).

## Run on Windows from the portable ZIP

The portable package is for **Windows x64**. It includes the runtime and requires no installer or Python installation. Use the v0.4.0 source instructions below to try direct Wi-Fi transfer while the v0.4.0 portable package is pending.

1. On the GitHub Releases page, select the **Windows x64 portable ZIP** for the version you want. GitHub's **Source code (zip)** is for the Python launch instructions below. [GitHub Releases](https://github.com/daniel91universe/treadcraft/releases)
2. In File Explorer, right-click the portable ZIP and choose **Extract All**.
3. Open the extracted `TreadCraft` folder and double-click `TreadCraft.exe`. Keep the `_internal` folder beside the executable.
4. To try the app, open `examples\3x3000mt.json` with **Open Workout**. Save your workouts and exports to a folder you can write to, such as Documents.

To verify the download, run `Get-FileHash -Algorithm SHA256 -LiteralPath '<path-to-portable-zip>'` in PowerShell and compare the result with the SHA-256 published alongside the ZIP. The executable is unsigned, so Windows may show a SmartScreen warning. Keep Windows protections enabled and use the archive from the official releases page. [Microsoft SmartScreen guidance](https://support.microsoft.com/en-au/windows/security/windows-security/app-browser-control-in-the-windows-security-app)

## Run on Windows from source

Use Python 3.12 with Tkinter, the configuration tested on Windows. In the Python installer, keep the Tcl/Tk option enabled. Download the repository source as a ZIP and extract it, or clone the repository. Open PowerShell in the folder containing `app.py` and run:

```powershell
py -3.12 -m tkinter
py -3.12 -m pip install -r requirements.txt
py -3.12 app.py
```

The first command opens a Tkinter test window. Close it before continuing. Install the dependencies before going offline if pip needs to download them. If you use `python` instead of the Windows launcher, check that `python --version` reports 3.12 and replace `py -3.12` with `python` throughout this guide.

## Create a workout

1. Enter a **Workout name**.
2. In **Add or Edit Segment**, choose a segment type and give it a name. Set it by **Time** (minutes) or **Distance** (km or m), then enter speed (km/h) and incline (%).
3. Use **Add Segment** to insert at the top level when nothing is selected, or immediately after a selected top-level segment. For repeated intervals, use **Add Block**, then select the block or one of its segments to add each interval or recovery to that block. Click a blank area of the workout list or press **Esc** to clear the selection and return to top-level insertion.
4. To edit a segment, select it under **Workout Structure**, click **Edit Segment**, change its values, then click **Update Segment**. Drag segments to reorder them.
5. Click **Save Workout** and save the file as `workout.json`. Use **Open Workout** to edit it later.

Try the included [3 × 3000 m workout](examples/3x3000mt.json) with **Open Workout**.

## Send a workout to QZ over Wi-Fi

1. Connect the Windows PC and Android device to the same Wi-Fi network. The transfer was verified with **QZ Android 2.20.29** on a local network without Internet access.
2. In QZ, use **Open Floating on a Browser** to get the current URL ending in `/floating/floating.htm`. Return to QZ and keep it in the foreground during the transfer.
3. Paste the full URL into **QZ address** in TreadCraft and click **Test Connection**. Wait for **QZ verified.** TreadCraft remembers the last verified address on this Windows account.
4. Open a workout and click **Send to QZ**. Wait for **Saved in QZ** and note the program name and row count in the confirmation. Open that program in QZ to review it. With the included 3 × 3000 m example, expect **8 rows**, with **3 km** in rows **2, 4, and 6**. Sending saves the program in QZ for review.
5. After restarting TreadCraft, use **Reconnect to QZ** to verify the saved address again. If QZ's IP address or port has changed, paste the current URL and run **Test Connection**. Use **Cancel** to stop a connection check while it is in progress.

## Export QZ XML

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

The example XML was also opened manually in QZ Android 2.20.29 without a treadmill connected. XML export remains available for transferring the file separately and opening it through the QZ file picker.

Commercial LE compatibility is preliminary. Hardware testing still needs to cover treadmill connection to QZ, actual speed reporting and automatic speed changes, positive incline response and whether decline is supported, time and distance transitions, and pause, resume, and stop. The current profile blocks negative incline.

## Run the tests

```powershell
py -3.12 -B -m unittest
```

Run the command from the project folder. The example and the synthetic legacy fixture are included in the repository.
