# UI-02B — Compact toolbar and block drag-and-drop

Date: 17 November 2026. Verdict: **READY — final layout accepted by the user**.

## Baseline and protection of existing work

Dedicated branch: `codex/ui-02b-layout-block-drag`.

Worktree: `C:\Users\user\Documents\TreadmillApp\.worktrees\ui-02b-layout-block-drag`.

Git HEAD: `b719231118341a0ad6914fafa0e8b7f242b2f822`.
Discovery and UI-02A are still uncommitted in their source worktrees. This branch
therefore starts with an explicit, SHA-256-verified snapshot of the ten UI-02A
development files, rather than assuming that HEAD already contains discovery.
The Git diff against HEAD includes these prerequisites as well as UI-02B.
No commits were created during implementation. See the publication review below.

The three existing worktrees were inspected before editing:

| Worktree / branch | Work preserved / recovered |
|---|---|
| `.worktrees/qz-discovery` / `codex/qz-discovery` | Existing discovery engine, adapter, dependencies, tests and packaging. No source-worktree changes. |
| `.worktrees/ui-02a-qz-controls` / `codex/ui-02a-qz-controls` | Verified snapshot of discovery plus UI-02A controls cleanup and tests. Source snapshot rechecked unchanged at completion. |
| Primary worktree / `codex/ui-02-layout-block-drag` | Recovered only block-drag handlers and the existing 12-test block-drag fixture. Original app.py still has its original 94 insertions / 9 deletions; no edits there. |

Unrelated reports, workouts, assets and earlier builds were left intact. No
changes to main, Android QZ, credentials, dependencies or network settings.

## Controls and behaviour

The main action bar has exactly six buttons, in equal-width adjacent columns:

| Column 1 | Column 2 | Column 3 |
|---|---|---|
| Open Workout | Check Commercial LE | QZ Devices |
| Save Workout | Export XML | Send to QZ |

`check_commercial_le` still assesses the current workout snapshot with
`assess_workout` and displays compatibility diagnostics. It does not save or send
a workout, or control a treadmill.

- Removed the Manual address opener, panel, entry, verifier button and unused
  panel-toggle method. Internal endpoint state, configuration persistence,
  `test_qz_connection`, `reconnect_to_qz` and identity verification remain.
- Device selection still verifies QZ identity separately from workout sending.
  The selector and automatic bounded search remain. Its toolbar caption is now
  consistently `QZ Devices`; search progress stays in the selector dialog.
- Cancel remains outside the six-action toolbar and appears only during
  cancellable identity verification. Sending retains its existing behaviour.
- Removed Move Block Up / Move Block Down widgets. Their internal move function
  was retained rather than removing unrelated logic.
- Duplicate Block is immediately below Update Block; original enabled/disabled
  behaviour is preserved.
- Follow-up refinement: editors are titled **Segments** and **Blocks**. Both use
  the same two-by-two command layout: Add / Update above Remove / Duplicate,
  with matching Success / Secondary / Danger / Secondary styles. Edit Segment
  is removed; selecting a segment loads its fields automatically, matching block
  selection. Repeated events for the same selection preserve unsaved field edits.
  Switching to a block or clearing selection disables the segment edit target.
  During a live drag, preview indices are not used to load model data.
- The old segment-action frame under the workout list and its unused wrapping
  handler are removed. Internal edit/update/duplicate/remove functions remain.
- Reduced existing editor padding slightly, without altering branding or fields.

## Block dragging

Recovered the existing original-row/subtree preview and model-reordering logic.
Added a thin destination-line overlay; it never creates a workout row or a copy
of a block. Preview changes only Treeview order. Release commits the model order,
preserving block identity, child segments, repetitions, expanded/collapsed state
and selection. Pointing at a child of another block targets the whole parent.

Own-child drops, movement below the drag threshold, headings and releases outside
the list do not reorder data. Esc restores the preview and clears selection.
When the live preview moves the original subtree under the pointer, its accepted
destination is retained rather than oscillating back to the old position.
If the release position differs from the last motion event, its target is resolved
against the visible preview before restoring the original tree order. This avoids
interpreting the same pointer coordinates as a different row after restoration.
The indicator is removed on cancellation and release. Existing segment dragging
is preserved; no new segment-drag feature was introduced.

## UI-02B-specific files

- `app.py`: toolbar, removed/moved controls, recovered block dragging and indicator.
- `qz_discovery_ui.py`: accepts the existing toolbar button; stable caption and
  removal of messages directing users to the removed manual panel. Network
  discovery/verification logic is unchanged.
- `test_qz_controls_cleanup.py`: adapts the seven UI-02A tests to the removed manual
  UI and cancels test-only pending Tk callbacks before destroying fixtures.
- `test_block_drag.py`: recovers the 12 existing tests and adds three regression
  tests for a preview under the pointer, changed release targets and repeated
  moves without loss/duplication.
- `test_ui02b_layout.py`: 15 new real-Tk tests, including matched styles/positions,
  automatic segment editing, draft retention, duplicate and remove commands.
- `test_segment_selection.py`: updates the previous explicit-edit selection test
  to the new automatic-edit selection behaviour.
- `README.md`: current toolbar, device-selection and drag instructions; removes
  obsolete manual-panel/Test Connection/Reconnect UI instructions.
- This report.

Inherited `qz_discovery.py`, requirements, packaging spec and discovery tests were
checked byte-for-byte against UI-02A. Workout data processing, XML exporter,
WebSocket payload/client, configuration module and brand assets are unchanged.

## Verification

**169 tests PASS, no skips** with the existing Python 3.12.10 environment at
`.worktrees/qz-discovery/.venv`. Full run: 16.753 seconds. No new dependencies.

Coverage includes toolbar grid/widths, removed controls, duplicate position and
states, segment action ancestry/position, the unchanged compatibility command,
live preview/indicator, actual Tk mouse press-motion-release bindings, cancellation,
up/down moves, own children, external segments, closed/identical blocks, repeated
moves, JSON saving and XML order, discovery selection without automatic sending,
WebSocket simulated-server tests and all existing workout/export/icon regressions.

The unchanged 3×3000 m example still exports eight rows with `distance="3"` at
positions 2, 4 and 6. Moving its repeated block before the warm-up produces eight
rows in the new intended order, with those distances at positions 1, 3 and 5;
the complete row attributes match the original rows reordered. The saved JSON
matches the actual new block order. No source fixture JSON/XML was modified.

Python syntax is exercised by the suite; `git diff --check` passes.

### Windows runtime and limits

Real Tk windows were opened and their widget positions, sizes, selection,
callbacks, mouse bindings and drop indicator checked. Runtime metrics:

- Effective window DPI reported: 96; Tk scaling approximately 1.33265.
- Initial geometry: 902×600; requested 900×600 is clamped to the existing
  content-based minimum of 902×600.
- Toolbar buttons: 144×33, columns at x=12, 162 and 312; rows at y=2 and 39.
- Content requested height 362, viewport 380: no vertical overflow in this run.
- Minimum-size test verifies toolbar and segment actions are not clipped.

Windows screen capture failed twice (FrameArrived/window-capture timeout).
Consequently **visual appearance at 175% and on the tablet is NOT VERIFIED in
this phase**. Metrics are not evidence of visual sharpness or physical mouse feel.
No Windows scaling or DPI-awareness setting was changed.

One real six-second DNS-SD search returned zero services. No repeated polling,
phone configuration changes or workout sending were performed. This is not a
new positive end-to-end QZ connection test. Discovery/client code is preserved
and simulated regressions pass; repeat the real-device check with QZ foregrounded.

### Follow-up uniformity refinement

The user requested the final Segments / Blocks layout after the initial UI-02B
trial. Final follow-up suite: 169 tests PASS. Previous runtime dimensions above
refer to the initial UI-02B measurement; the new action-grid geometry is checked
by the updated real-Tk minimum-window tests. Visual acceptance of these new
positions remains pending on PC/tablet.

## Local portable

Built successfully using the unchanged inherited onedir spec and existing
PyInstaller 6.22.3 environment. Runtime checks include Python 3.12, Tcl/Tk,
brand icon and collected discovery dependencies.

Executable:
`C:\Users\user\AppData\Local\Temp\treadcraft-ui02b-dist\TreadCraft\TreadCraft.exe`

The executable was started locally, exposed a responsive `TreadCraft` window,
and closed normally, including after the final release-target correction.
This is an application-startup check, not a completed
tablet or QZ-button test. Copy the **entire TreadCraft folder**, including
`_internal`, for tablet testing; the executable alone is insufficient.
No ZIP, tag, PR, push or release was created.

## Manual review on PC at 175% and tablet

1. Start the new portable explicitly from the path above, keeping old builds
   closed to avoid confusing the versions. Confirm the three columns and no
   Manual address / Move Block controls, plus Duplicate Block below Update Block, plus the matching Segments / Blocks action grids.
2. Open a copy of `examples/3x3000mt.json`. Verify segment actions inside Segments
   and all controls at the minimum size. Select an internal and external segment,
   check automatic field loading and Update Segment; test Duplicate and Remove. Check normal resizing and keyboard focus.
3. Drag the repeated block above the warm-up and below the cooldown. Observe the
   original subtree and destination line, selection and preserved repetitions.
   Check Esc, outside-list release and an invalid own-child drop. Add another
   block to check swaps, including a collapsed block and repeated moves.
4. Save/reopen under a new test filename and export XML. Check eight rows and
   their new order. Reopen the unchanged original example to verify the original
   eight-row order (3 km at rows 2, 4 and 6).
5. With discovery-enabled QZ foregrounded, open QZ Devices, select and connect.
   Confirm identity checking does not send a workout. Send only on explicit click
   and review QZ's eight-row acknowledgement. No treadmill is required for this
   transport/import check; hardware transitions remain outside this phase.

## Verdict

**READY**. No failures remain in automated tests or startup. The user confirmed
the final Segments / Blocks layout works and approved publication as a draft PR.
The final acceptance did not specify a new 175%/tablet test or renewed end-to-end
QZ connection; those are not inferred from the layout confirmation.

## Publication review

GitHub main was checked and still points to
`b719231118341a0ad6914fafa0e8b7f242b2f822`. Discovery and UI-02A are not on main.
After this dependency was explicitly identified, the user authorized publishing
them as separate prerequisite commits, followed by the distinct UI-02B commit,
all on `codex/ui-02b-layout-block-drag`. The original source worktrees remain
unchanged. The draft PR therefore includes all three increments, distinguished
in its history and description. No build outputs or unrelated files are included.
Publication does not authorize merge, tags or releases.
