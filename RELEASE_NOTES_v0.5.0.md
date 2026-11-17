# TreadCraft v0.5.0 — QZ discovery and compact workout editing

Windows x64 portable and source distribution.

## Changes

- Discover QZ services advertising `_qzws._tcp.local.`. Select a device and explicitly verify its identity before sending; browsing never sends a workout.
- Use the three-column Open/Save, Check Commercial LE/Export XML and QZ Devices/Send to QZ toolbar.
- Drag whole blocks with their repeats and segments, with a destination indicator, consistent selection and cancellation.
- Use matching Segments/Blocks action grids. Selecting a segment loads its fields; Update Segment applies changes.
- Preserve editable JSON and the existing QZ XML mapping and explicit WebSocket send behaviour.
- Include LICENSE, README and `examples/3x3000mt.json` in the Windows x64 onedir folder, with pinned build requirements documented separately.

## Windows distribution

Extract the complete portable ZIP and run `TreadCraft/TreadCraft.exe`; no Python installation is required on the target device. Keep `_internal` beside it. Compare the SHA-256 for the exact archive. Source distributions require Python 3.12 with Tkinter and the runtime requirements. See README for setup and build instructions.

## Compatibility and validation limits

Discovery requires an announcement from the QZ build in use; it is not supported universally by official QZ versions. QZ Android 2.20.29 without that announcement can still import exported XML. Keep a compatible QZ foregrounded on the same LAN, with its server active. Internet access is unnecessary for local transfer. Multicast restrictions can prevent discovery even when WebSocket verification succeeds.

The automated source suite passed 169 tests. The 3×3000 m example retains eight XML rows and three 3 km repeats at rows 2, 4 and 6. The user completed the portable functional test successfully and confirmed discovery on the new router through TreadCraft portable after changing the trusted home Ethernet profile from Public to Private. WebSocket connection and a real workout transfer were also confirmed by the user. These are user-observed application results, not an autonomous capture of mDNS packets.

On Windows, a Public network profile can be one cause of discovery problems. Use Private only for a trusted home network; it is not universally necessary. Keep the firewall enabled and never classify an untrusted/public network as Private. The QZ service advertisement is still required.

Commercial LE support is preliminary: connection, reported/commanded speed, positive incline and decline capability, time/distance transitions, pause, resume and stop require hardware tests. The current profile blocks negative incline. Saving a program or exporting XML does not validate treadmill control.
