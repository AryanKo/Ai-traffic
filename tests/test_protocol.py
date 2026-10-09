import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from protocol import parse_line, is_allowed_command

TEL_LINE = (
    '{"type":"tel","ms":5123,"g":"A","next":"-","ph":"GREEN","pt":1100,'
    '"mode":"AUTO","why":"PRESSURE","emg":"-","emgLeft":0,'
    '"a":{"raw":30000,"d":503,"q":0,"n":0,"line":403,"w":0,"p":0.00,"ok":1},'
    '"b":{"raw":210,"d":212,"q":188,"n":3,"line":400,"w":3200,"p":4.60,"ok":1}}'
)
EVT_LINE = '{"type":"evt","ms":10,"ev":"BOOT","lineA":0,"lineB":0,"carMm":70}'
ACK_LINE = '{"type":"ack","ms":11,"cmd":"PING"}'


def test_parses_valid_telemetry():
    obj = parse_line(TEL_LINE)
    assert obj["type"] == "tel"
    assert obj["g"] == "A"
    assert obj["a"]["raw"] == 30000


def test_parses_valid_event():
    obj = parse_line(EVT_LINE)
    assert obj["type"] == "evt"
    assert obj["ev"] == "BOOT"


def test_parses_valid_ack():
    obj = parse_line(ACK_LINE)
    assert obj["type"] == "ack"


def test_rejects_empty_line():
    assert parse_line("") is None
    assert parse_line("\n") is None


def test_rejects_truncated_json():
    assert parse_line('{"type":"tel","ms":51') is None


def test_rejects_non_json_noise():
    assert parse_line("garbled startup text from the bootloader") is None


def test_rejects_json_without_recognized_type():
    assert parse_line('{"type":"debug","msg":"hi"}') is None


def test_rejects_json_array():
    assert parse_line("[1,2,3]") is None


def test_allows_exact_whitelisted_commands():
    for cmd in ("PING", "CFG", "CAL", "E:A", "E:B", "E:OFF"):
        assert is_allowed_command(cmd)


def test_allows_car_command_in_range():
    assert is_allowed_command("CAR:70")
    assert is_allowed_command("CAR:10")
    assert is_allowed_command("CAR:500")


def test_rejects_car_command_out_of_range():
    assert not is_allowed_command("CAR:9")
    assert not is_allowed_command("CAR:501")
    assert not is_allowed_command("CAR:9999")


def test_rejects_car_command_non_numeric():
    assert not is_allowed_command("CAR:abc")
    assert not is_allowed_command("CAR:")


def test_rejects_unknown_or_near_miss_commands():
    assert not is_allowed_command("cal")
    assert not is_allowed_command("E:C")
    assert not is_allowed_command("PING; rm -rf")
    assert not is_allowed_command("")


def test_allows_led_commands():
    for cmd in ("L:00", "L:01", "L:10", "L:11"):
        assert is_allowed_command(cmd)


def test_rejects_malformed_led_commands():
    for cmd in ("L:2", "L:1", "L:111", "L:12", "L:", "l:10", "L:10\nCAL"):
        assert not is_allowed_command(cmd)
