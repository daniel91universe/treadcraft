# TreadCraft — QZ DNS-SD discovery implementation

Date: 17 November 2026. Verdict: READY for user review and manual Windows testing.

## Baseline and isolation

GitHub main and local baseline: b719231118341a0ad6914fafa0e8b7f242b2f822,
the PR #19 merge after v0.4.0. This repository is a Tkinter desktop application,
not a FastAPI/web application. Existing networking lives in qz_ws_client.py.

Branch: codex/qz-discovery. Worktree:
C:\Users\user\Documents\TreadmillApp\.worktrees\qz-discovery

The primary workspace remains on codex/ui-02-layout-block-drag. Its existing
103-line app.py diff (94 additions, 9 removals) and other local files are preserved.
No commit, push, release, QZ modification or phone operation was performed.

## Implementation

qz_discovery.py browses only _qzws._tcp.local. using python-zeroconf's asyncio API.
Each session lasts six seconds, uses IPv4 on the available interfaces, limits
the session to 32 instance names and four simultaneous resolutions, and limits
each resolution to 1200 ms. Closing the view/application cancels the session.
The browser, resolver tasks and Zeroconf sockets are closed in finally blocks.
Updates replace instance endpoints; removals remove them; duplicate endpoint sets
are collapsed for presentation. No subnet scan or DNS-system .local lookup occurs.

TXT parsing bounds field count and size, rejects malformed encodings and explicitly
unsupported protocol/version/path values. Missing TXT is marked incomplete and
still requires explicit user verification. Only root ws endpoints accepted by
the existing normalize_endpoint function are offered. Loopback, multicast,
public and unsupported addresses are discarded. LAN addresses precede link-local;
up to eight published candidates are tried after user selection, each with a
two-second QZ identity-verification timeout. No connection is attempted by browsing.

qz_discovery_ui.py provides a branded ttk list in a secondary window. Discovery
runs once after the main QZ controls open. The QZ devices button shows search/count
state; opening the list starts a new search if none is active. Search again starts
another bounded session. Services and successful identity verification are separate.
Workers communicate through a queue; only the Tk thread updates widgets.

The selected service uses start_qz_operation and existing verify_qz, including
the existing non-destructive workouteditor_env verification and persistence only
after success. It sends no training program and starts no treadmill. The original
manual address, Test Connection, Reconnect and Send paths remain available.
Verified endpoints are written back to the address field, including a successful
alternate IPv4 address. A busy QZ operation prevents switching the endpoint.

## Files and dependencies

- app.py: small integration with the existing QZ controls and operation worker.
- qz_discovery.py: parsing, lifecycle, bounded browse and verifier reuse.
- qz_discovery_ui.py: Tk discovery view and worker/queue adapter.
- test_qz_discovery.py: 24 new automated tests.
- requirements.txt: zeroconf==0.154.0, ifaddr==0.2.0; websockets unchanged.
- TreadCraft.spec: existing Windows onedir packaging approach with explicit
  collection of zeroconf/ifaddr dynamic modules, binaries and license metadata.
- README.md and this report: operation, packaging and limitations.

Development dependencies were installed only in this worktree's .venv, using
CPython 3.12.10 x64. No system Python changes. The pinned historical release
builder was not repurposed for uncommitted development code.

## Verification

- Full suite: 132 tests PASS (108 baseline + 24 discovery/integration tests).
- pip check: PASS. git diff --check: PASS.
- Mock DNS-SD tests: parsing, dynamic IP/port, zero/one/multiple instances,
  removal including pending resolution, duplicates, missing/invalid TXT,
  resolution failure, duration bounds, cancellation and browser cleanup.
- Mock WebSocket integration: candidate fallback, failed identity, explicit
  selection and preservation of a busy manual operation. Existing WebSocket,
  XML and workout regression tests remain in the full suite.
- Actual Tk construction/result rendering/selection/close: PASS under the
  Windows user account, with the connection operation mocked (no command sent).
- One actual LAN browse: QZ Fitness WebSocket._qzws._tcp.local. resolved to
  ws://192.168.1.12:35885/ with complete metadata. WebSocket handshake PASS.
  No QZ application message or training program was sent during this real test.
- PyInstaller onedir build: PASS, including python312.dll, _tkinter.pyd,
  Tcl/Tk data, zeroconf/ifaddr packages and zeroconf license COPYING.

The first sandbox packaging trial lacked access to Tcl/Tk and excluded it.
It is NOT the usable build. The build repeated with the Windows user account
passed explicit runtime-file checks and includes the final source changes.
Usable local build:
C:\Users\user\AppData\Local\Temp\treadcraft-discovery-user-dist\TreadCraft\TreadCraft.exe

This is a packaging/build check, not a completed portable visual/tablet test.

## Manual Galaxy A15 test

1. Keep QZ-06F-03 in the foreground on the same LAN as Windows. No treadmill or
   Internet connection is needed. Leave existing network and firewall settings intact.
2. Launch app.py with this worktree's .venv\Scripts\python.exe, or use the local
   onedir executable above with its entire adjacent _internal directory.
3. Wait six seconds and open QZ devices. Confirm instance name and current endpoint;
   do not assume the test endpoint/port is still current.
4. Select it and Connect to selected QZ. Expect QZ verified and the selected
   working address in the original address field. This step sends only the existing
   identity query, not a workout. Do not press Send to QZ for the discovery test.
5. Restart QZ manually if desired, then Search again and verify its new port.
   During a search, closing QZ should remove its service when a removal/expiry is received.
6. Close the discovery window during a search, reopen it, and test manual entry.
   Existing automatic-reconnection policies are unchanged.

## Limits

DNS-SD is an unauthenticated hint. The existing QZ verifier recognizes protocol
structure but is not cryptographic authentication. Plain local ws is unchanged.
A successful verification is point-in-time: the client closes the connection
after the check and does not monitor QZ continuously. A saved list may become
stale after a bounded search; refresh before reconnecting after an IP/port change.
VPNs, Wi-Fi client isolation, adapter policy or multicast firewall rules can block
discovery. Never disable protections as a workaround; manual entry remains usable.
Windows public/private LAN addresses are handled through the existing client policy;
CGNAT/mobile addresses and IPv6 discovery are intentionally not offered here.
The standard QZ 2.20.29 app may not advertise this service; the verified phone test
uses the experimental QZ-06F-03 build. Portable user testing remains pending.

## Sources checked

https://pypi.org/project/zeroconf/0.154.0/ (Python >=3.11, Windows CPython 3.12 wheel).
Installed 0.154.0 AsyncServiceBrowser/AsyncServiceInfo/AsyncZeroconf signatures
were inspected directly before implementation and exercised in mock and LAN tests.
