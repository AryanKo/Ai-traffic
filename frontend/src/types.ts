export interface LaneTelemetry {
  raw: number;
  d: number;
  q: number;
  n: number;
  line: number;
  w: number;
  p: number;
  ok: 0 | 1;
}

export interface Telemetry {
  type: "tel";
  ms: number;
  g: "A" | "B" | "X";
  next: "A" | "B" | "-";
  ph: "GREEN" | "CLEAR";
  pt: number;
  mode: "AUTO" | "EMERGENCY" | "DEGRADED";
  why: "BOOT" | "GAP_OUT" | "PRESSURE" | "MAX_GREEN" | "EMERGENCY";
  emg: "A" | "B" | "-";
  emgLeft: number;
  a: LaneTelemetry;
  b: LaneTelemetry;
}

export interface EventMsg {
  type: "evt";
  ms: number;
  ev: "BOOT" | "CFG" | "CAL" | "SWITCH" | "GREEN" | "EMG_ON" | "EMG_OFF" | "FAULT" | "RECOVER" | "ERR";
  host_ts?: number;
  [key: string]: unknown;
}

export interface AckMsg {
  type: "ack";
  ms: number;
  cmd: string;
}

export interface LinkStatus {
  connected: boolean;
  port: string | null;
  pps: number;
  last_packet_age: number | null;
  parse_errors: number;
  booted: boolean;
}

export interface Config {
  lineA: number;
  lineB: number;
  carMm: number;
  minG: number;
  maxG: number;
  clr: number;
  emgT: number;
  queueMin: number;
  waitW: number;
  margin: number;
  faultDemand: number;
  tof: number;
  cal?: "EEPROM" | "NONE";
}

export const NO_TARGET_RAW = 30000;

export function isNoQueue(raw: number, q: number): boolean {
  return raw === NO_TARGET_RAW || q === 0;
}
