import { calculateBaziChart, type BaziInput } from "@openfate/bazi-engine";

import type { ChartRequest } from "./schema.js";

const POLICY = {
  calendar_type: "solar",
  timezone_id: "Asia/Shanghai",
  dst_offset: 0,
  day_boundary_mode: "ZI_HOUR_23",
} as const;

export function calculateChart(request: ChartRequest) {
  const [year, month, day] = request.birth_date.split("-").map(Number);
  const input: BaziInput = {
    year: year!,
    month: month!,
    day: day!,
    gender: request.gender,
    longitude: request.longitude,
    timezoneId: POLICY.timezone_id,
    dstOffset: POLICY.dst_offset,
    calendarType: POLICY.calendar_type,
    enableTrueSolarTime: request.true_solar_time,
    dayBoundaryMode: POLICY.day_boundary_mode,
  };

  if (!request.birth_time_unknown) {
    input.hour = Number(request.birth_time!.slice(0, 2));
    input.minute = Number(request.birth_time!.slice(3, 5));
  }

  const chart = calculateBaziChart(input);
  return {
    chart: {
      pillars: chart.pillars,
      day_master: chart.dayMaster,
      da_yun: chart.daYun,
      interactions: chart.interactions,
      solar_time: chart.solarTimeInfo,
      calendar: chart.calendar,
      metadata: chart.metadata,
    },
    policy: {
      ...POLICY,
      true_solar_time: request.true_solar_time,
      birth_time_unknown: request.birth_time_unknown,
    },
    attribution: {
      name: "OpenFate.ai",
      url: "https://openfate.ai",
      engine: "@openfate/bazi-engine@1.1.1",
      true_solar_time_engine: "@openfate/true-solar-time@4.0.2",
    },
  };
}
