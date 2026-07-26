import assert from "node:assert/strict";
import { once } from "node:events";
import { test } from "node:test";

import { createAppServer } from "../src/server.js";

test("serves health and rejects malformed chart requests", async (context) => {
  const server = createAppServer().listen(0, "127.0.0.1");
  context.after(() => server.close());
  await once(server, "listening");
  const address = server.address();
  assert(address && typeof address === "object");
  const origin = `http://127.0.0.1:${address.port}`;

  const health = await fetch(`${origin}/health`);
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { status: "ok" });

  const invalid = await fetch(`${origin}/chart`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ birth_date: "1998-12-13" }),
  });
  assert.equal(invalid.status, 422);
  assert.equal((await invalid.json() as { error: { code: string } }).error.code, "INVALID_REQUEST");
});
