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
- The v0.4.0 Windows x64 portable package and its verification are pending.

## Commercial LE hardware testing

Commercial LE support remains preliminary. Hardware testing still needs to cover connecting the treadmill to QZ, reading and controlling speed, positive incline response and whether decline is supported, transitions between timed and distance intervals, and pause, resume, and stop. The current profile blocks negative incline.
