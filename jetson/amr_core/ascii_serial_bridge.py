"""The existing STM32 ASCII STATUS decoder used by the avoidance runtime.

Extracted without changing the parser from test_drive's ASCII bridge. The
unused binary bridge and transport stack are not part of this submission.
Compact seven-field telemetry is decoded in full_run_legacy.py.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AsciiMcuStatus:
    base_rpm: int
    sharp_adc: int
    sharp_distance_cm: int
    left_target_rpm: int
    right_target_rpm: int
    left_rpm: int
    right_rpm: int
    left_pwm: int
    right_pwm: int
    emergency: bool


def decode_ascii_status(line: str) -> AsciiMcuStatus:
    """Decode the original eleven-field STATUS, including its prefix."""
    fields = line.strip().split(",")
    if len(fields) != 11 or fields[0] != "$STATUS":
        raise ValueError("invalid STM32 STATUS line")
    try:
        values = [int(value) for value in fields[1:]]
    except ValueError as exc:
        raise ValueError("STATUS fields must be integers") from exc
    if values[1] < 0 or values[7] < 0 or values[8] < 0:
        raise ValueError("ADC and PWM fields cannot be negative")
    if values[9] not in (0, 1):
        raise ValueError("ESTOP must be 0 or 1")
    return AsciiMcuStatus(*values[:9], bool(values[9]))
