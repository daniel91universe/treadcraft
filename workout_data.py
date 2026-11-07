"""Pure validation and calculations for the existing workout JSON formats."""

import math


SEGMENT_FIELDS = {
    "name", "measure_mode", "measure_value", "distance_unit", "duration_min",
    "speed_kmh", "incline_percent", "estimated_distance_km",
}
WORKOUT_FIELDS = {
    "format_version", "workout_name", "blocks", "segments",
    "total_duration_min", "estimated_distance_km",
}


def _object(value, fields, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    unknown = set(value) - fields
    if unknown:
        raise ValueError(f"{label} contains unsupported fields: "
                         + ", ".join(sorted(map(str, unknown))) + ".")
    return value


def _required(value, key, label):
    if key not in value:
        raise ValueError(f"{label} is missing '{key}'.")
    return value[key]


def _name(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value.strip()


def _number(value, label):
    # Numeric strings remain readable for files accepted by earlier versions.
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{label} must be a finite number.")
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise ValueError(f"{label} must be a finite number.") from None
    if not math.isfinite(result):
        raise ValueError(f"{label} must be a finite number.")
    return result


def _positive(value, label):
    result = _number(value, label)
    if result <= 0:
        raise ValueError(f"{label} must be positive.")
    return result


def _derived(value, label):
    result = _positive(value, label)
    result = round(result, 4)
    if result == 0:
        raise ValueError(f"{label} is too small for the workout file precision.")
    return result


def normalize_block_values(name, repetitions):
    """Validate block input without truncating fractional repetitions."""
    name = _name(name, "Block name")
    if isinstance(repetitions, str):
        try:
            repetitions = int(repetitions)
        except ValueError:
            raise ValueError("Repetitions must be a whole number.") from None
    if (isinstance(repetitions, bool)
            or not isinstance(repetitions, (int, float))
            or not 1 <= repetitions <= 100
            or int(repetitions) != repetitions):
        raise ValueError("Repetitions must be a whole number between 1 and 100.")
    return {"name": name, "repetitions": int(repetitions)}


def normalize_segment(segment):
    """Read legacy time segments and current time/distance segments."""
    segment = _object(segment, SEGMENT_FIELDS, "Segment")
    name = _name(_required(segment, "name", "Segment"), "Segment name")
    speed = _number(_required(segment, "speed_kmh", "Segment"), "Speed")
    incline = _number(_required(segment, "incline_percent", "Segment"), "Incline")
    if not 0 < speed <= 20:
        raise ValueError("Speed must be greater than 0 and no more than 20 km/h.")
    if not -3 <= incline <= 12:
        raise ValueError("Incline must be between -3% and 12%.")

    mode = segment.get("measure_mode", "Time")
    if mode not in ("Time", "Distance"):
        raise ValueError("Segment measure_mode must be Time or Distance.")
    unit = segment.get("distance_unit", "km")
    if unit not in ("km", "m"):
        raise ValueError("Distance unit must be km or m.")

    # Cached estimates are recalculated, but invalid supplied values are errors.
    for key in ("duration_min", "estimated_distance_km"):
        if key in segment and _number(segment[key], key) < 0:
            raise ValueError(f"{key} cannot be negative.")
    if "measure_value" in segment:
        _positive(segment["measure_value"], "Duration/distance")

    if mode == "Distance":
        if "measure_value" in segment:
            raw_value = _positive(segment["measure_value"], "Segment distance")
            distance_km = raw_value / 1000 if unit == "m" else raw_value
        else:
            # This fallback is already in km, regardless of the chosen UI unit.
            distance_km = _positive(
                _required(segment, "estimated_distance_km", "Distance segment"),
                "Segment distance",
            )
            raw_value = distance_km * 1000 if unit == "m" else distance_km
        duration_min = distance_km / speed * 60
    else:
        # Files without a mode historically used duration_min as the authority.
        if "measure_mode" not in segment or "measure_value" not in segment:
            value = _required(segment, "duration_min", "Time segment")
        else:
            value = segment["measure_value"]
        raw_value = _positive(value, "Segment duration")
        duration_min = raw_value
        distance_km = speed * duration_min / 60
        unit = "km"

    return {
        "name": name,
        "measure_mode": mode,
        "measure_value": _positive(raw_value, "Duration/distance"),
        "distance_unit": unit,
        "duration_min": _derived(duration_min, "Segment duration"),
        "speed_kmh": speed,
        "incline_percent": incline,
        "estimated_distance_km": _derived(distance_km, "Segment distance"),
    }


def calculate_totals(blocks):
    """Calculate totals from normalized entries, using existing rounding rules."""
    duration = 0.0
    distance = 0.0
    for entry in blocks:
        if entry["type"] == "segment":
            segments = [entry["segment"]]
            repetitions = 1
        else:
            segments = entry["segments"]
            repetitions = entry["repetitions"]
        for segment in segments:
            duration += segment["duration_min"] * repetitions
            distance += segment["estimated_distance_km"] * repetitions
    return (_number(duration, "Total duration"),
            _number(distance, "Total distance"))


def normalize_workout(workout):
    """Validate completely before the caller replaces its current UI state.

    Versions 1-4 and unversioned historical files are accepted. Unknown fields
    and future versions are rejected rather than silently lost on saving.
    Empty blocks/workouts remain readable, as in the previous block format.
    """
    workout = _object(workout, WORKOUT_FIELDS, "Workout")
    if "format_version" in workout:
        version = workout["format_version"]
        if type(version) is not int or not 1 <= version <= 4:
            raise ValueError("Unsupported workout format_version; expected 1 to 4.")
    name = workout.get("workout_name", "My Running Workout")
    if not isinstance(name, str):
        raise ValueError("Workout name must be a string.")
    for key in ("total_duration_min", "estimated_distance_km"):
        if key in workout and _number(workout[key], key) < 0:
            raise ValueError(f"{key} cannot be negative.")
    if "blocks" in workout and "segments" in workout:
        raise ValueError("Workout cannot contain both blocks and segments.")

    blocks = []
    if "blocks" in workout:
        if not isinstance(workout["blocks"], list):
            raise ValueError("Workout blocks must be a list.")
        for index, entry in enumerate(workout["blocks"], 1):
            try:
                if not isinstance(entry, dict):
                    raise ValueError("Entry must be an object.")
                kind = entry.get("type", "block")
                if kind == "segment":
                    _object(entry, {"type", "segment"}, "Standalone segment")
                    blocks.append({
                        "type": "segment",
                        "segment": normalize_segment(_required(entry, "segment", "Entry")),
                    })
                elif kind == "block":
                    _object(entry, {"type", "name", "repetitions", "segments"}, "Block")
                    block = normalize_block_values(
                        _required(entry, "name", "Block"),
                        _required(entry, "repetitions", "Block"),
                    )
                    segments = _required(entry, "segments", "Block")
                    if not isinstance(segments, list):
                        raise ValueError("Block segments must be a list.")
                    block.update(type="block", segments=_segments(segments))
                    blocks.append(block)
                else:
                    raise ValueError("Entry type must be block or segment.")
            except ValueError as error:
                raise ValueError(f"Workout entry {index}: {error}") from None
    elif "segments" in workout:
        segments = workout["segments"]
        if not isinstance(segments, list) or not segments:
            raise ValueError("Workout segments must be a non-empty list.")
        blocks.append({"type": "block", "name": "Imported Workout",
                       "repetitions": 1, "segments": _segments(segments)})
    else:
        raise ValueError("Unrecognized workout file format.")

    duration, distance = calculate_totals(blocks)
    return {
        "format_version": 4,
        "workout_name": name,
        "blocks": blocks,
        "total_duration_min": round(duration, 4),
        "estimated_distance_km": round(distance, 4),
    }


def _segments(segments):
    result = []
    for index, segment in enumerate(segments, 1):
        try:
            result.append(normalize_segment(segment))
        except ValueError as error:
            raise ValueError(f"Segment {index}: {error}") from None
    return result
