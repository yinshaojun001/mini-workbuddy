import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

interface CityRecord {
  code: string;
  parent_code: string;
  name: string;
  longitude: number;
  geoname_id: number;
  level: "province" | "city";
}

const catalog = JSON.parse(
  await readFile(new URL("../data/cities.json", import.meta.url), "utf8"),
) as { source: { license: string; input_sha256: string }; records: CityRecord[] };

test("contains complete GeoNames province and prefecture coverage", () => {
  assert(catalog.records.filter((record) => record.level === "province").length >= 30);
  assert(catalog.records.filter((record) => record.level === "city").length >= 300);
  assert.equal(catalog.source.license, "CC BY 4.0");
  assert.match(catalog.source.input_sha256, /^[a-f0-9]{64}$/);
});

test("representative cities have plausible longitudes and valid parents", () => {
  const provinces = new Set(catalog.records.filter((record) => record.level === "province").map((record) => record.code));
  const expected = [
    ["北京市", 116.4],
    ["上海市", 121.47],
    ["广州市", 113.26],
    ["乌鲁木齐市", 87.62],
  ] as const;

  for (const [name, longitude] of expected) {
    const record = catalog.records.find((candidate) => candidate.name === name && candidate.level === "city");
    assert(record, `Missing ${name}`);
    assert(Math.abs(record.longitude - longitude) < 1.5, `${name} longitude is implausible`);
    assert(provinces.has(record.parent_code), `${name} has an invalid parent`);
  }
});

test("catalog codes and GeoNames identifiers are unique", () => {
  assert.equal(new Set(catalog.records.map((record) => record.code)).size, catalog.records.length);
  assert.equal(new Set(catalog.records.map((record) => record.geoname_id)).size, catalog.records.length);
});
