# TrafficMind Lite

Live dashboard for the two-lane TrafficMind Lite Arduino junction, plus a phone
remote that switches the junction's two LEDs over Wi-Fi.

## How the pieces fit

```
 Phone (browser)  ──Wi-Fi / hotspot──▶  Laptop: python run.py  ──USB cable──▶  Arduino Uno ──▶ LED A, LED B
 /remote page                            serves the dashboard      L:<a><b>        sends the LED state back
                                         and the phone page                        10 times a second
```

- The phone never talks to the Arduino directly. It talks to the laptop over Wi-Fi.
  The laptop forwards each tap over USB and reads back the LED state the Arduino reports.
- The phone page asks the laptop for that reported state every 0.4 s, so the
  switches always show what the LEDs are actually doing.
- You never choose a COM port. The laptop scans the USB ports every 2 s and connects
  to the first one that is an Arduino (genuine Uno, or a clone with a CH340, CP210x or
  FTDI chip). Plugging the cable in after starting the app is fine.
- The dashboard's top bar shows `Connected COMx` once the Arduino is found.
- The dashboard's top bar also says the LEDs are manually controlled, the sensors are
  offline, and the traffic shown is a simulation.

## One-time setup

You need [Python 3.11+](https://www.python.org/downloads/) (tick "Add Python to PATH"
when installing), [Node.js 20+](https://nodejs.org/) and
[Arduino IDE 2](https://www.arduino.cc/en/software).

1. **Flash the Arduino**
   1. Open `traffic_controller/traffic_controller.ino` in Arduino IDE 2.
   2. Library Manager (left sidebar) → search **VL53L0X** → install the one **by Pololu**.
   3. Tools → Board → **Arduino Uno**. Tools → Port → the port that appears when the Uno is plugged in.
   4. Click **Upload** and wait for "Done uploading".
   5. **Close the Arduino IDE** (or at least its Serial Monitor). Only one program can use the USB port at a time.
2. **Install the laptop app.** Open a terminal in this folder and run:
   ```
   pip install -r requirements.txt
   cd frontend
   npm install
   cd ..
   ```

## Every time you run it

1. Turn on your phone's **hotspot** and connect the laptop to it.
2. Plug the Arduino into the laptop with the USB cable.
3. In a terminal in this folder, run:
   ```
   python run.py
   ```
   It prints something like:
   ```
   Dashboard: http://127.0.0.1:8000
   Phone remote (open on your phone): http://172.20.10.4:8000/remote
     other network adapters, only if the one above fails: http://192.168.56.1:8000/remote
   ```
   The dashboard opens in the laptop's browser on its own.
4. **First run only:** Windows asks whether Python may use the network. Tick
   **Private networks** and click **Allow**.
5. On the phone, open the **Phone remote (open on your phone)** address exactly as printed (it starts with
   `http://`, not `https://`).
6. Wait until the badge in the top-right of the phone page reads **Connected**. Then tap:
   - **LED A** / **LED B**: turns that LED on or off (red glow = on).
   - **Both on** / **Both off**: sets both at once.

To stop, press `Ctrl+C` in the terminal.

## If something doesn't work

| What you see | What to do |
|---|---|
| Phone page won't load | The laptop and phone must be on the same hotspot. Use the exact address `run.py` printed, starting with `http://`. If it still fails, open Windows Settings → Network & internet → Wi-Fi → your hotspot → set **Network profile type** to **Private**, then try again. |
| Phone page won't load at the first address | Try the "other network adapters" addresses one by one. Addresses like `192.168.56.x` belong to VirtualBox and never work from the phone. |
| Phone badge says **No device** | The Arduino isn't connected. Check the USB cable and close the Arduino IDE / Serial Monitor. The app reconnects within 2 s, so there's no need to restart it. |
| Dashboard says **No device** with the Arduino plugged in | Another program has the port (usually the Arduino Serial Monitor), or the board has an unusual USB chip. Name the port yourself: `python run.py --port COM5` (find the number in Arduino IDE → Tools → Port, or Windows Device Manager → Ports). |
| Phone says **Connected** but the switches are greyed out and show "—" | The Arduino is still running the old firmware. Flash it again (setup step 1). |
| Tap shows "Not applied (…)" | The Arduino didn't confirm the change within 2 s. Check the USB cable and tap again. |
| `pip` or `npm` "not recognized" | Python or Node isn't installed or isn't on PATH. Reinstall it, then open a new terminal. |

## Notes

- Anyone connected to your hotspot can open the remote page, so keep the hotspot password to yourself.
- The Uno restarts whenever the laptop app connects to it. The app puts the LEDs
  back to the state they had before the restart.
- To go back to the automatic, sensor-driven controller, set `BOOT_DIRECT = false`
  near the top of `traffic_controller.ino` and flash it again.
- Wiring is in `WIRING_AND_SETUP.md`.

## Tests

```
python -m pytest tests
cd frontend && npx vitest run
```
