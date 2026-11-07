"""Build native QZ workout XML in memory."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import xml.etree.ElementTree as ET

from device_capabilities import CompatibilityReport, Diagnostic, require_exportable
from workout_data import normalize_workout


MAX_ROWS = 10_000


class QzXmlExportError(ValueError):
    """The workout cannot be represented or serialized as QZ XML."""


@dataclass(frozen=True)
class QzXmlExport:
    xml: str
    compatibility: CompatibilityReport
    diagnostics: tuple[Diagnostic, ...]
    row_count: int
    timed_seconds: int
    duration_adjustment_seconds: Decimal


def _row_attributes(segment, path, repetitions, diagnostics):
    value = Decimal(str(segment["measure_value"]))
    adjustment = Decimal(0)
    seconds = 0
    if segment["measure_mode"] == "Distance":
        if segment["distance_unit"] == "m":
            value /= 1000
        attributes = {"distance": format(value.normalize(), "f")}
    else:
        exact = value * 60
        rounded = exact.to_integral_value(rounding=ROUND_HALF_UP)
        if not 1 <= rounded < 86400:
            raise QzXmlExportError(
                f"{path} ({segment['name']}): duration {exact} s is outside the "
                "QZ range 00:00:01 to 23:59:59 after rounding."
            )
        seconds = int(rounded)
        adjustment = rounded - exact
        if adjustment:
            diagnostics.append(Diagnostic(
                "warning", "duration_rounded",
                f"{segment['name']}: {exact} s rounded to {seconds} s "
                f"per occurrence ({repetitions} occurrence(s)).", path,
            ))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds_part = divmod(remainder, 60)
        attributes = {"duration": f"{hours:02}:{minutes:02}:{seconds_part:02}"}

    attributes.update(
        speed=format(Decimal(str(segment["speed_kmh"])).normalize(), "f"),
        inclination=format(Decimal(str(segment["incline_percent"])).normalize(), "f"),
        forcespeed="1",
        zonehr="0",
    )
    return attributes, seconds, adjustment


def export_workout(workout) -> QzXmlExport:
    """Export a decoded legacy or v4 workout for the Commercial LE profile.

    ProfileCompatibilityError carries diagnostics for invalid data or blockers.
    QzXmlExportError covers XML representation, row budget and serialization.
    """
    compatibility = require_exportable(workout)
    blocks = normalize_workout(workout)["blocks"]
    row_count = sum(1 if entry["type"] == "segment" else
                    len(entry["segments"]) * entry["repetitions"] for entry in blocks)
    if row_count > MAX_ROWS:
        raise QzXmlExportError(f"Workout expands to {row_count} rows. Maximum is {MAX_ROWS}.")

    root = ET.Element("rows")
    diagnostics = list(compatibility.diagnostics)
    timed_seconds = 0
    duration_adjustment = Decimal(0)
    for block_index, entry in enumerate(blocks):
        if entry["type"] == "segment":
            segments = [(f"blocks[{block_index}].segment", entry["segment"])]
            repetitions = 1
        else:
            segments = [(f"blocks[{block_index}].segments[{index}]", segment)
                        for index, segment in enumerate(entry["segments"])]
            repetitions = entry["repetitions"]
        rows = []
        for path, segment in segments:
            attributes, seconds, adjustment = _row_attributes(
                segment, path, repetitions, diagnostics
            )
            rows.append(attributes)
            timed_seconds += seconds * repetitions
            duration_adjustment += adjustment * repetitions
        for _ in range(repetitions):
            for attributes in rows:
                ET.SubElement(root, "row", attributes)

    try:
        ET.indent(root)
        xml = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
    except (ValueError, TypeError) as error:
        raise QzXmlExportError(f"Could not serialize QZ XML: {error}") from error
    return QzXmlExport(xml, compatibility, tuple(diagnostics), row_count,
                       timed_seconds, duration_adjustment)
