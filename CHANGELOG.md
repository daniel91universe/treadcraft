# Changelog

## v0.4.0 (unreleased)

- Send workouts directly from Windows to QZ Android over local Wi-Fi, with confirmation of the saved program name and row count. XML export remains available.
- Verify the QZ address, reconnect to the last verified address after restarting TreadCraft, or cancel a connection check. If QZ changes address or port, enter its current URL and test again.
- Fit the QZ controls on one row and size the window at startup to show the editor panels when screen space allows.
- Verified with QZ Android 2.20.29 without Internet or a treadmill. The 3 × 3000 m transfer preserves eight rows and all three 3 km repeats. Commercial LE hardware validation remains pending.

## v0.3.0

- Added a portable Windows x64 ZIP with the Python and Tcl/Tk runtime, branding assets, and the 3 × 3000 m sample. Extract the complete folder and run TreadCraft without installing Python.
- Compacted the Speed and Incline fields, aligned the segment type selector, and placed the block name and repetition count on one line in **Workout Blocks**.
- **Save Workout** suggests a JSON filename based on the workout title. When a loaded workout has a blank, missing, or default title, the editor shows the filename without its extension.

## v0.2.0

- Applied Brand v1.0, with a dark palette, a clearer header logo, Windows icons, and distinct button and focus styles.
- Moved the main commands and totals above the workspace. Placed the workout table on the left and the segment and block editors on the right.
- Made the editor more compact and clarified distance units, repetition counts, numeric columns, and validation messages.
- Set a compact startup size with a minimum width that accounts for font scaling. Centered the QZ export preview and restored focus when it closes.
- Preserved JSON compatibility and the QZ XML export format. Direct Wi-Fi delivery to QZ remains planned.

## v0.1.0 · 2026-11-08

- First public Windows source release, with an editor for timed and distance-based workouts and repeat blocks, editable JSON, and QZ XML export with a preview.
