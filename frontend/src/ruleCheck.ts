import type { Config, LaneTelemetry, Telemetry } from "./types";

export interface RuleResult {
  id: string;
  label: string;
  pass: boolean;
  detail: string;
}

function other(tel: Telemetry): LaneTelemetry {
  return tel.g === "A" ? tel.b : tel.a;
}
function green(tel: Telemetry): LaneTelemetry {
  return tel.g === "A" ? tel.a : tel.b;
}

export function evaluateRules(tel: Telemetry, config: Config): RuleResult[] {
  if (tel.g === "X") {
    return [{ id: "all_red", label: "All red clearance in progress", pass: true, detail: "Rules apply once a lane has green" }];
  }
  const g = green(tel);
  const o = other(tel);
  const minGreenOk = tel.pt >= config.minG;
  const otherHasCars = o.n > 0;
  const gapOut = g.n === 0;
  const pressureMargin = o.p > g.p + config.margin;
  const maxGreenOk = tel.pt >= config.maxG;

  return [
    { id: "min_green", label: "Min green reached", pass: minGreenOk, detail: `${tel.pt}ms / ${config.minG}ms` },
    { id: "other_has_cars", label: "Other lane has cars", pass: otherHasCars, detail: `${o.n} cars` },
    { id: "gap_out", label: "Green lane has no cars (GAP_OUT)", pass: minGreenOk && otherHasCars && gapOut, detail: `green lane cars: ${g.n}` },
    { id: "pressure", label: "Pressure: other > green + margin", pass: minGreenOk && otherHasCars && pressureMargin, detail: `${o.p.toFixed(2)} vs ${g.p.toFixed(2)} + ${config.margin}` },
    { id: "max_green", label: "Max green reached", pass: maxGreenOk, detail: `${tel.pt}ms / ${config.maxG}ms` },
  ];
}
