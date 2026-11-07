"""Device compatibility is a separate, read-only layer over workout data.

Evidence is pinned to the audit snapshot, not to an arbitrary installed QZ
release. No capability in the initial Commercial LE profile is hardware-tested.
"""

from dataclasses import dataclass
from enum import Enum

from workout_data import normalize_workout


class Evidence(str, Enum):
    PRELIMINARY = "IPOTESI"
    SOURCE_CONFIRMED = "CONFERMATO_NEL_CODICE"
    UNSUPPORTED = "NON_SUPPORTATO_CON_EVIDENZA"
    HARDWARE_REQUIRED = "RICHIEDE_HARDWARE"
    UNKNOWN = "NON_DETERMINATO"


@dataclass(frozen=True)
class Limit:
    value: float | None
    unit: str
    evidence: Evidence
    reference: str


@dataclass(frozen=True)
class Capability:
    key: str
    label: str
    qz_evidence: Evidence
    hardware_evidence: Evidence
    note: str
    references: tuple[str, ...]


@dataclass(frozen=True)
class DeviceProfile:
    key: str
    name: str
    model_candidates: tuple[str, ...]
    identification_verified: bool
    qz_commit: str
    qz_driver: str
    speed_min: Limit
    speed_max: Limit
    incline_min: Limit
    incline_max: Limit
    speed_step: Limit
    incline_step: Limit
    driver_speed_max: Limit
    driver_incline_max: Limit
    driver_speed_step: Limit
    capabilities: tuple[Capability, ...]

    def capability(self, key):
        return next((item for item in self.capabilities if item.key == key), None)


QZ_COMMIT = "89ebf525e87fe3f334c437e656417e1f818b9e27"
DRIVER = "src/devices/proformtreadmill/proformtreadmill.cpp"
SOURCE = f"https://github.com/cagnulein/qdomyos-zwift/blob/{QZ_COMMIT}/"
AUDIT = "COMMERCIAL_LE_COMPATIBILITY.md"


def _capability(key, label, status, note, *references):
    return Capability(key, label, status, Evidence.HARDWARE_REQUIRED, note, references)


COMMERCIAL_LE = DeviceProfile(
    key="nordictrack_commercial_le",
    name="NordicTrack Commercial LE",
    model_candidates=("NTL13125_0", "NTL13125-INT.0"),
    identification_verified=False,
    qz_commit=QZ_COMMIT,
    qz_driver="nordictrack_treadmill_commercial_le",
    # These are project assumptions, not measured or certified machine limits.
    speed_min=Limit(None, "km/h", Evidence.UNKNOWN, AUDIT),
    speed_max=Limit(20.0, "km/h", Evidence.PRELIMINARY, AUDIT),
    incline_min=Limit(-3.0, "%", Evidence.PRELIMINARY, AUDIT),
    incline_max=Limit(12.0, "%", Evidence.PRELIMINARY, AUDIT),
    speed_step=Limit(None, "km/h", Evidence.UNKNOWN, AUDIT),
    incline_step=Limit(None, "%", Evidence.UNKNOWN, AUDIT),
    # Driver acceptance/advertised increments are distinct from hardware limits.
    driver_speed_max=Limit(22.0, "km/h", Evidence.SOURCE_CONFIRMED,
                           SOURCE + DRIVER + "#L392-L397"),
    driver_incline_max=Limit(15.0, "%", Evidence.SOURCE_CONFIRMED,
                             SOURCE + DRIVER + "#L382-L390"),
    driver_speed_step=Limit(0.1, "km/h", Evidence.SOURCE_CONFIRMED,
                            SOURCE + "src/devices/proformtreadmill/proformtreadmill.h#L40"),
    capabilities=(
        _capability("speed", "Automatic speed", Evidence.SOURCE_CONFIRMED,
                    "Implemented in QZ; requires forcespeed and automatic control enabled.",
                    SOURCE + DRIVER + "#L392-L397", SOURCE + "src/devices/treadmill.cpp#L95-L96"),
        _capability("incline", "Automatic incline", Evidence.SOURCE_CONFIRMED,
                    "Non-negative requests implemented; limits and response need hardware tests.",
                    SOURCE + DRIVER + "#L382-L390"),
        _capability("decline", "Automatic decline", Evidence.UNSUPPORTED,
                    "The audited Commercial LE driver replaces negative incline with zero. "
                    "The workout must not be silently flattened to a level segment.",
                    SOURCE + DRIVER + "#L383-L384"),
        _capability("fan", "Integrated fan / AutoBreeze", Evidence.UNSUPPORTED,
                    "No integrated-fan command consumer was found in the audited LE driver; "
                    "a QZ fan target does not prove AutoBreeze control.",
                    AUDIT, SOURCE + "src/devices/bluetoothdevice.cpp#L161-L177"),
        _capability("start", "Remote belt start", Evidence.UNKNOWN,
                    "The LE branch emits tapeStarted, without an observed physical start write.",
                    SOURCE + DRIVER + "#L399-L402"),
        _capability("stop", "Remote belt stop", Evidence.UNSUPPORTED,
                    "The audited LE requestStop branch does not write a stop command. "
                    "Workout completion must not be treated as a guaranteed belt stop.",
                    SOURCE + DRIVER + "#L404-L407"),
        _capability("pause", "Remote belt pause", Evidence.UNSUPPORTED,
                    "A software wait/pause does not establish a physical belt stop in this driver.",
                    SOURCE + DRIVER + "#L404-L407", AUDIT),
        _capability("heart_rate", "Heart-rate control", Evidence.SOURCE_CONFIRMED,
                    "QZ control logic exists; sensor, actuator mode and signal loss need testing. "
                    "The current desktop JSON does not store heart-rate targets.",
                    SOURCE + "src/homeform.cpp#L8501-L8788",
                    SOURCE + "src/homeform.cpp#L12291-L12342"),
        _capability("telemetry", "Speed/incline telemetry", Evidence.SOURCE_CONFIRMED,
                    "Notification decoding exists; readings on the exact unit remain unverified.",
                    SOURCE + DRIVER + "#L4293-L4308"),
    ),
)


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    path: str = "workout"


@dataclass(frozen=True)
class CompatibilityReport:
    profile: DeviceProfile
    diagnostics: tuple[Diagnostic, ...]

    @property
    def has_blockers(self):
        return any(item.severity == "error" for item in self.diagnostics)

    def text(self):
        heading = ("Blocked for this QZ/device profile." if self.has_blockers else
                   "No blocking incompatibilities found in the current workout.")
        lines = [self.profile.name, heading,
                 "This check is not a hardware compatibility certification.",
                 f"QZ audit snapshot: {self.profile.qz_commit}", ""]
        lines.extend(f"{item.severity.upper()} [{item.path}]: {item.message}"
                     for item in self.diagnostics)
        return "\n".join(lines)


class ProfileCompatibilityError(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__(report.text())


def assess_workout(workout, profile=COMMERCIAL_LE, *, required_features=()):
    """Inspect a legacy/current JSON object without mutating it or applying clamps.

    required_features declares extra driver requirements (e.g. fan or stop) for
    callers of the future exporter. It does not extend the workout JSON schema.
    No blockers only means no known software incompatibility, never hardware
    verification. The current author-data validation remains device-independent.
    """
    def display(limit):
        return "unknown" if limit.value is None else f"{limit.value:g}"

    issues = [
        Diagnostic("warning", "preliminary_limits",
                   f"Profile project bounds: speed {display(profile.speed_min)} to "
                   f"{display(profile.speed_max)} km/h; incline {display(profile.incline_min)} "
                   f"to {display(profile.incline_max)}%. "
                   "The Commercial LE bounds are preliminary; physical increments are unknown."),
        Diagnostic("warning", "hardware_unverified",
                   "Exact model, firmware, QZ build and hardware behavior have not been verified."),
        Diagnostic("warning", "control_configuration",
                   "Automatic speed/incline requires appropriate QZ settings; "
                   "gains, offsets and heart-rate/power control can change requests."),
    ]
    # Report start/stop limitations even when not explicitly required by a file.
    for key in ("start", "stop", "fan"):
        capability = profile.capability(key)
        if capability is not None:
            issues.append(Diagnostic("warning", f"{key}_limitation", capability.note))

    try:
        normalized = normalize_workout(workout)
    except ValueError as error:
        issues.append(Diagnostic("error", "invalid_workout", str(error)))
        return CompatibilityReport(profile, tuple(issues))

    if not any(entry["type"] == "segment" or entry["segments"]
               for entry in normalized["blocks"]):
        issues.append(Diagnostic("error", "empty_workout", "The workout contains no segments."))

    requirements = set(required_features) | {"speed", "incline"}
    for key in sorted(requirements):
        capability = profile.capability(key)
        if capability is None:
            issues.append(Diagnostic("error", "unknown_capability",
                                     f"Unknown capability requested: {key}."))
        elif capability.qz_evidence != Evidence.SOURCE_CONFIRMED:
            issues.append(Diagnostic("error", f"{key}_unavailable",
                                     f"{capability.label}: {capability.note}"))
        else:
            issues.append(Diagnostic("warning", f"{key}_hardware_unverified",
                                     f"{capability.label}: confirmed in QZ source only; "
                                     "requires verification on the exact treadmill."))

    for block_index, entry in enumerate(normalized["blocks"]):
        if entry["type"] == "segment":
            segments = [(f"blocks[{block_index}].segment", entry["segment"])]
        else:
            segments = [(f"blocks[{block_index}].segments[{index}]", segment)
                        for index, segment in enumerate(entry["segments"])]
        for path, segment in segments:
            speed, incline = segment["speed_kmh"], segment["incline_percent"]
            for value, low, high, label in (
                (speed, profile.speed_min, profile.speed_max, "Speed"),
                (incline, profile.incline_min, profile.incline_max, "Incline"),
            ):
                if ((low.value is not None and value < low.value)
                        or (high.value is not None and value > high.value)):
                    issues.append(Diagnostic("error", "profile_limit",
                                             f"{segment['name']}: {label} exceeds the profile "
                                             "project limits; no automatic clamp was applied.", path))
            if incline < 0:
                capability = profile.capability("decline")
                if capability is None or capability.qz_evidence != Evidence.SOURCE_CONFIRMED:
                    note = capability.note if capability else "No decline capability defined."
                    issues.append(Diagnostic("error", "decline_unavailable",
                                             f"{segment['name']}: {note}", path))
    return CompatibilityReport(profile, tuple(issues))


def require_exportable(workout, profile=COMMERCIAL_LE, *, required_features=()):
    """Gate for the future exporter; never asserts hardware readiness."""
    report = assess_workout(workout, profile, required_features=required_features)
    if report.has_blockers:
        raise ProfileCompatibilityError(report)
    return report
