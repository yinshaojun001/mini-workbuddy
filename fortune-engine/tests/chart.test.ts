import assert from "node:assert/strict";
import { test } from "node:test";

import { calculateChart } from "../src/chart.js";
import { parseChartRequest, RequestValidationError } from "../src/schema.js";

const baseRequest = {
  birth_date: "1998-12-13",
  birth_time: "12:00",
  birth_time_unknown: false,
  gender: "female",
  longitude: 116.39,
  true_solar_time: false,
} as const;

test("matches the published OpenFate Four Pillars example", () => {
  const result = calculateChart(baseRequest);
  assert.deepEqual(
    Object.values(result.chart.pillars).map((pillar) => pillar?.ganZhi ?? null),
    ["戊寅", "甲子", "甲午", "庚午"],
  );
  assert.equal(result.chart.day_master.element, "wood");
  assert.equal(Object.values(result.chart.five_elements).reduce((total, count) => total + count, 0), 8);
  assert.equal(result.chart.ten_gods.day, "日主");
  assert(result.chart.hidden_stems.year.length > 0);
  assert.equal(result.policy.day_boundary_mode, "ZI_HOUR_23");
  assert.equal(result.chart.metadata.trueSolarTimeApplied, false);
});

test("applies true solar time and can cross an hour branch in Urumqi", () => {
  const civil = calculateChart({ ...baseRequest, birth_time: "09:10", longitude: 87.62 });
  const solar = calculateChart({ ...baseRequest, birth_time: "09:10", longitude: 87.62, true_solar_time: true });
  assert.equal(civil.chart.pillars.hour?.branch, "巳");
  assert.notEqual(solar.chart.pillars.hour?.branch, civil.chart.pillars.hour?.branch);
  assert.equal(solar.chart.metadata.trueSolarTimeApplied, true);
  assert.match(solar.chart.solar_time?.trueSolarTime ?? "", /^\d{2}:\d{2}/);
});

test("uses the 23:00 Zi-hour day boundary", () => {
  const before = calculateChart({ ...baseRequest, birth_date: "2000-01-01", birth_time: "22:59" });
  const after = calculateChart({ ...baseRequest, birth_date: "2000-01-01", birth_time: "23:00" });
  assert.notEqual(after.chart.pillars.day.ganZhi, before.chart.pillars.day.ganZhi);
  assert.equal(after.chart.pillars.hour?.branch, "子");
});

test("changes year and month pillars across the 2024 Li Chun boundary", () => {
  const before = calculateChart({ ...baseRequest, birth_date: "2024-02-04", birth_time: "16:25" });
  const after = calculateChart({ ...baseRequest, birth_date: "2024-02-04", birth_time: "16:40" });
  assert.notEqual(after.chart.pillars.year.ganZhi, before.chart.pillars.year.ganZhi);
  assert.notEqual(after.chart.pillars.month.ganZhi, before.chart.pillars.month.ganZhi);
});

test("returns a three-pillar chart when birth time is unknown", () => {
  const result = calculateChart({
    ...baseRequest,
    birth_time: null,
    birth_time_unknown: true,
    true_solar_time: false,
  });
  assert.equal(result.chart.pillars.hour, null);
  assert.equal(Object.values(result.chart.five_elements).reduce((total, count) => total + count, 0), 6);
  assert.equal(result.chart.calendar.civilSolar.hour, null);
  assert.equal(result.chart.solar_time, null);
});

test("gender controls Da Yun direction", () => {
  const female = calculateChart(baseRequest);
  const male = calculateChart({ ...baseRequest, gender: "male" });
  assert.notEqual(female.chart.da_yun.isForward, male.chart.da_yun.isForward);
  assert.notEqual(female.chart.da_yun.cycles[0]?.ganZhi, male.chart.da_yun.cycles[0]?.ganZhi);
});

test("rejects unknown fields and invalid time combinations", () => {
  assert.throws(() => parseChartRequest({ ...baseRequest, agent_id: "other" }), RequestValidationError);
  assert.throws(
    () => parseChartRequest({ ...baseRequest, birth_time_unknown: true, true_solar_time: true }),
    /unknown birth time/,
  );
  assert.throws(() => parseChartRequest({ ...baseRequest, birth_date: "2024-02-31" }), /invalid/);
});
