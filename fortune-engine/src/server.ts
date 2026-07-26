import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { randomUUID } from "node:crypto";
import { pathToFileURL } from "node:url";

import { calculateChart } from "./chart.js";
import { MAX_REQUEST_BYTES, parseChartRequest, RequestValidationError } from "./schema.js";

interface PublicError {
  error: { code: string; message: string; request_id: string };
}

function sendJson(response: ServerResponse, status: number, body: unknown): void {
  response.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(body));
}

async function readJson(request: IncomingMessage): Promise<unknown> {
  const declaredLength = Number(request.headers["content-length"] ?? 0);
  if (declaredLength > MAX_REQUEST_BYTES) {
    throw new RequestValidationError("Request body exceeds 16 KB");
  }

  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.length;
    if (size > MAX_REQUEST_BYTES) {
      throw new RequestValidationError("Request body exceeds 16 KB");
    }
    chunks.push(buffer);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new RequestValidationError("Request body must contain valid JSON");
  }
}

export function createAppServer() {
  return createServer(async (request, response) => {
    const requestId = randomUUID();
    const startedAt = performance.now();
    let status = 500;
    try {
      if (request.method === "GET" && request.url === "/health") {
        status = 200;
        return sendJson(response, status, { status: "ok" });
      }
      if (request.method !== "POST" || request.url !== "/chart") {
        status = 404;
        return sendJson(response, status, { error: { code: "NOT_FOUND", message: "Not found", request_id: requestId } });
      }
      if (!request.headers["content-type"]?.toLowerCase().startsWith("application/json")) {
        throw new RequestValidationError("Content-Type must be application/json");
      }
      const input = parseChartRequest(await readJson(request));
      const result = calculateChart(input);
      status = 200;
      return sendJson(response, status, result);
    } catch (error) {
      if (error instanceof RequestValidationError || error instanceof RangeError) {
        status = 422;
        const body: PublicError = {
          error: { code: "INVALID_REQUEST", message: error.message, request_id: requestId },
        };
        return sendJson(response, status, body);
      }
      status = 500;
      const body: PublicError = {
        error: { code: "CALCULATION_FAILED", message: "Unable to calculate chart", request_id: requestId },
      };
      return sendJson(response, status, body);
    } finally {
      console.info(JSON.stringify({ request_id: requestId, method: request.method, path: request.url, status, duration_ms: Math.round(performance.now() - startedAt) }));
    }
  });
}

const isMainModule = process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href;

if (isMainModule) {
  const port = Number(process.env.PORT ?? 8080);
  createAppServer().listen(port, "0.0.0.0", () => {
    console.info(JSON.stringify({ event: "server.started", port }));
  });
}
