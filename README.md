# TrafficMind Lite

Live dashboard for the two-lane TrafficMind Lite Arduino junction.

## Run

1. Flash `traffic_controller/traffic_controller.ino` to the Uno (Arduino IDE 2, install the "VL53L0X" library by Pololu). See `WIRING_AND_SETUP.md`.
2. Close the Arduino Serial Monitor (only one program can hold the port).
3. `pip install -r requirements.txt`
4. `cd frontend && npm install && cd ..`
5. `python run.py`

The dashboard opens at http://127.0.0.1:8000.

## Finding the COM port

The backend auto-detects the Uno by USB vendor ID. If it picks the wrong port, or you have more than one device plugged in, pass it explicitly:

```
python run.py --port COM5
```

or set `TRAFFIC_PORT=COM5`.
