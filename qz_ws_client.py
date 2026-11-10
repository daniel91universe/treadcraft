"""Connect to a local QZ instance and confirm a save-program request."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import ipaddress
import json
import math
import re
import socket
from urllib.parse import urlsplit
from uuid import uuid4

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException


class QzConnectionError(ValueError):
    """The WebSocket connection could not be established."""


class QzIdentityError(QzConnectionError):
    """The service did not return a recognizable QZ identity response."""


class QzSaveUncertainError(RuntimeError):
    """The program may have been saved, but QZ did not confirm it."""

    def __init__(self, name, reason):
        self.name = name
        super().__init__(f"Save not confirmed for {name}: {reason}. Check QZ before retrying.")


@dataclass(frozen=True)
class QzSaveReceipt:
    name: str
    row_count: int


_LOCAL_NETWORKS = tuple(map(ipaddress.ip_network, (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",
    "127.0.0.0/8", "fc00::/7", "::1/128",
)))


def _endpoint(address):
    address = address.strip()
    if "://" not in address:
        address = "ws://" + address
    try:
        url = urlsplit(address)
        host = ipaddress.ip_address(url.hostname or "")
        port = url.port
    except ValueError as exc:
        raise QzConnectionError("Enter a local QZ IP address and port.") from exc
    floating = url.scheme == "http" and url.path == "/floating/floating.htm"
    if (not port or url.username is not None or url.query or url.fragment
            or not any(host in network for network in _LOCAL_NETWORKS)
            or not (floating or url.scheme == "ws" and url.path in ("", "/"))):
        raise QzConnectionError("Use a local ws://IP:port/ or the QZ floating-window URL.")
    literal = f"[{host}]" if host.version == 6 else str(host)
    return f"ws://{literal}:{port}/", host, port


@asynccontextmanager
async def _connection(address, timeout):
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be positive and finite.")
    uri, host, port = _endpoint(address)
    family = socket.AF_INET6 if host.version == 6 else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setblocking(False)
        try:
            async with asyncio.timeout(timeout):
                await asyncio.get_running_loop().sock_connect(sock, (str(host), port))
                # A preconnected socket keeps redirects from changing the destination.
                connection = await connect(uri, sock=sock, proxy=None, compression=None,
                                           ping_interval=None, close_timeout=1)
        except (OSError, WebSocketException, ValueError) as exc:
            raise QzConnectionError(f"Could not connect to QZ: {exc}") from exc
        try:
            yield connection
        finally:
            await connection.close()
    finally:
        sock.close()


async def check_connection(address, *, timeout=5):
    """Check the WebSocket handshake without sending a QZ command."""
    async with _connection(address, timeout):
        return


def normalize_endpoint(address):
    return _endpoint(address)[0]


async def verify_qz(address, *, timeout=5):
    """Verify the QZ workout editor protocol without writing to the device."""
    endpoint = normalize_endpoint(address)
    try:
        async with asyncio.timeout(timeout):
            async with _connection(endpoint, timeout) as ws:
                await ws.send('{"msg":"workouteditor_env"}')
                while True:
                    reply = json.loads(await ws.recv())
                    if isinstance(reply, dict) and reply.get("msg") == "workout":
                        continue
                    if isinstance(reply, dict) and reply.get("msg") == "R_workouteditor_env":
                        content = reply.get("content")
                        if (isinstance(content, dict) and type(content.get("miles")) is bool
                                and isinstance(content.get("device"), str)
                                and content["device"].strip()):
                            return endpoint
                    raise QzIdentityError("Response not recognized as QZ.")
    except TimeoutError as exc:
        raise QzConnectionError("Timed out verifying QZ.") from exc
    except QzConnectionError as exc:
        if isinstance(exc.__cause__, ConnectionRefusedError):
            raise QzConnectionError("QZ connection refused.") from exc
        if isinstance(exc.__cause__, TimeoutError):
            raise QzConnectionError("Timed out connecting to QZ.") from exc
        raise
    except (OSError, WebSocketException, ValueError) as exc:
        raise QzIdentityError("QZ did not return a valid identity response.") from exc


async def save_training_program(address, payload, *, timeout=5):
    """Send an adapter payload once and return only a matching save receipt."""
    content = payload["content"]
    rows = content["list"]
    if payload["msg"] != "savetrainingprogram" or not isinstance(rows, list) or not rows:
        raise ValueError("Expected a non-empty QZ save-program payload.")
    title = re.sub(r"[^A-Za-z0-9_-]+", "-", content["name"]).strip("-_")[:48]
    name = f"{title or 'TreadCraft'}-{uuid4().hex}"
    message = json.dumps({"msg": "savetrainingprogram",
                          "content": {"name": name, "list": rows}}, allow_nan=False)

    async with _connection(address, timeout) as ws:
        try:
            async with asyncio.timeout(timeout):
                await ws.send(message)
                while True:
                    reply = json.loads(await ws.recv())
                    if not isinstance(reply, dict) or not isinstance(reply.get("msg"), str):
                        raise ValueError("malformed QZ response")
                    if reply["msg"] == "R_savetrainingprogram":
                        break
        except TimeoutError as exc:
            raise QzSaveUncertainError(name, "timed out waiting for confirmation") from exc
        except (OSError, WebSocketException, ValueError) as exc:
            raise QzSaveUncertainError(name, "connection lost or invalid response") from exc

        result = reply.get("content")
        if (not isinstance(result, dict) or result.get("name") != name
                or type(result.get("list")) is not int or result["list"] != len(rows)):
            raise QzSaveUncertainError(name, "response name or row count did not match")
        return QzSaveReceipt(name, len(rows))
