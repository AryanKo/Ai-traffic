# TrafficMind Lite: Wiring and Setup

Two one-way lanes drive toward one junction. Only one lane can cross at a time. Each lane has one distance sensor and one red LED.

- Lane A (comes from the bottom): HC-SR04 ultrasonic sensor + red LED A
- Lane B (comes from the right): VL53L0X laser distance sensor + red LED B
- Red LED ON means STOP. Red LED OFF means GO.
- When both LEDs are on, the junction is in "all red" clearance between switches.

## 1. Parts

| Part | Qty |
|---|---|
| Arduino Uno + USB cable | 1 |
| HC-SR04 ultrasonic sensor | 1 |
| VL53L0X sensor module (GY-530 / "VL53L0X V2") | 1 |
| Red LED | 2 |
| 220 ohm resistor (anything from 150 to 330 ohm is fine) | 2 |
| Breadboard + jumper wires | 1 set |
| Toy cars or small blocks with flat backs | 6 to 10 |
| Cardboard for lane edges, plus one flat card for calibration | some |

## 2. Pin table

| Component pin | Arduino pin |
|---|---|
| HC-SR04 VCC | 5V |
| HC-SR04 GND | GND |
| HC-SR04 TRIG | D9 |
| HC-SR04 ECHO | D10 |
| VL53L0X VIN (or VCC) | 5V (see note) |
| VL53L0X GND | GND |
| VL53L0X SDA | A4 |
| VL53L0X SCL | A5 |
| VL53L0X XSHUT, GPIO1 | leave unconnected |
| Red LED A long leg, through 220 ohm resistor | D5 |
| Red LED A short leg | GND |
| Red LED B long leg, through 220 ohm resistor | D6 |
| Red LED B short leg | GND |

**VL53L0X power note:** most blue/purple GY-530 boards have a regulator on them and work on 5V. If your board is a bare one marked "2.8V" or "3.3V only", connect VIN to the Uno's **3.3V** pin instead. Everything else stays the same.

## 3. Step by step

1. Unplug the Uno from USB while wiring.
2. Run a wire from Uno **5V** to the breadboard **+** rail, and from Uno **GND** to the **-** rail.
3. **HC-SR04:** VCC to + rail, GND to - rail, TRIG to D9, ECHO to D10.
4. **VL53L0X:** VIN to + rail (or 3.3V, see note), GND to - rail, SDA to A4, SCL to A5.
5. **LED A:** put the LED in the breadboard. Connect D5 to one end of a 220 ohm resistor, the other end of the resistor to the LED's long leg. Short leg to the - rail.
6. **LED B:** same as LED A, but from D6.
7. Check every GND goes to the same - rail. A missing shared ground is the most common fault.

```
 Uno 5V  ----+---- HC-SR04 VCC
             +---- VL53L0X VIN
 Uno GND ----+---- HC-SR04 GND, VL53L0X GND, LED A short leg, LED B short leg
 D9  ---------- HC-SR04 TRIG
 D10 ---------- HC-SR04 ECHO
 A4  ---------- VL53L0X SDA
 A5  ---------- VL53L0X SCL
 D5  --[220R]-- LED A long leg
 D6  --[220R]-- LED B long leg
```

## 4. Building the model junction

This matches your drawing. Lane A comes up from the bottom, lane B comes in from the right. Both drive toward the junction only.

```
                     |   exit   |
                     |    ^     |
                     |    |     |
     ----------------+          +----------------------------------
       exit  <---                  [LED B]                    [SENSOR B]
                       JUNCTION    <-- car car car ...  <---  looks left
     ----------------+          +----------------------------------
                     | [LED A]  |
                     |   car    |
                     |   car    |
                     |   ...    |
                     |    ^     |
                     | [SENSOR A] looks up
```

Each sensor sits at the **start** of its lane (the end far from the junction) and looks along the lane **toward the junction**. Cars queue from the stop line back toward the sensor. The sensor measures how far away the **last car in the queue** is. More cars means the last car is closer to the sensor.

- Make each lane about **25 to 50 cm** long, from sensor to stop line.
- Put each red LED next to its lane's stop line, like the lights in your drawing.
- Mount each sensor at **car height** (about 2 to 4 cm off the table) so it hits the backs of the cars.
- Leave at least **5 cm** between the sensor and where the longest queue can reach. The HC-SR04 can't read closer than about 2 cm.
- When a lane has no cars, its sensor looks across the junction and either sees nothing or sees something far away. That is fine. Anything past the stop line counts as "no queue". You don't need a wall there.
- The HC-SR04 has a wide beam. Keep tall objects out of a 10 cm wide strip along lane A, or keep the lane edges lower than the sensor.
- Cars with a flat back (like LEGO bricks or small boxes) give much steadier readings than rounded toy cars.

To "move" traffic during the demo: when a lane is GO (its LED is off), take the front car away (it has crossed the junction) and slide the rest forward. When a lane is STOP, add cars to the back of its queue.

## 5. Install the library and upload

1. Install **Arduino IDE 2**.
2. Go to **Tools > Manage Libraries**, search **VL53L0X**, and install the one **by Pololu**.
3. Open `traffic_controller/traffic_controller.ino`. (The folder name must match the file name.)
4. **Tools > Board:** Arduino Uno. **Tools > Port:** the COM port for your Uno.
5. Click **Upload**.

## 6. Check it works (before building the dashboard)

1. Open **Tools > Serial Monitor**, set baud to **115200** and line ending to **Newline**.
2. You should see a `BOOT` line, then about 10 lines per second like:

```
{"type":"tel","ms":5123,"g":"A","next":"-","ph":"GREEN","pt":1100,"mode":"AUTO","why":"BOOT","emg":"-","emgLeft":0,"a":{"raw":30000,"d":503,"q":0,"n":0,"line":403,"w":0,"p":0.00,"ok":1},"b":{...}}
```

   `raw` of 30000 just means the sensor sees nothing in range, so no cars.

3. **Calibrate once** (see section 7). Until you do, both lanes show 0 cars.
4. Put 2 cars in lane B. Its `q` (queue in mm) and `n` (cars) should go up. After a few seconds lane B should get green: LED B goes off, LED A comes on, with a short "both on" moment in between.
5. Type `E:A` and press Enter. Lane A should get green and stay green. Type `E:OFF` to cancel.
6. **Close the Serial Monitor** before running the dashboard. Only one program can use the port at a time.

## 7. Calibration and settings

Calibration tells the Uno how far each stop line is from its sensor.

1. Take all cars off both lanes.
2. Stand a flat card upright on lane A's stop line, facing sensor A, and another on lane B's stop line, facing sensor B. Both lanes are measured at the same time, so you need two cards.
3. Send `CAL` (from the Serial Monitor or the dashboard button). Lights go all red for about a second.
4. Remove the cards.

It is saved in the Uno, so it survives power off. Do it again any time you move a sensor or a stop line.
- **Car length:** measure one car plus the gap you leave behind it, in mm. Send `CAR:70` (for 70 mm). This only changes how mm is turned into a car count.
- Timing values (min green, max green, clearance, etc.) are at the top of the `.ino` file if you want to change them.

## 8. How the decision works

There is no fixed clock cycle. Each lane gets green based on how much it needs it.

- **Queue length** = distance from sensor to stop line, minus the distance to the last car now.
- **Pressure** of the waiting lane = cars waiting + 0.5 for every second it has waited. The green lane's pressure is just its car count. The waiting time part means a short queue can't be ignored forever.
- Once a green has run for at least **4 s**, it switches when:
  - **GAP_OUT:** the green lane has no cars left and the other lane has cars.
  - **PRESSURE:** the waiting lane's pressure is more than 1.5 above the green lane's.
  - **MAX_GREEN:** the green has run 20 s and the other lane still has cars.
- If the other lane has no cars, green **stays** where it is. Nobody gets a green with no cars waiting.
- Every switch goes through **1.5 s of all red**.
- **Emergency** (from the dashboard) forces one lane green for up to 30 s, still with the all-red clearance first.
- If a sensor stops giving readings, that lane is marked faulty and treated as having 3 cars, so it keeps getting turns. The dashboard shows this as DEGRADED.

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `TOF_INIT_FAILED` at boot | Check SDA on A4, SCL on A5, VIN and GND. Try 3.3V if 5V does nothing. |
| Lane A `raw` is always -1 | TRIG and ECHO swapped, or no shared ground. |
| Both lanes always show 0 cars | Not calibrated yet. Do section 7. |
| `CAL` reports `okA:0` or `okB:0` | That sensor couldn't see the card. Make the card bigger and face it straight at the sensor. |
| Queue numbers jump around | Use flat-backed cars, lower the lane edges, mount the sensor straight. |
| Lane shows cars when there are none | Something is inside the lane in the sensor's view. Clear it, or recalibrate. |
| LED never turns on | LED is backwards (long leg goes to the resistor side), or wrong pin. |
| Dashboard can't open the port | Close the Arduino Serial Monitor. |
