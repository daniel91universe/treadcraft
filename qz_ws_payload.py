"""Adapt the existing QZ XML export to a save-program JSON payload."""

import re
import xml.etree.ElementTree as ET

from qz_xml_export import QzXmlExportError, export_workout


def build_save_payload(workout, *, name):
    """Return a JSON-serializable QZ command with an explicit program name."""
    if not isinstance(name, str) or not name.strip():
        raise QzXmlExportError("A QZ program name is required.")

    result = export_workout(workout)
    rows = []
    for index, element in enumerate(ET.fromstring(result.xml), start=1):
        attributes = element.attrib
        duration = attributes.get("duration", "")
        if (not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]", duration)
                or duration == "00:00:00"):
            raise QzXmlExportError(
                f"QZ row {index} needs a duration from 00:00:01 to 23:59:59 "
                "for WebSocket transfer, including distance segments. "
                "You can still export the workout as XML."
            )
        row = {
            "duration": duration,
            "speed": float(attributes["speed"]),
            "inclination": float(attributes["inclination"]),
            "forcespeed": attributes["forcespeed"] == "1",
            "zoneHR": int(attributes["zonehr"]),
        }
        if "distance" in attributes:
            row["distance"] = float(attributes["distance"])
        rows.append(row)

    return {"msg": "savetrainingprogram",
            "content": {"name": name.strip(), "list": rows}}
