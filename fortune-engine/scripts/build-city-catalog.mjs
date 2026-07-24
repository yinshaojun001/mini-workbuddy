import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { basename, resolve } from "node:path";

const [inputArg, outputArg = "data/cities.json"] = process.argv.slice(2);
if (!inputArg) {
  console.error("Usage: node scripts/build-city-catalog.mjs <CN.txt> [output.json]");
  process.exit(1);
}

const inputPath = resolve(inputArg);
const outputPath = resolve(outputArg);
const input = await readFile(inputPath);
const checksum = createHash("sha256").update(input).digest("hex");
const rows = input.toString("utf8").split("\n").filter(Boolean).map((line) => line.split("\t"));

const DIRECT_MUNICIPALITIES = new Map([
  ["22", ["110000", "110100"]],
  ["28", ["120000", "120100"]],
  ["23", ["310000", "310100"]],
  ["33", ["500000", "500100"]],
]);

function chineseName(columns, level) {
  const candidates = (columns[3] ?? "").split(",").filter((name) => /^[\p{Script=Han}]+$/u.test(name));
  const suffixPattern = level === "province" ? /(省|市|自治区)$/u : /(市|地区|自治州|盟)$/u;
  const preferred = candidates.filter((name) => suffixPattern.test(name));
  const selected = (preferred.length > 0 ? preferred : candidates).sort((left, right) => right.length - left.length)[0];
  if (!selected) throw new Error(`Missing Chinese name for GeoNames row ${columns[0]}`);
  return selected;
}

const admin1ToNationalCode = new Map(DIRECT_MUNICIPALITIES.entries().map(([admin1, [provinceCode]]) => [admin1, provinceCode]));
for (const columns of rows) {
  if (columns[6] !== "A" || columns[7] !== "ADM2" || columns[8] !== "CN" || !columns[10]) continue;
  if (/^\d{4}$/.test(columns[11] ?? "")) admin1ToNationalCode.set(columns[10], `${columns[11].slice(0, 2)}0000`);
}

const provinces = new Map();
for (const columns of rows) {
  if (columns[6] !== "A" || columns[7] !== "ADM1" || columns[8] !== "CN" || !columns[10]) continue;
  const code = admin1ToNationalCode.get(columns[10]);
  if (!code) throw new Error(`Missing national code for GeoNames ADM1 row ${columns[0]}`);
  provinces.set(columns[10], {
    code,
    parent_code: "CN",
    name: chineseName(columns, "province"),
    longitude: Number(columns[5]),
    geoname_id: Number(columns[0]),
    level: "province",
  });
}

const cities = [];
for (const columns of rows) {
  if (columns[6] !== "A" || columns[7] !== "ADM2" || columns[8] !== "CN" || !columns[10] || !columns[11]) continue;
  const parent = provinces.get(columns[10]);
  if (!parent) throw new Error(`Missing ADM1 parent for GeoNames row ${columns[0]}`);
  const directCode = DIRECT_MUNICIPALITIES.get(columns[10])?.[1];
  const code = directCode ?? (/^\d{4}$/.test(columns[11]) ? `${columns[11]}00` : undefined);
  // GeoNames also labels some province-administered county-level units ADM2.
  // They have no four-digit prefecture code and are outside this catalog's scope.
  if (!code) continue;
  cities.push({
    code,
    parent_code: parent.code,
    name: chineseName(columns, "city"),
    longitude: Number(columns[5]),
    geoname_id: Number(columns[0]),
    level: "city",
  });
}

const records = [...provinces.values(), ...cities].sort((left, right) => left.code.localeCompare(right.code));
if (provinces.size < 30 || cities.length < 300) {
  throw new Error(`Unexpected GeoNames coverage: ${provinces.size} provinces and ${cities.length} cities`);
}
if (records.some((record) => !record.name || !Number.isFinite(record.longitude))) {
  throw new Error("Catalog contains an invalid name or longitude");
}

const catalog = {
  schema_version: 1,
  source: {
    name: "GeoNames",
    url: "https://download.geonames.org/export/dump/CN.zip",
    license: "CC BY 4.0",
    input_file: basename(inputPath),
    input_sha256: checksum,
  },
  records,
};

await writeFile(outputPath, `${JSON.stringify(catalog, null, 2)}\n`, "utf8");
console.log(`Wrote ${records.length} records to ${outputPath}`);
