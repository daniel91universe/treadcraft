"""Bounded IPv4 DNS-SD discovery. No QZ commands or connections during browsing."""
import asyncio
from dataclasses import dataclass
import ipaddress
import math

from qz_ws_client import QzConnectionError, normalize_endpoint, verify_qz

SERVICE_TYPE = "_qzws._tcp.local."


@dataclass(frozen=True)
class QzService:
    name: str
    endpoints: tuple[str, ...]
    host: str = ""
    warning: str = ""


def parse_service(name, info, addresses):
    """Treat DNS-SD as untrusted hints; permit only the existing root WS contract."""
    if not isinstance(name, str) or not name.endswith(SERVICE_TYPE) or len(name) > 255:
        raise ValueError("Invalid QZ service name.")
    if type(info.port) is not int or not 1 <= info.port <= 65535:
        raise ValueError("Invalid QZ port.")
    properties = info.properties or {}
    if not isinstance(properties, dict) or len(properties) > 32:
        raise ValueError("Invalid QZ TXT records.")
    txt = {}
    size = 0
    for key, value in properties.items():
        if not isinstance(key, bytes) or value is not None and not isinstance(value, bytes):
            raise ValueError("Invalid QZ TXT encoding.")
        size += len(key) + len(value or b"")
        if size > 4096:
            raise ValueError("QZ TXT records too large.")
        if key in (b"path", b"protocol", b"version"):
            txt[key] = (value or b"").decode("ascii")
    for key, expected in ((b"path", "/"), (b"protocol", "ws"), (b"version", "1")):
        if key in txt and txt[key] != expected:
            raise ValueError("Unsupported QZ service contract.")
    endpoints = set()
    for address in addresses[:32]:
        try:
            ip = ipaddress.IPv4Address(address)
            if ip.is_loopback or ip.is_multicast or ip.is_unspecified:
                continue
            endpoints.add(normalize_endpoint(f"ws://{ip}:{info.port}/"))
        except (ValueError, QzConnectionError):
            continue
    if not endpoints:
        raise ValueError("QZ service has no supported local IPv4 address.")
    # Try LAN addresses before link-local. Connection verifies every candidate, not just the first.
    ordered = tuple(sorted(endpoints, key=lambda e: ("169.254." in e, e)))[:8]
    label = name[:-len(SERVICE_TYPE)].rstrip(".")
    label = "".join(c if c.isprintable() else " " for c in label)[:128]
    missing = len(txt) != 3
    return QzService(name, ordered, str(info.server or "")[:255],
                     "Missing TXT metadata; QZ identity must be verified." if missing else "")


async def verify_service(service, *, timeout=2):
    """Called only after user selection; reuse the existing non-destructive QZ verifier."""
    for endpoint in service.endpoints:
        try:
            return await verify_qz(endpoint, timeout=timeout)
        except QzConnectionError:
            continue
    raise QzConnectionError("Discovered QZ could not be verified. Open QZ Devices and choose Search again. Keep QZ open and check that it advertises its service on this LAN.")


async def discover(*, duration=6, cancel=None, emit=lambda services: None, backend=None):
    """One bounded browse session. Updates/removals replace snapshots; always close sockets."""
    if not math.isfinite(duration) or not 0 < duration <= 30:
        raise ValueError("Discovery duration must be between 0 and 30 seconds.")
    if backend is None:
        try:
            from zeroconf import IPVersion, ServiceStateChange
            from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf
        except ImportError as exc:
            raise RuntimeError("Discovery requires zeroconf. Install the documented dependencies, then open QZ Devices and choose Search again. Check that QZ advertises its service on this LAN.") from exc
        backend = (AsyncZeroconf, AsyncServiceBrowser, AsyncServiceInfo, IPVersion.V4Only,
                   ServiceStateChange.Removed)
    Zc, Browser, Info, ipv4, removed = backend
    services, tasks, revisions = {}, {}, {}
    pending = set()
    semaphore = asyncio.Semaphore(4)
    zc = browser = None
    closing = False

    def publish():
        # Collapse duplicate endpoints for presentation while retaining all instance lifetimes.
        unique = {}
        for key in sorted(services):
            service = services[key]
            unique.setdefault(service.endpoints, service)
        emit(tuple(unique.values()))

    async def resolve(name, revision):
        try:
            async with semaphore:
                info = Info(SERVICE_TYPE, name)
                if not await info.async_request(zc.zeroconf, 1200):
                    services.pop(name, None)
                    publish()
                    return
                service = parse_service(name, info, info.parsed_addresses(ipv4))
                if not closing and revisions.get(name) == revision:
                    services[name] = service
                    publish()
        except Exception:
            # Resolver/parser failures affect only this instance, never a newer update.
            if not closing and revisions.get(name) == revision:
                services.pop(name, None)
                publish()

    def changed(zeroconf, service_type, name, state_change):
        if closing or service_type != SERVICE_TYPE or not isinstance(name, str) or len(name) > 255:
            return
        if name not in revisions and len(revisions) >= 32:
            return
        revision = revisions[name] = revisions.get(name, 0) + 1
        old = tasks.pop(name, None)
        if old:
            old.cancel()
        if state_change == removed:
            services.pop(name, None)
            publish()
        else:
            tasks[name] = asyncio.create_task(resolve(name, revision))
            pending.add(tasks[name])
            tasks[name].add_done_callback(pending.discard)

    try:
        zc = Zc(ip_version=ipv4)
        browser = Browser(zc.zeroconf, SERVICE_TYPE, handlers=[changed])
        deadline = asyncio.get_running_loop().time() + duration
        while asyncio.get_running_loop().time() < deadline:
            if cancel is not None and cancel.is_set():
                break
            await asyncio.sleep(0.05)
        return tuple(services.values())
    finally:
        closing = True
        try:
            if browser is not None:
                await browser.async_cancel()
        finally:
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            if zc is not None:
                await zc.async_close()
