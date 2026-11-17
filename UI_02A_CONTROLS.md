# UI-02A — Functional QZ controls cleanup

17 November 2026. Verdict: READY for manual review.

## Isolation and baseline

Worktree: C:\Users\user\Documents\TreadmillApp\.worktrees\ui-02a-qz-controls
Branch: codex/ui-02a-qz-controls. HEAD remains b719231 (main baseline).
This worktree contains a hash-verified copy of the eight uncommitted discovery
files from codex/qz-discovery, plus the UI-02A changes. No local commits were made.
The original discovery worktree and primary UI-02 layout/block-drag work remain
unchanged. This phase contains no block-drag or general layout changes.

Since discovery is still uncommitted, the Git diff from HEAD includes that
prerequisite implementation. The UI-02A-specific delta against the discovery
snapshot is app.py, README.md, test_qz_discovery.py (test timing only),
test_qz_controls_cleanup.py and this report. A future commit/PR must preserve this
distinction rather than attributing all inherited discovery code to UI-02A.

## Controls inventory

| Control | Function | UI-02A result |
|---|---|---|
| Test Connection | test_qz_connection → verify_qz | Removed from main UI; same function used by advanced manual verifier |
| Reconnect to QZ | reconnect_to_qz → verify_qz | Removed widget; internal function and saved-endpoint loading retained |
| Send to QZ | send_to_qz → existing payload/save client | Kept as primary action, no automatic sending |
| Export to QZ XML | export_qz_xml | Renamed Export XML; dialog, mapping and output unchanged |
| QZ devices | DiscoveryControls.open | Kept, with bounded automatic discovery and explicit selection |
| Search again | DiscoveryControls.search | Kept in discovery window |
| Connect to selected QZ | connect_discovered_qz | Kept; identity verification only, no workout |
| Editable endpoint | qz_address | Moved to collapsed Manual address panel; current address still displayed on main UI |
| Verify manual address | test_qz_connection | Advanced-panel action reusing the existing verifier |
| Cancel | cancel_qz_verification | Hidden while idle/sending; shown only for cancellable verification |

Workout editing controls and XML/workout formats are unchanged. Manual fields and
send controls retain existing disabling/error handling while operations run.
No endpoint gives an actionable message about selecting a device/manual entry.
No qz_reconnect_button widget references remain. Internal reconnect and verifier
methods remain exercised by tests.

## Files

- app.py: local QZ controls cleanup and Export XML button label.
- README.md: updated control descriptions.
- test_qz_controls_cleanup.py: seven actual Tk tests with discovery mocked.
- test_qz_discovery.py: update test now waits for the first resolution before
  injecting the next event, removing a Windows event-loop scheduling race.
- This report.

Dependencies are inherited unchanged: websockets 15.0.1, zeroconf 0.154.0,
ifaddr 0.2.0. Tests/build use the existing isolated discovery .venv, not global Python.

## Verification

139 tests PASS, including full XML, WebSocket, discovery and workout regressions.
Seven new Tk tests cover removed/kept controls, manual panel toggle/address retention,
internal verifier/reconnect, cancellation visibility, cancellation persistence,
send without unsafe cancel and missing-endpoint messaging.
Tests ran with the Windows user account and real Tcl/Tk widgets; no actual workout
or application protocol command was sent by these GUI tests.
An existing discovery test initially failed due to time-based event injection;
only its fixture timing was corrected. The discovery implementation did not change.

One real six-second LAN discovery returned no services in that window. No phone
configuration or network changes were attempted. This is not a new positive
phone-discovery verification; the earlier real discovery success remains in the
discovery report. Zero-device handling is covered by automated tests.

Packaging uses the unchanged inherited TreadCraft.spec and Windows onedir approach.
Local test build: C:\Users\user\AppData\Local\Temp\treadcraft-ui02a-dist\TreadCraft\TreadCraft.exe
Runtime checks require Tcl/Tk, python312.dll, zeroconf and ifaddr. Tablet/visual
portable acceptance remains a separate manual test, not implied by build success.

## Scope

No push, merge, release, Android operation, QZ change, keystore modification,
general restyling or new drag-and-drop work. The inherited worktree snapshots
remain uncommitted; no conflicts were resolved by overwriting original work.
