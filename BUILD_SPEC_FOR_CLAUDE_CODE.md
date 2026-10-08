# Build Spec: TrafficMind Lite Live Dashboard

Give this whole file to Claude Code. Put it in an empty project folder together with the `traffic_controller/` folder.

## 0. What to build

A local web app that shows a live, real-time view of a physical two-lane smart traffic junction. The junction has two one-way lanes that both drive toward it: lane A comes from the bottom (heading up), lane B comes from the right (heading left). There are no other lanes. Only one lane can cross the junction at a time. The junction is an Arduino Uno connected to this laptop by USB. The Arduino already runs the traffic logic (`traffic_controller/traffic_controller.ino`, do not change its behavior). The app:

1. Reads the Arduino's serial output (JSON lines).
2. Shows everything live in a clean, advanced-looking dashboard.
3. Lets the operator trigger emergency priority, recalibrate, and set car length.
4. Logs every packet and event to SQLite and shows stats computed from that log.

It runs on this laptop only, opened at `http://127.0.0.1:8000`. One command starts everything.

## 1. Hard rules (most important)

1. **No fake data anywhere.** No mock data, no demo mode, no simulator, no replay mode, no placeholder numbers, no `Math.random()`, no generated sample series, no "example" charts. Every number, bar, chart point and light state on screen must come from a serial message received from the Arduino in this session, or from the SQLite log of real messages.
2. **No device, no numbers.** If the Arduino is not connected, the UI shows a clear "No device connected" state. Numeric fields show a dash. Charts show empty axes. Nothing pretends to work.
3. **Stale data is shown as stale.** If no telemetry has arrived for more than 1 second, grey out live values and show "Signal lost, last data X s ago". Never interpolate, extrapolate, or animate values that did not arrive.
4. **The Arduino decides, the app displays.** The app must never make its own signal decisions. Switch reasons, phases and emergency state come from the Arduino. The app may show a "rule check" panel that re-applies the Arduino's rules to the latest reported values (section 6.4), clearly labelled as such.
5. **Settings come from the device.** Min green, max green, clearance, margins, car length, stop line distances: read them from the `BOOT` and `CFG` events. Do not hardcode them in the UI.
6. Tests may use fixed sample JSON lines to test the parser. Those must live only under `tests/` and must never be importable or reachable by the running app.
7. Before finishing, search the codebase for `random`, `mock`, `fake`, `dummy`, `faker`, `sample`, `demo`, `simulate` and remove any use outside `tests/`.

## 2. Tech stack

- **Backend:** Python 3.10+, FastAPI, Uvicorn, pyserial, built-in `sqlite3`. WebSocket via FastAPI.
- **Frontend:** React + Vite + TypeScript + Tailwind CSS. Charts with **uPlot** (fast enough for 10 Hz). Icons with lucide-react.
- The frontend is built to static files and served by FastAPI. The user runs one command: `python run.py`.
- Must work on Windows (COM ports) and also macOS/Linux.

## 3. Serial protocol (exactly what the Arduino sends)

- 115200 baud, `\n` terminated lines, one JSON object per line.
- Opening the port resets the Uno. Wait for the `BOOT` event before sending commands. Ignore any partial or non-JSON line (count them as `parse_errors`).

### 3.1 Telemetry (10 per second)

```json
{"type":"tel","ms":5123,"g":"A","next":"-","ph":"GREEN","pt":1100,"mode":"AUTO",
 "why":"PRESSURE","emg":"-","emgLeft":0,
 "a":{"raw":30000,"d":503,"q":0,"n":0,"line":403,"w":0,"p":0.00,"ok":1},
 "b":{"raw":210,"d":212,"q":188,"n":3,"line":400,"w":3200,"p":4.60,"ok":1}}
```

| Field | Meaning |
|---|---|
| `ms` | Arduino uptime in ms |
| `g` | Lane that has GO: `"A"`, `"B"`, or `"X"` (all red) |
| `next` | During all red: lane that gets GO next. Otherwise `"-"` |
| `ph` | `"GREEN"` or `"CLEAR"` (all-red clearance) |
| `pt` | ms since this phase started |
| `mode` | `"AUTO"`, `"EMERGENCY"`, or `"DEGRADED"` (a sensor is faulty) |
| `why` | Reason for the most recent switch: `BOOT`, `GAP_OUT`, `PRESSURE`, `MAX_GREEN`, `EMERGENCY` |
| `emg` | Emergency lane `"A"`/`"B"`, or `"-"` |
| `emgLeft` | ms until the emergency times out (0 if none) |
| lane `raw` | Latest raw distance in mm. `-1` = reading failed. `30000` = sensor sees nothing in range (normal, means no cars) |
| lane `d` | Filtered distance in mm, `-1` if not valid. Values past the stop line are capped at `line + 100` |
| lane `q` | Queue length in mm (stop line back to the last car), `-1` if not valid |
| lane `n` | Estimated cars, `-1` if not valid |
| lane `line` | Calibrated distance from sensor to stop line in mm (`0` = not calibrated yet) |
| lane `w` | ms this lane has been waiting with cars on red (0 if not waiting) |
| lane `p` | Pressure score the Arduino is using |
| lane `ok` | `1` sensor fine, `0` sensor faulty |

Lane A uses the ultrasonic sensor, lane B uses the VL53L0X laser sensor. Show the sensor type on each lane card.

Physical LEDs: red ON = stop, red OFF = go. In the UI show the go state as a green light (that is what LED off means), and label it "GO".

### 3.2 Events

All have `"type":"evt"`, `"ms"`, and `"ev"`:

| `ev` | Extra fields |
|---|---|
| `BOOT` | `lineA, lineB, carMm, minG, maxG, clr, emgT, queueMin, waitW, margin, faultDemand, tof, cal` (`cal` is `"EEPROM"` if saved calibration was loaded, `"NONE"` if never calibrated) |
| `CFG` | same as BOOT without `cal` |
| `CAL` | `lineA, okA, lineB, okB` |
| `SWITCH` | `from, to, why, greenMs, nA, nB, pA, pB` (greenMs = how long the ending green lasted) |
| `GREEN` | `lane, why` |
| `EMG_ON` | `lane` |
| `EMG_OFF` | `lane, why` (`MANUAL` or `TIMEOUT`) |
| `FAULT` / `RECOVER` | `lane` |
| `ERR` | `msg` (`TOF_INIT_FAILED`, `CAR_OUT_OF_RANGE`, `UNKNOWN_CMD`) |

### 3.3 Acks

`{"type":"ack","ms":..,"cmd":"E:A"}` is sent for each accepted command.

### 3.4 Commands the app may send (newline terminated)

`PING`, `CFG`, `CAL`, `E:A`, `E:B`, `E:OFF`, `CAR:<10..500>`. Nothing else. Validate on the backend with a whitelist.

## 4. Backend

### 4.1 Serial manager
- Auto-detect the Uno port (USB VID `2341` or `2A03` for genuine boards, `1A86` for CH340 clones). Allow override with `--port COM5` or env `TRAFFIC_PORT`.
- Run the reader in a background thread. On disconnect, mark the link down, close the session, and retry every 2 s.
- Track link stats from real arrivals: connected yes/no, port name, packets per second (rolling 5 s), last packet age, parse errors, time since BOOT.
- Write commands through a lock. After sending, wait up to 2 s for the matching ack. Return success or timeout to the caller. For `CAL`, also wait up to 4 s for the `CAL` event and return it.

### 4.2 SQLite (`data/trafficmind.db`)
- `sessions(id, started_at, ended_at, port, boot_json)` one row per connection.
- `telemetry(id, session_id, host_ts, dev_ms, g, ph, pt, mode, why, emg, a_raw, a_d, a_q, a_n, a_e, a_w, a_p, a_ok, b_raw, b_d, b_q, b_n, b_e, b_w, b_p, b_ok)` every packet.
- `events(id, session_id, host_ts, dev_ms, ev, json)`.
- `commands(id, session_id, host_ts, cmd, result)`.
- Use WAL mode and batch inserts (flush every 0.5 s).

### 4.3 API
- `GET /api/status` link stats, latest telemetry, latest config.
- `GET /api/history?seconds=120` telemetry for the current session from the in-memory ring buffer (keep last 10 minutes).
- `GET /api/events?limit=100` latest events for the current session.
- `GET /api/stats` computed from the current session's DB rows only:
  - switches total and by reason
  - average and longest green per lane (from `SWITCH.greenMs`)
  - average and max wait per lane (the lane's `w` value in the last packet before each `GREEN` for that lane)
  - peak queue (cars and mm) per lane
  - emergencies count, faults count, session uptime
  - share of green time per lane
- `POST /api/command` body `{"cmd":"E:A"}`. Whitelisted. Returns ack result.
- `WS /ws` pushes `{"kind":"tel"|"evt"|"ack"|"link","data":{...}}` as they arrive. Push a `link` message once per second and on every change.

### 4.4 Run
- `run.py` checks the frontend is built (builds it with `npm run build` if `frontend/dist` is missing), starts Uvicorn on `127.0.0.1:8000`, and opens the browser.
- Bind to `127.0.0.1` only. No auth needed (laptop only).

## 5. Look and feel

- Dark theme. Near-black background (around `#0B0D10`), panels slightly lighter with 1px subtle borders, 12 to 16px corner radius, generous spacing.
- One accent color for UI (cool cyan or blue). Signal colors only for signals: green for GO, red for STOP, amber for all-red clearance and emergency.
- Fonts: Inter for text, JetBrains Mono for numbers. Numbers use tabular figures so they don't jitter.
- Calm, technical, control-room feel. No emoji, no heavy gradients, no glow overload, no cartoon graphics.
- Smooth transitions only between real values (bars easing to the new height over about 150 ms is fine).
- Desktop first, laid out for a 1440 x 900 screen without scrolling. Should still stack sensibly on a narrow window.

## 6. Screen layout

### 6.1 Top bar
Project name "TrafficMind Lite", link status pill (Connected COM5 / Booting / No device / Signal lost), packets per second, last packet age, current mode badge (AUTO / EMERGENCY / DEGRADED), device uptime.

### 6.2 Junction view (centre, largest panel)
- Top-down SVG of the junction: lane A enters from the bottom heading up, lane B enters from the right heading left. Draw the exit roads (up and left) as plain roads with direction arrows. Each lane is one-way toward the junction.
- Each approach lane drawn to scale using its `line` (sensor to stop line) as full length, with a sensor icon at the outer end. The queue drawn as a filled band from the stop line back toward the sensor, length `q / line` of the lane. Draw `n` car blocks inside the band.
- If `line` is 0 for a lane, show "Not calibrated" on that lane and a banner with a Calibrate button.
- A signal head at each stop line showing GO (green) or STOP (red), from `g`. During `CLEAR`, both red, with a small "ALL RED" badge and a countdown from `clr - pt`.
- Show the measured distance as a thin line from the sensor icon to the tail of the queue, labelled in cm. When `raw` is 30000 or `q` is 0, show "No queue" instead.
- If a lane `ok` is 0, hatch that lane and label "SENSOR FAULT".
- During emergency, an amber outline around the junction and a banner "Emergency priority: Lane A, 24 s left" (from `emgLeft`).

### 6.3 Lane cards (one per lane)
Lane name with direction (Lane A, from bottom / Lane B, from right), sensor type, raw mm (show "nothing in range" for 30000), filtered mm, queue cm, cars, waiting time, pressure, sensor health, stop line distance. A small sparkline of cars over the last 60 s from the ring buffer.

### 6.4 Decision panel
- Current GO lane, how long it has been green (`pt`), progress bar from 0 to `maxG` with a marker at `minG`.
- Last switch reason from `why`, in plain words (e.g. PRESSURE: "Lane B had built up more demand").
- **Rule check** (labelled "Live rule check, from latest readings"): show each Arduino rule as a row with pass/fail, using reported values and reported config:
  - Min green reached: `pt >= minG`
  - Other lane has cars
  - Green lane has no cars (GAP_OUT)
  - Pressure: `p_other > p_green + margin` with the actual numbers shown
  - Max green reached
- Pressure bars for both lanes side by side, with the margin line drawn above the green lane's bar.

### 6.5 Live chart
uPlot chart of cars in lane A and lane B over the last 120 s (toggle 60 / 120 / 300 s), with the background shaded by which lane had GO at that moment (from `g`). Data only from received telemetry.

### 6.6 Event log
Newest first: time, event, details in plain words ("Switched A to B after 9.2 s: PRESSURE (A 1.0, B 4.6)"). Colour tag per event type.

### 6.7 Controls
- **Emergency:** "Priority to Lane A", "Priority to Lane B", "Cancel emergency". Confirm before sending. Disabled when no device. Show the ack result.
- **Calibrate:** opens a dialog: "Remove all cars. Stand a flat card upright on each stop line, facing its sensor. Then press Calibrate. Remove the cards afterwards." Shows the returned `CAL` event result (stop line distances in cm, and which lanes succeeded).
- **Car length:** number input in mm, sends `CAR:<mm>`, shows the new value from the returned `CFG` event.

### 6.8 Session stats
Cards from `/api/stats`, refreshed every 5 s: switches by reason, average green per lane, average and max wait per lane, green time share, emergencies, faults.

## 7. Project structure

```
trafficmind/
  traffic_controller/traffic_controller.ino   (given, do not change behavior)
  backend/
    main.py          FastAPI app, routes, websocket
    serial_link.py   port detection, reader thread, command writer
    store.py         SQLite + ring buffer
    stats.py         stats from DB
    protocol.py      parsing and validation of lines
  frontend/          Vite + React + TS + Tailwind
  tests/             parser tests with fixed sample lines (only place they may exist)
  data/              created at runtime
  run.py
  requirements.txt
  README.md          how to run, how to find the COM port
```

## 8. Done when

1. With the Arduino unplugged, the app starts, shows "No device connected", and no numbers or chart points appear.
2. Plugging the Arduino in is detected within 3 s without restarting the app. A BOOT event shows in the log.
3. Putting cars in a lane changes its queue and car count on screen within about 0.3 s.
4. A real switch on the hardware appears in the event log with the same reason the Arduino sent, and the junction view lights match the physical LEDs.
5. Emergency buttons change the physical LEDs and the UI shows the countdown from the device.
6. Unplugging USB mid-run marks the UI as "Signal lost" within 1 s and freezes values in grey.
7. Stats only reflect the current session's logged data.
8. The search in rule 1.7 finds nothing outside `tests/`.
9. `python run.py` is the only command needed after installing requirements and `npm install`.
