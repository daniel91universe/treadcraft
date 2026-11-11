# TreadCraft v0.4.0 · QZ Wi-Fi integration

Draft release notes.

TreadCraft can send workouts directly from Windows to QZ Android on the same local Wi-Fi network. QZ saves the program for review and TreadCraft reports the saved name and row count. Editable JSON and QZ XML export remain available.

## Connect and send

1. In QZ Android, use **Open Floating on a Browser** to get the current URL. Return to QZ and keep it in the foreground.
2. Paste that URL into **QZ address** in TreadCraft and click **Test Connection**. After **QZ verified.**, open a workout and click **Send to QZ**. Use the name in the confirmation to find the program in QZ.
3. Use **Reconnect to QZ** after restarting TreadCraft. If the saved address no longer works, paste the current URL and verify it. **Cancel** stops a connection check in progress.

See the [README](README.md) for Windows setup, the complete Wi-Fi guide, and XML export.

## Verification

- The full source suite passed **95 tests** at the PR #17 merge commit `0116844`.
- On Windows with **QZ Android 2.20.29**, using local Wi-Fi without Internet or a treadmill, the source build passed reconnection after restart, stale address handling, and cancellation.
- The final source test confirmed that the **3 × 3000 m** workout arrived with **8 rows** and that rows **2, 4, and 6** retained **3 km** each.
- The source snapshot used for the portable build, commit `cd978aa3a3e6752e16724ad17f6d6a13c0a0c5d5`, also passed **95 tests**. The extracted portable executable started successfully on Windows.
- On 11 November 2026, the user verified the portable on a Windows tablet without Python installed, with QZ Android **2.20.29** and no Internet or treadmill. Startup, reconnection after restart, and transfer passed. QZ received **8 rows** and preserved all **three 3 km repeats**.

## Portable candidate

The Windows x64 onedir candidate is `TreadCraft-v0.4.0-Windows-x64-cd978aa.zip`, built from commit `cd978aa3a3e6752e16724ad17f6d6a13c0a0c5d5` with Python 3.12.10, PyInstaller 6.22.3, and websockets 15.0.1. Publication is pending.

SHA-256, recalculated and matched against the local checksum file:

```text
7dd642467dac7fa0f49bd887890b423f157b0ccc6b45d309235352c23e835da0
```

## Commercial LE hardware testing

Commercial LE support remains preliminary. Hardware testing still needs to cover connecting the treadmill to QZ, reading and controlling speed, positive incline response and whether decline is supported, transitions between timed and distance intervals, and pause, resume, and stop. The current profile blocks negative incline.
