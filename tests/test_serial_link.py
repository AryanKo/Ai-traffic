import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from serial_link import SerialLink, find_port, ALLOWED_VIDS

TEL_LINE = (
    '{"type":"tel","ms":1,"g":"A","ph":"GREEN","pt":1,"mode":"AUTO","why":"BOOT","emg":"-",'
    '"a":{"raw":1,"d":1,"q":0,"n":0,"line":1,"w":0,"p":0.0,"ok":1},'
    '"b":{"raw":1,"d":1,"q":0,"n":0,"line":1,"w":0,"p":0.0,"ok":1}}'
)
BOOT_LINE = '{"type":"evt","ms":1,"ev":"BOOT","lineA":0,"lineB":0}'


class FakePort:
    vid = 0x2341
    device = "COM9"


class WrongVidPort:
    vid = 0x9999
    device = "COM3"


def test_find_port_accepts_known_vids(monkeypatch):
    import serial_link
    monkeypatch.setattr(serial_link.list_ports, "comports", lambda: [WrongVidPort(), FakePort()])
    assert find_port() == "COM9"


def test_find_port_returns_none_when_nothing_matches(monkeypatch):
    import serial_link
    monkeypatch.setattr(serial_link.list_ports, "comports", lambda: [WrongVidPort()])
    assert find_port() is None


def test_handle_line_delivers_parsed_message_to_callback():
    received = []
    link = SerialLink(on_message=received.append)
    link._handle_line(TEL_LINE)
    assert len(received) == 1
    assert received[0]["type"] == "tel"
    assert link.last_packet_at is not None


def test_handle_line_counts_parse_errors_without_crashing():
    received = []
    link = SerialLink(on_message=received.append)
    link._handle_line("not json at all")
    link._handle_line("")
    assert link.parse_errors == 2
    assert received == []


def test_handle_line_tracks_boot_time():
    link = SerialLink(on_message=lambda obj: None)
    assert link.boot_at is None
    link._handle_line(BOOT_LINE)
    assert link.boot_at is not None


def test_pps_counts_only_last_5_seconds():
    link = SerialLink(on_message=lambda obj: None)
    now = time.time()
    link._arrivals = [now - 10, now - 1, now]
    assert link.pps() == 2 / 5.0


def test_send_command_without_connection_returns_not_connected():
    link = SerialLink(on_message=lambda obj: None)
    result = link.send_command("PING")
    assert result == {"ok": False, "error": "not_connected"}
