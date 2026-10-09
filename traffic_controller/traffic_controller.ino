/*
  TrafficMind Lite: adaptive two-lane junction controller
  ------------------------------------------------------
  Board   : Arduino Uno
  Layout  : two one-way lanes that both drive TOWARD one junction.
            Lane A comes from the bottom, lane B comes from the right.
            Only one lane can cross the junction at a time.
  Lane A  : HC-SR04 ultrasonic sensor   (TRIG -> D9, ECHO -> D10)
  Lane B  : VL53L0X laser ToF sensor    (SDA -> A4, SCL -> A5)
  Lights  : Lane A red LED -> D5, Lane B red LED -> D6
            LED ON  = red (stop)
            LED OFF = go
  Library : "VL53L0X" by Pololu (install from Library Manager)
  Serial  : 115200 baud. One JSON object per line out. Plain text commands in.

  Where the sensors go:
    Each sensor sits at the start of its lane (the end far from the junction)
    and looks along the lane toward the junction. Cars queue from the stop
    line back toward the sensor. The sensor measures the distance to the
    LAST car in the queue.

  Calibration (stop line distance):
    Stand a flat piece of card upright on each stop line and send CAL.
    The Uno saves how far each stop line is from its sensor.
    Queue length = stop line distance minus measured distance.
    If a sensor sees nothing, or sees something past the stop line
    (across the junction), that lane has no queue.

  How the decision works (no fixed clock cycle):
    - A waiting lane builds "pressure" = cars + (seconds waiting x WAIT_WEIGHT).
      The green lane's pressure is just its car count.
    - The green lane keeps green until one of these happens (only after MIN_GREEN):
        GAP_OUT   : green lane is empty and the other lane has cars
        PRESSURE  : waiting lane pressure beats green lane pressure by SWITCH_MARGIN
        MAX_GREEN : green has run for MAX_GREEN and the other lane still has cars
    - If the other lane has no cars, green stays where it is.
    - Every switch goes through an all-red clearance (both LEDs on).
    - Emergency mode (sent from the dashboard) forces one lane green until
      it is cancelled or times out.

  Commands (end each with a newline):
    PING        -> ack
    CFG         -> ack, then the current settings
    CAL         -> measures both stop lines (card on each stop line first)
    CAR:<mm>    -> sets the length of one car plus its gap, in mm (10 to 500)
    E:A / E:B   -> emergency priority for lane A or lane B
    E:OFF       -> cancel emergency
    L:<a><b>    -> direct LED control, each digit 1 = LED on, 0 = LED off
                   (L:10 = LED A on, LED B off). Switches to direct mode.

  Direct mode (BOOT_DIRECT = true):
    The board starts with the LEDs under direct L:<a><b> control. It does not
    read the sensors or run the automatic decision logic. E:A / E:B still
    work: they turn the priority lane's LED off and the other LED on.
    Set BOOT_DIRECT to false to boot into the automatic controller.
*/

#include <Wire.h>
#include <EEPROM.h>
#include <VL53L0X.h>

// ---------------- Pins ----------------
const uint8_t PIN_TRIG  = 9;
const uint8_t PIN_ECHO  = 10;
const uint8_t PIN_RED_A = 5;
const uint8_t PIN_RED_B = 6;

// ---------------- Timing (ms) ----------------
const unsigned long SAMPLE_MS      = 100;    // sensor read + telemetry rate (10 per second)
const unsigned long MIN_GREEN_MS   = 4000;   // a green always lasts at least this long
const unsigned long MAX_GREEN_MS   = 20000;  // longest green while the other lane waits
const unsigned long CLEAR_MS       = 1500;   // all-red time between greens
const unsigned long EMG_TIMEOUT_MS = 30000;  // emergency ends by itself after this

// ---------------- Decision tuning ----------------
const uint16_t QUEUE_MIN_MM    = 20;   // a queue shorter than this counts as no queue (sensor noise)
const float    WAIT_WEIGHT     = 0.5;  // pressure added per second of waiting
const float    SWITCH_MARGIN   = 1.5;  // waiting lane must beat the green lane by this much
const uint8_t  FAULT_LIMIT     = 10;   // bad readings in a row before a sensor is marked faulty
const uint8_t  FAULT_DEMAND    = 3;    // cars assumed for a faulty lane so it still gets turns

// A reading of NO_TARGET_MM means "the sensor sees nothing in range".
// That is normal: it means there is no car in the lane.
const int16_t  NO_TARGET_MM    = 30000;

// ---------------- Direct LED control ----------------
const bool BOOT_DIRECT = true;
bool direct = BOOT_DIRECT;
bool ledOnA = true;   // LED on = red; both on at boot is the safe default
bool ledOnB = true;

// ---------------- Saved settings ----------------
const uint16_t EE_MAGIC = 0xC0E1;
uint16_t carLenMm = 70;  // one toy car plus the gap behind it

// ---------------- Lane state ----------------
struct Lane {
  char     id;
  uint16_t lineMm;          // distance from sensor to stop line (0 = not calibrated)
  int16_t  lastRaw;         // latest raw reading in mm, -1 = failed, 30000 = nothing in range
  uint16_t buf[5];          // last 5 good readings for the median filter
  uint8_t  bufCount;
  uint8_t  bufIdx;
  float    filtMm;          // smoothed distance
  bool     hasFilt;
  uint16_t queueMm;         // measured queue length
  uint8_t  cars;            // estimated cars in the queue
  unsigned long waitStart;  // when this lane started waiting (0 = not waiting)
  uint8_t  badCount;
  bool     fault;
  float    pressure;
};

Lane laneA;
Lane laneB;
VL53L0X tof;
bool tofReady = false;

// ---------------- Controller state ----------------
enum Phase : uint8_t { PH_GREEN, PH_CLEAR };
Phase phase = PH_CLEAR;
char  greenLane  = 'A';   // lane that has green (during CLEAR: the lane that just had it)
char  targetLane = 'A';   // lane that gets green when CLEAR ends
unsigned long phaseStart = 0;
const char* lastReason = "BOOT";
char  emgLane = 0;        // 0 = no emergency
unsigned long emgStart = 0;
unsigned long lastSample = 0;

char    cmdBuf[24];
uint8_t cmdLen = 0;

// ================= Small helpers =================

Lane& laneById(char id) { return (id == 'A') ? laneA : laneB; }
char otherLane(char id) { return (id == 'A') ? 'B' : 'A'; }

uint16_t medianOf(const uint16_t* src, uint8_t n) {
  uint16_t tmp[15];
  if (n > 15) n = 15;
  for (uint8_t i = 0; i < n; i++) tmp[i] = src[i];
  for (uint8_t i = 1; i < n; i++) {
    uint16_t v = tmp[i];
    int8_t j = i - 1;
    while (j >= 0 && tmp[j] > v) { tmp[j + 1] = tmp[j]; j--; }
    tmp[j + 1] = v;
  }
  return tmp[n / 2];
}

// 'A' = lane A goes, 'B' = lane B goes, 'X' = all red
void setLights(char g) {
  digitalWrite(PIN_RED_A, (g == 'A') ? LOW : HIGH);
  digitalWrite(PIN_RED_B, (g == 'B') ? LOW : HIGH);
}

void applyDirectLeds() {
  digitalWrite(PIN_RED_A, ledOnA ? HIGH : LOW);
  digitalWrite(PIN_RED_B, ledOnB ? HIGH : LOW);
}

// Puts the LEDs back to what the current mode says they should be.
void restoreLights() {
  if (direct) applyDirectLeds();
  else        setLights(phase == PH_GREEN ? greenLane : 'X');
}

// ================= JSON output helpers =================

void evtStart(const __FlashStringHelper* name) {
  Serial.print(F("{\"type\":\"evt\",\"ms\":"));
  Serial.print(millis());
  Serial.print(F(",\"ev\":\""));
  Serial.print(name);
  Serial.print('"');
}
void evtEnd() { Serial.println('}'); }

void kvStr(const __FlashStringHelper* k, const char* v) {
  Serial.print(F(",\"")); Serial.print(k); Serial.print(F("\":\""));
  Serial.print(v); Serial.print('"');
}
void kvChar(const __FlashStringHelper* k, char v) {
  Serial.print(F(",\"")); Serial.print(k); Serial.print(F("\":\""));
  Serial.print(v); Serial.print('"');
}
void kvLong(const __FlashStringHelper* k, long v) {
  Serial.print(F(",\"")); Serial.print(k); Serial.print(F("\":"));
  Serial.print(v);
}
void kvFloat(const __FlashStringHelper* k, float v) {
  Serial.print(F(",\"")); Serial.print(k); Serial.print(F("\":"));
  Serial.print(v, 2);
}

void emitErr(const __FlashStringHelper* msg) {
  Serial.print(F("{\"type\":\"evt\",\"ms\":"));
  Serial.print(millis());
  Serial.print(F(",\"ev\":\"ERR\",\"msg\":\""));
  Serial.print(msg);
  Serial.println(F("\"}"));
}

void ack(const __FlashStringHelper* cmd) {
  Serial.print(F("{\"type\":\"ack\",\"ms\":"));
  Serial.print(millis());
  Serial.print(F(",\"cmd\":\""));
  Serial.print(cmd);
  Serial.println(F("\"}"));
}

void emitConfig(const __FlashStringHelper* name, const char* calSource) {
  evtStart(name);
  kvLong(F("lineA"), laneA.lineMm);
  kvLong(F("lineB"), laneB.lineMm);
  kvLong(F("carMm"), carLenMm);
  kvLong(F("minG"), MIN_GREEN_MS);
  kvLong(F("maxG"), MAX_GREEN_MS);
  kvLong(F("clr"), CLEAR_MS);
  kvLong(F("emgT"), EMG_TIMEOUT_MS);
  kvLong(F("queueMin"), QUEUE_MIN_MM);
  kvFloat(F("waitW"), WAIT_WEIGHT);
  kvFloat(F("margin"), SWITCH_MARGIN);
  kvLong(F("faultDemand"), FAULT_DEMAND);
  kvLong(F("tof"), tofReady ? 1 : 0);
  kvLong(F("direct"), direct ? 1 : 0);
  if (calSource) kvStr(F("cal"), calSource);
  evtEnd();
}

// ================= Sensors =================

// Lane A: HC-SR04.
// Returns distance in mm, NO_TARGET_MM if nothing is in range,
// or -1 if the sensor did not answer (wiring fault) or the object is too close.
int16_t readUltrasonic() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);

  unsigned long t0 = micros();
  while (digitalRead(PIN_ECHO) == LOW) {
    if (micros() - t0 > 5000UL) return -1;           // sensor never answered
  }
  unsigned long start = micros();
  while (digitalRead(PIN_ECHO) == HIGH) {
    if (micros() - start > 30000UL) return NO_TARGET_MM;  // no echo came back
  }
  unsigned long us = micros() - start;
  long mm = (long)(us * 0.1715f);                    // speed of sound / 2
  if (mm < 20) return -1;                            // too close to measure
  if (mm > 4000) return NO_TARGET_MM;
  return (int16_t)mm;
}

// Lane B: VL53L0X.
// Returns distance in mm, NO_TARGET_MM if nothing is in range,
// or -1 if the sensor did not answer.
int16_t readTof() {
  if (!tofReady) return -1;
  uint16_t mm = tof.readRangeContinuousMillimeters();
  if (tof.timeoutOccurred()) return -1;
  if (mm >= 8000) return NO_TARGET_MM;
  return (int16_t)mm;
}

// ================= Settings in EEPROM =================

void saveSettings() {
  EEPROM.put(0, EE_MAGIC);
  EEPROM.put(2, laneA.lineMm);
  EEPROM.put(4, laneB.lineMm);
  EEPROM.put(6, carLenMm);
}

bool loadSettings() {
  uint16_t magic, a, b, c;
  EEPROM.get(0, magic);
  if (magic != EE_MAGIC) return false;
  EEPROM.get(2, a);
  EEPROM.get(4, b);
  EEPROM.get(6, c);
  if (c >= 10 && c <= 500) carLenMm = c;
  laneA.lineMm = a;
  laneB.lineMm = b;
  return (a > 0 && b > 0);
}

void resetFilter(Lane& L) {
  L.bufCount = 0;
  L.bufIdx = 0;
  L.hasFilt = false;
  L.badCount = 0;
}

// Measures the distance from each sensor to its stop line.
// Before sending CAL, stand a flat card upright on each stop line.
// Lights go all red while it runs.
bool calibrate() {
  setLights('X');
  uint16_t a[15], b[15];
  uint8_t na = 0, nb = 0;
  for (uint8_t i = 0; i < 15; i++) {
    int16_t ra = readUltrasonic();
    if (ra > 0 && ra < NO_TARGET_MM) a[na++] = ra;
    int16_t rb = readTof();
    if (rb > 0 && rb < NO_TARGET_MM) b[nb++] = rb;
    delay(70);
  }
  bool okA = (na >= 8);
  bool okB = (nb >= 8);
  if (okA) laneA.lineMm = medianOf(a, na);
  if (okB) laneB.lineMm = medianOf(b, nb);
  resetFilter(laneA);
  resetFilter(laneB);
  saveSettings();

  evtStart(F("CAL"));
  kvLong(F("lineA"), laneA.lineMm);
  kvLong(F("okA"), okA ? 1 : 0);
  kvLong(F("lineB"), laneB.lineMm);
  kvLong(F("okB"), okB ? 1 : 0);
  evtEnd();
  return okA && okB;
}

// ================= Lane processing =================

void updateLane(Lane& L, int16_t reading) {
  L.lastRaw = reading;

  if (reading < 0) {
    if (L.badCount < 255) L.badCount++;
    if (!L.fault && L.badCount >= FAULT_LIMIT) {
      L.fault = true;
      evtStart(F("FAULT")); kvChar(F("lane"), L.id); evtEnd();
    }
    return;
  }

  L.badCount = 0;
  if (L.fault) {
    L.fault = false;
    evtStart(F("RECOVER")); kvChar(F("lane"), L.id); evtEnd();
  }

  // Anything past the stop line (across the junction, or nothing at all)
  // just means "no queue". Clamp it so the filter reacts quickly.
  if (L.lineMm > 0 && reading > (int16_t)(L.lineMm + 100)) {
    reading = L.lineMm + 100;
  }

  // median of last 5, then light smoothing
  L.buf[L.bufIdx] = (uint16_t)reading;
  L.bufIdx = (L.bufIdx + 1) % 5;
  if (L.bufCount < 5) L.bufCount++;
  uint16_t med = medianOf(L.buf, L.bufCount);
  if (!L.hasFilt) { L.filtMm = med; L.hasFilt = true; }
  else            { L.filtMm = 0.6f * L.filtMm + 0.4f * med; }

  if (L.lineMm == 0) {      // not calibrated yet, so no queue can be worked out
    L.queueMm = 0;
    L.cars = 0;
    return;
  }

  long q = (long)L.lineMm - (long)(L.filtMm + 0.5f);
  if (q < (long)QUEUE_MIN_MM) q = 0;
  L.queueMm = (uint16_t)q;
  if (q == 0) {
    L.cars = 0;
  } else {
    long n = (q + carLenMm / 2) / carLenMm;
    if (n < 1) n = 1;
    if (n > 99) n = 99;
    L.cars = (uint8_t)n;
  }
}

uint8_t carsFor(const Lane& L) { return L.fault ? FAULT_DEMAND : L.cars; }

void computePressure(Lane& L, unsigned long now) {
  uint8_t c = carsFor(L);
  bool isGreen = (phase == PH_GREEN && greenLane == L.id);
  if (isGreen || c == 0) {
    L.waitStart = 0;
  } else if (L.waitStart == 0) {
    L.waitStart = now;
  }
  float waitSec = L.waitStart ? (now - L.waitStart) / 1000.0f : 0.0f;
  L.pressure = c + waitSec * WAIT_WEIGHT;
}

// ================= Signal control =================

void startSwitch(char to, const char* why, unsigned long now) {
  evtStart(F("SWITCH"));
  kvChar(F("from"), greenLane);
  kvChar(F("to"), to);
  kvStr(F("why"), why);
  kvLong(F("greenMs"), now - phaseStart);
  kvLong(F("nA"), carsFor(laneA));
  kvLong(F("nB"), carsFor(laneB));
  kvFloat(F("pA"), laneA.pressure);
  kvFloat(F("pB"), laneB.pressure);
  evtEnd();

  phase = PH_CLEAR;
  targetLane = to;
  phaseStart = now;
  lastReason = why;
  setLights('X');
}

void finishClear(unsigned long now) {
  greenLane = targetLane;
  phase = PH_GREEN;
  phaseStart = now;
  setLights(greenLane);
  laneById(greenLane).waitStart = 0;
  evtStart(F("GREEN"));
  kvChar(F("lane"), greenLane);
  kvStr(F("why"), lastReason);
  evtEnd();
}

void startEmergency(char lane, unsigned long now) {
  emgLane = lane;
  emgStart = now;
  evtStart(F("EMG_ON")); kvChar(F("lane"), lane); evtEnd();
  if (direct) {                 // priority lane's LED off (go), other LED on (stop)
    ledOnA = (lane != 'A');
    ledOnB = (lane != 'B');
    applyDirectLeds();
    return;
  }
  if (phase == PH_CLEAR) {      // already changing: send the change to the emergency lane
    targetLane = lane;
    lastReason = "EMERGENCY";
  }
}

void endEmergency(const char* why) {
  if (!emgLane) return;
  evtStart(F("EMG_OFF"));
  kvChar(F("lane"), emgLane);
  kvStr(F("why"), why);
  evtEnd();
  emgLane = 0;
}

void decide(unsigned long now) {
  if (phase == PH_CLEAR) {
    if (now - phaseStart >= CLEAR_MS) finishClear(now);
    return;
  }

  // Emergency overrides everything except the all-red clearance
  if (emgLane) {
    if (now - emgStart >= EMG_TIMEOUT_MS) {
      endEmergency("TIMEOUT");
    } else {
      if (emgLane != greenLane) startSwitch(emgLane, "EMERGENCY", now);
      return;
    }
  }

  unsigned long greenFor = now - phaseStart;
  char other = otherLane(greenLane);
  Lane& g = laneById(greenLane);
  Lane& o = laneById(other);
  uint8_t gc = carsFor(g);
  uint8_t oc = carsFor(o);

  if (oc == 0) return;                    // nobody waiting: keep green
  if (greenFor < MIN_GREEN_MS) return;    // let the current green do some work

  if (gc == 0)                            { startSwitch(other, "GAP_OUT", now);   return; }
  if (greenFor >= MAX_GREEN_MS)           { startSwitch(other, "MAX_GREEN", now); return; }
  if (o.pressure > g.pressure + SWITCH_MARGIN) { startSwitch(other, "PRESSURE", now); return; }
}

// ================= Telemetry =================

void printLane(const __FlashStringHelper* key, const Lane& L, unsigned long now) {
  bool valid = !L.fault && L.hasFilt;
  Serial.print(F(",\"")); Serial.print(key); Serial.print(F("\":{\"raw\":"));
  Serial.print(L.lastRaw);
  Serial.print(F(",\"d\":"));    Serial.print(valid ? (long)(L.filtMm + 0.5f) : -1L);
  Serial.print(F(",\"q\":"));    Serial.print(valid ? (long)L.queueMm : -1L);
  Serial.print(F(",\"n\":"));    Serial.print(valid ? (long)L.cars : -1L);
  Serial.print(F(",\"line\":")); Serial.print(L.lineMm);
  Serial.print(F(",\"w\":"));    Serial.print(L.waitStart ? (long)(now - L.waitStart) : 0L);
  Serial.print(F(",\"p\":"));    Serial.print(L.pressure, 2);
  Serial.print(F(",\"ok\":"));   Serial.print(L.fault ? 0 : 1);
  Serial.print('}');
}

void sendTelemetry(unsigned long now) {
  Serial.print(F("{\"type\":\"tel\",\"ms\":"));
  Serial.print(now);
  Serial.print(F(",\"g\":\""));    Serial.print(phase == PH_GREEN ? greenLane : 'X');
  Serial.print(F("\",\"next\":\"")); Serial.print(phase == PH_CLEAR ? targetLane : '-');
  Serial.print(F("\",\"ph\":\""));   Serial.print(phase == PH_GREEN ? F("GREEN") : F("CLEAR"));
  Serial.print(F("\",\"pt\":"));     Serial.print(now - phaseStart);
  Serial.print(F(",\"mode\":\""));
  if (direct)                           Serial.print(F("DIRECT"));
  else if (emgLane)                     Serial.print(F("EMERGENCY"));
  else if (laneA.fault || laneB.fault)  Serial.print(F("DEGRADED"));
  else                                  Serial.print(F("AUTO"));
  Serial.print(F("\",\"why\":\""));  Serial.print(lastReason);
  Serial.print(F("\",\"emg\":\""));  Serial.print(emgLane ? emgLane : '-');
  long emgLeft = 0;
  if (emgLane) {
    unsigned long used = now - emgStart;
    emgLeft = (used >= EMG_TIMEOUT_MS) ? 0 : (long)(EMG_TIMEOUT_MS - used);
  }
  Serial.print(F("\",\"emgLeft\":")); Serial.print(emgLeft);
  Serial.print(F(",\"la\":")); Serial.print(ledOnA ? 1 : 0);
  Serial.print(F(",\"lb\":")); Serial.print(ledOnB ? 1 : 0);
  printLane(F("a"), laneA, now);
  printLane(F("b"), laneB, now);
  Serial.println('}');
}

// ================= Commands from the dashboard =================

void handleCmd(char* c) {
  unsigned long now = millis();
  if (strcmp(c, "PING") == 0) {
    ack(F("PING"));
  } else if (strcmp(c, "CFG") == 0) {
    ack(F("CFG"));
    emitConfig(F("CFG"), NULL);
  } else if (strcmp(c, "CAL") == 0) {
    ack(F("CAL"));
    calibrate();
    restoreLights();
  } else if (strcmp(c, "E:A") == 0) {
    ack(F("E:A"));
    startEmergency('A', now);
  } else if (strcmp(c, "E:B") == 0) {
    ack(F("E:B"));
    startEmergency('B', now);
  } else if (strcmp(c, "E:OFF") == 0) {
    ack(F("E:OFF"));
    endEmergency("MANUAL");
  } else if (c[0] == 'L' && c[1] == ':' && (c[2] == '0' || c[2] == '1')
             && (c[3] == '0' || c[3] == '1') && c[4] == 0) {
    direct = true;
    ledOnA = (c[2] == '1');
    ledOnB = (c[3] == '1');
    applyDirectLeds();
    ack(F("L"));
  } else if (strncmp(c, "CAR:", 4) == 0) {
    long v = atol(c + 4);
    if (v >= 10 && v <= 500) {
      carLenMm = (uint16_t)v;
      saveSettings();
      ack(F("CAR"));
      emitConfig(F("CFG"), NULL);
    } else {
      emitErr(F("CAR_OUT_OF_RANGE"));
    }
  } else if (c[0] != 0) {
    emitErr(F("UNKNOWN_CMD"));
  }
}

void pollSerial() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      cmdBuf[cmdLen] = 0;
      handleCmd(cmdBuf);
      cmdLen = 0;
    } else if (cmdLen < sizeof(cmdBuf) - 1) {
      cmdBuf[cmdLen++] = ch;
    }
  }
}

// ================= Setup and loop =================

void setup() {
  Serial.begin(115200);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_RED_A, OUTPUT);
  pinMode(PIN_RED_B, OUTPUT);
  digitalWrite(PIN_TRIG, LOW);
  setLights('X');                 // start all red

  laneA.id = 'A';
  laneB.id = 'B';

  Wire.begin();
  Wire.setWireTimeout(3000, true);  // stops the Uno freezing if the I2C wire comes loose
  tof.setTimeout(100);
  tofReady = tof.init();
  if (tofReady) tof.startContinuous(33);

  delay(300);
  bool calibrated = loadSettings();
  if (!tofReady && !direct) emitErr(F("TOF_INIT_FAILED"));
  // If not calibrated yet, both lanes show no queue until CAL is sent.
  emitConfig(F("BOOT"), calibrated ? "EEPROM" : "NONE");

  phase = PH_GREEN;
  greenLane = 'A';
  targetLane = 'A';
  phaseStart = millis();
  lastReason = "BOOT";
  if (direct) {
    applyDirectLeds();
  } else {
    setLights('A');
    evtStart(F("GREEN")); kvChar(F("lane"), 'A'); kvStr(F("why"), "BOOT"); evtEnd();
  }
}

void loop() {
  pollSerial();
  unsigned long now = millis();
  if (now - lastSample >= SAMPLE_MS) {
    lastSample = now;
    if (direct) {
      if (emgLane && now - emgStart >= EMG_TIMEOUT_MS) endEmergency("TIMEOUT");
    } else {
      updateLane(laneA, readUltrasonic());
      updateLane(laneB, readTof());
      now = millis();
      computePressure(laneA, now);
      computePressure(laneB, now);
      decide(now);
    }
    sendTelemetry(now);
  }
}
