# Changelog

## v0.3.0 (unreleased)

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
