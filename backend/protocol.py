"""Parsing and validation of lines exchanged with the Arduino."""
import json
import re
from typing import Optional

_WHITELIST_EXACT = {"PING", "CFG", "CAL", "E:A", "E:B", "E:OFF"}
_RECOGNIZED_TYPES = {"tel", "evt", "ack"}
_LED_CMD = re.compile(r"L:[01][01]")


def parse_line(line: str) -> Optional[dict]:
    """Parse one line of serial output into a dict, or None if it is not
    a recognized, well-formed JSON message. Malformed or partial lines
    (power blips, a line split across two reads) must return None rather
    than raise, so the caller can count them as parse errors."""
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    if obj.get("type") not in _RECOGNIZED_TYPES:
        return None
    return obj


def is_allowed_command(cmd: str) -> bool:
    """Whitelist for commands the app may send to the device."""
    if cmd in _WHITELIST_EXACT:
        return True
    if _LED_CMD.fullmatch(cmd):
        return True
    if cmd.startswith("CAR:"):
        value = cmd[4:]
        if not value.isdigit():
            return False
        n = int(value)
        return 10 <= n <= 500
    return False
