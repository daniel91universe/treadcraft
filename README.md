# TreadCraft

TreadCraft builds treadmill workouts from timed and distance-based segments and repeated blocks. Save editable JSON, export QZ XML, or explicitly send a workout to a compatible QZ application over the local network.

## v0.5.0

The compact toolbar has three columns:

| Column 1 | Column 2 | Column 3 |
|---|---|---|
| Open Workout | Check Commercial LE | QZ Devices |
| Save Workout | Export XML | Send to QZ |

The **Segments** and **Blocks** editors use matching Add/Update and Remove/Duplicate actions. Select a segment to load its fields, then use **Update Segment** to apply changes. Drag a block heading to reorder the whole block with its repeats and segments. A line marks the destination; Esc or an outside-list release cancels the block move. Existing segment dragging remains available.

See [CHANGELOG.md](CHANGELOG.md) and [v0.5.0 release notes](RELEASE_NOTES_v0.5.0.md). Earlier releases remain documented in their own versioned notes.

## Windows portable

The Windows x64 onedir package includes Python and Tcl/Tk; the target PC does not need Python installed. Extract the **whole ZIP** and run `TreadCraft/TreadCraft.exe`. Keep `_internal` beside the executable. The TreadCraft folder also contains `LICENSE`, this README and `examples/3x3000mt.json`.

Use **Open Workout** to open the bundled example. Save user JSON and XML files to a writable folder such as Documents. The app stores the last verified QZ endpoint separately under `%LOCALAPPDATA%/TreadCraft/qz_connection.json`.

Compare the archive checksum with the checksum supplied for that exact candidate:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '.\TreadCraft-v0.5.0-windows-x64-RC.zip'
```

A checksum establishes file integrity, not publisher identity. The executable is unsigned. Keep Windows security protections enabled. Source code ZIPs require the Python setup below; they are not portable binaries.

## Run from source

Validated baseline: Windows 10 x64, Python 3.12.10 with Tcl/Tk 8.6.15. Enable Tcl/Tk in the Python installer. From the extracted source directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m tkinter
.\.venv\Scripts\python.exe app.py
```

Close the Tkinter test window before launching the app. Runtime versions are websockets 15.0.1, zeroconf 0.154.0 and ifaddr 0.2.0. Install dependencies while online; local transfer itself does not require Internet access.

## Create and edit workouts

1. Enter a workout name.
2. In **Segments**, choose the type and name, Time (minutes) or Distance (km/m), speed in km/h and incline in percent.
3. **Add Segment** inserts at the top level with no selection, after a selected top-level segment, or inside the selected block/its selected segment. Click blank list space or press Esc to clear the selection.
4. In **Blocks**, enter a name and repetition count, choose **Add Block**, then select the block to add its intervals and recoveries.
5. Select a segment to edit its fields and choose **Update Segment**. Duplicate and Remove operate on the selected item. Block actions follow the same arrangement. Drag blocks to reorder whole repeats; drag segments for segment moves.
6. **Save Workout** saves editable JSON; **Open Workout** reloads it. Reordering changes the order of exported rows, not the JSON/XML formats.

## QZ discovery, verification and sending

Automatic discovery requires QZ to publish **`_qzws._tcp.local.`** with its current WebSocket endpoint. Support is not universal across QZ versions. Official QZ Android 2.20.29 without this advertisement cannot be discovered automatically; XML file import remains available.

1. Put Windows and the Android device on the same LAN. Keep a discovery-capable QZ build in the foreground with its server active.
2. TreadCraft performs a bounded six-second search. Open **QZ Devices**, select a service, then **Connect to selected QZ**. This verifies QZ identity with `workouteditor_env`; discovery alone does not establish identity or send a workout.
3. Wait for **QZ verified.**, then explicitly choose **Send to QZ**. Confirm the saved name and row count and review that program in QZ. Cancel is available during cancellable identity verification.
4. After a QZ server restart or port change, open **QZ Devices** and choose **Search again**, then verify the current service. If no device appears, check that QZ publishes the service and that the LAN carries multicast. A reachable WebSocket alone does not prove DNS-SD is working.

Browsing is IPv4 and bounded; it does not scan the subnet. VPNs, guest-network isolation and multicast handling can affect discovery. No Bonjour installation is required. A verified endpoint is a point-in-time result, not a guarantee QZ remains online. Sending saves a training program for review; it does not start the treadmill.

The user confirmed successful discovery in the portable on the new router after changing the trusted home Ethernet network profile from Public to Private, together with successful WebSocket connection and workout transfer. This is a user-observed application result, not an independent packet capture. Earlier QZ 2.20.29 transfer tests do not establish universal discovery compatibility.

**Windows troubleshooting:** if discovery finds no QZ device, check whether the connection to your trusted home LAN is classified as Public. Using the Private profile on a trusted home network may resolve discovery restrictions; it is not universally required. Do not disable the firewall and do not classify public or untrusted networks as Private. QZ must still publish `_qzws._tcp.local.`.

## Export XML

Open a workout and select **Export XML**. Review row counts, time/distance estimates and compatibility diagnostics. Choose **Export**, then a destination. Either preview cancellation or destination cancellation leaves no exported file.

The bundled 3×3000 m example exports **8 rows**, with `distance="3"` at rows **2, 4 and 6**. Distance is retained in km as the end criterion; an estimated duration supports QZ preview. Reordering the workout reorders those rows. Transfer XML separately and open it in QZ to review it.

Writing a new XML file requires a filesystem supporting hard links; choose another destination if necessary. JSON remains editable and compatible with existing workouts.

## Commercial LE limitations

**Check Commercial LE** assesses a preliminary capability profile. It does not connect to or control the treadmill. Negative incline is blocked. Hardware tests remain pending: connection, reported/commanded speed, incline/decline, timed and distance transitions, pause, resume and stop. No hardware success is inferred from file export or network transport.

## Tests and reproducible build procedure

Use a fresh source checkout and a separate environment. Runtime and build dependencies are separated; `requirements-build.txt` includes runtime requirements and pins the validated build tools.

```powershell
py -3.12 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv-build\Scripts\python.exe -m pip check
.\.venv-build\Scripts\python.exe -B -m unittest discover -q
.\.venv-build\Scripts\python.exe -m PyInstaller --clean --noconfirm TreadCraft.spec
```

Validated builder: Python 3.12.10/Tcl-Tk 8.6.15, PyInstaller 6.22.3 and hooks 2026.10 on Windows 10 x64. The spec retains the onedir architecture, collects discovery modules and dependency licenses, and adds the user-facing files beside the exe. This procedure fixes versions but does **not** promise byte-for-byte binary reproducibility.

Check `dist/TreadCraft` for the exe, complete `_internal`, LICENSE, README and example. Copy that entire folder to an independent directory and test it before archiving. A local candidate ZIP can be created after automated checks pass:

```powershell
Compress-Archive -Path .\dist\TreadCraft -DestinationPath .\TreadCraft-v0.5.0-windows-x64-RC.zip
Get-FileHash -Algorithm SHA256 -LiteralPath .\TreadCraft-v0.5.0-windows-x64-RC.zip
```

Verify the extracted archive and test creation/editing, drag-and-drop, JSON save/reopen and eight-row XML export on the new portable, including a Windows device without Python. Build success and startup alone do not complete this functional validation. A checksum must always correspond to the archive being distributed.
