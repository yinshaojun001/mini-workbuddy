export const MAX_REQUEST_BYTES = 16 * 1024;

export type Gender = "male" | "female";

export interface ChartRequest {
  birth_date: string;
  birth_time: string | null;
  birth_time_unknown: boolean;
  gender: Gender;
  longitude: number;
  true_solar_time: boolean;
}

const ALLOWED_FIELDS = new Set([
  "birth_date",
  "birth_time",
  "birth_time_unknown",
  "gender",
  "longitude",
  "true_solar_time",
]);

export class RequestValidationError extends Error {
  readonly code = "INVALID_REQUEST";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseChartRequest(value: unknown): ChartRequest {
  if (!isRecord(value)) {
    throw new RequestValidationError("Request body must be a JSON object");
  }

  const unknownFields = Object.keys(value).filter((key) => !ALLOWED_FIELDS.has(key));
  if (unknownFields.length > 0) {
    throw new RequestValidationError(`Unknown field: ${unknownFields[0]}`);
  }

  const { birth_date, birth_time, birth_time_unknown, gender, longitude, true_solar_time } = value;
  if (typeof birth_date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(birth_date)) {
    throw new RequestValidationError("birth_date must use YYYY-MM-DD");
  }
  const [year, month, day] = birth_date.split("-").map(Number);
  const parsedDate = new Date(Date.UTC(year!, month! - 1, day));
  if (
    year! < 1900 ||
    year! > 2100 ||
    parsedDate.getUTCFullYear() !== year ||
    parsedDate.getUTCMonth() + 1 !== month ||
    parsedDate.getUTCDate() !== day
  ) {
    throw new RequestValidationError("birth_date is outside the supported range or invalid");
  }
  if (gender !== "male" && gender !== "female") {
    throw new RequestValidationError("gender must be male or female");
  }
  if (typeof birth_time_unknown !== "boolean" || typeof true_solar_time !== "boolean") {
    throw new RequestValidationError("time flags must be boolean");
  }
  if (typeof longitude !== "number" || !Number.isFinite(longitude) || longitude < 73 || longitude > 135) {
    throw new RequestValidationError("longitude must be a mainland China coordinate");
  }

  if (birth_time_unknown) {
    if (birth_time !== null || true_solar_time) {
      throw new RequestValidationError("unknown birth time requires null time and disables true solar time");
    }
  } else if (typeof birth_time !== "string" || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(birth_time)) {
    throw new RequestValidationError("birth_time must use HH:mm");
  }

  return {
    birth_date,
    birth_time: birth_time as string | null,
    birth_time_unknown,
    gender,
    longitude,
    true_solar_time,
  };
}
