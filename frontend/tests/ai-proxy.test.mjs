// Uses the already-installed TypeScript compiler and Node's built-in test runner.
// Fetch is mocked: no backend or paid provider is contacted.
import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";

const compile = (source) => ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const moduleUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const contractUrl = moduleUrl(compile(await readFile(new URL("../lib/ai-contract.ts", import.meta.url), "utf8")));
const contract = await import(contractUrl);
const authUrl = moduleUrl(`export async function createClient() {
  return { auth: {
    getSession: async () => {
      globalThis.__supabaseAuthCalls.push("getSession");
      if (globalThis.__supabaseSessionThrows) throw new Error("private session failure");
      return globalThis.__supabaseSessionResult;
    },
    getClaims: async (token) => {
      globalThis.__supabaseAuthCalls.push(["getClaims", token]);
      if (globalThis.__supabaseClaimsThrows) throw new Error("private claims failure");
      return globalThis.__supabaseClaimsResult;
    },
  } };
}`);
const testAccessToken = "synthetic-campus-pilot-access-token";
globalThis.__supabaseAuthCalls = [];
globalThis.__supabaseSessionThrows = false;
globalThis.__supabaseClaimsThrows = false;
globalThis.__supabaseSessionResult = {
  data: { session: { access_token: testAccessToken } }, error: null,
};
globalThis.__supabaseClaimsResult = {
  data: { claims: { sub: "fictional-test-user", role: "authenticated" } }, error: null,
};
const route = compile(await readFile(new URL("../app/api/ai/ask/route.ts", import.meta.url), "utf8"))
  .replace(/(["'])@\/lib\/ai-contract\1/g, JSON.stringify(contractUrl))
  .replace(/(["'])@\/utils\/supabase\/server\1/g, JSON.stringify(authUrl));
const { POST } = await import(moduleUrl(route));
const answered = {
  status: "answered", answer: "Fictional source excerpt.", fictional: true,
  citations: [{ evidence_id: "e1", document_id: 103, page_no: 1, chunk_index: 0,
    title: "Fictional Enrollment", version: "v1", source_reference: "fictional://demo-campus/103/v1" }],
};
const request = (value, headers = {}) => new Request("http://localhost:3000/api/ai/ask", {
  method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(value),
});

test("question validation rejects empty, extra fields, and oversize; counts Unicode code points", () => {
  for (const value of [{ question: " " }, { question: 3 }, { question: "x", is_staff: true }, { question: "x".repeat(2001) }]) {
    assert.equal(contract.parseQuestion(value), null);
  }
  assert.equal(contract.parseQuestion({ question: "🎓".repeat(2000) }), "🎓".repeat(2000));
});

test("response validation enforces status, fictional marker, citation shape and invariants", () => {
  assert.deepEqual(contract.parseAnswer(answered), answered);
  for (const value of [{ ...answered, fictional: false }, { ...answered, status: "invented" },
    { ...answered, citations: [] }, { ...answered, citations: [answered.citations[0], answered.citations[0]] },
    { ...answered, status: "denied" }, { ...answered, citations: [{ ...answered.citations[0], page_no: true }] }]) {
    assert.equal(contract.parseAnswer(value), null);
  }
});

test("proxy cases never contact a real service", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalBase = process.env.AI_API_BASE_URL;
  const originalSecret = process.env.AI_DEMO_SHARED_SECRET;

  const testSecret = "a".repeat(64);

  process.env.AI_API_BASE_URL = "http://127.0.0.1:8012";
  process.env.AI_DEMO_SHARED_SECRET = testSecret;

  try {
    await t.test("answered and non-2xx backend statuses retain the actual contract", async () => {
      for (const status of ["answered", "insufficient_evidence", "denied", "unavailable"]) {
        const payload = status === "answered" ? answered : { status, answer: "Safe fallback.", fictional: true, citations: [] };
        globalThis.fetch = async (url, options) => {
          assert.equal(String(url), "http://127.0.0.1:8012/api/ai/ask");
          assert.deepEqual(JSON.parse(options.body), { question: "enrollment" });
          assert.equal(options.redirect, "error");
          assert.equal(options.cache, "no-store");
          assert.equal(
  new Headers(options.headers).get("X-AI-Demo-Secret"),
  testSecret
);
          assert.equal(
            new Headers(options.headers).get("Authorization"),
            `Bearer ${testAccessToken}`
          );
          return Response.json(payload, { status: contract.statusCodes[status] });
        };
        globalThis.__supabaseAuthCalls = [];
        const response = await POST(request({ question: " enrollment " }, {
          Origin: "http://127.0.0.1:3000", Host: "127.0.0.1:3000",
        }));
        assert.deepEqual(globalThis.__supabaseAuthCalls, [
          "getSession",
          ["getClaims", testAccessToken],
        ]);
        assert.equal(response.status, contract.statusCodes[status]);
        assert.deepEqual(await response.json(), payload);
        assert.equal(response.headers.get("cache-control"), "no-store");
      }
    });
    await t.test("invalid requests and cross-origin calls never fetch", async () => {
      let calls = 0;
      globalThis.fetch = async () => { calls++; throw new Error("unexpected_fetch"); };
      assert.equal((await POST(request({ question: "" }))).status, 422);
      assert.equal((await POST(request({ question: "x", is_staff: true }))).status, 422);
      assert.equal((await POST(request({ question: "x" }, { Origin: "http://other.invalid" }))).status, 403);
      assert.equal((await POST(request({ question: "x".repeat(20000) }))).status, 422);
      assert.equal(calls, 0);
    });
    await t.test("anonymous and invalid claims are rejected before backend access", async () => {
      let calls = 0;
      globalThis.fetch = async () => { calls++; throw new Error("unexpected_fetch"); };
      const rejected = [
        { data: null, error: { message: "sanitized test error" } },
        { data: { claims: { role: "authenticated" } }, error: null },
        { data: { claims: { sub: "anonymous", role: "authenticated", is_anonymous: true } }, error: null },
      ];
      try {
        for (const result of rejected) {
          globalThis.__supabaseClaimsResult = result;
          const response = await POST(request({ question: "enrollment" }));
          assert.equal(response.status, 401);
          assert.match((await response.json()).detail, /sign in/i);
        }
        assert.equal(calls, 0);
      } finally {
        globalThis.__supabaseClaimsResult = {
          data: { claims: { sub: "fictional-test-user", role: "authenticated" } }, error: null,
        };
      }
    });
    await t.test("missing sessions and access tokens are rejected before backend access", async () => {
      let calls = 0;
      globalThis.fetch = async () => { calls++; throw new Error("unexpected_fetch"); };
      const invalidSessions = [
        { data: { session: null }, error: null },
        { data: { session: { access_token: "" } }, error: null },
        { data: { session: { access_token: null } }, error: null },
        { data: { session: { access_token: testAccessToken } }, error: { message: "session error" } },
      ];
      try {
        for (const session of invalidSessions) {
          globalThis.__supabaseSessionResult = session;
          globalThis.__supabaseAuthCalls = [];
          const response = await POST(request({ question: "enrollment" }));
          assert.equal(response.status, 401);
          assert.match((await response.json()).detail, /sign in/i);
        }
        assert.equal(calls, 0);
      } finally {
        globalThis.__supabaseSessionResult = {
          data: { session: { access_token: testAccessToken } }, error: null,
        };
      }
    });
    await t.test("authentication service exceptions are sanitized", async () => {
      let calls = 0;
      globalThis.fetch = async () => { calls++; throw new Error("unexpected_fetch"); };
      for (const flag of ["__supabaseSessionThrows", "__supabaseClaimsThrows"]) {
        globalThis[flag] = true;
        const response = await POST(request({ question: "enrollment" }));
        assert.equal(response.status, 503);
        assert.doesNotMatch(await response.text(), /private .* failure/);
        globalThis[flag] = false;
      }
      assert.equal(calls, 0);
    });
    await t.test("network, timeout, invalid JSON and status mismatch are sanitized", async () => {
      for (const fake of [
        async () => { throw new Error("private upstream detail"); },
        async () => { throw new DOMException("private timeout", "AbortError"); },
        async () => new Response("private invalid JSON", { headers: { "Content-Type": "application/json" } }),
        async () => Response.json(answered, { status: 503 }),
        async () => new Response("<html>private error</html>"),
      ]) {
        globalThis.fetch = fake;
        const response = await POST(request({ question: "enrollment" }));
        assert.equal(response.status, 502);
        assert.doesNotMatch(await response.text(), /private/);
      }
    });
    await t.test("backend validation errors do not echo request or upstream data", async () => {
      globalThis.fetch = async () => Response.json({ detail: "private input" }, { status: 422 });
      const response = await POST(request({ question: "enrollment" }));
      assert.equal(response.status, 422);
      assert.doesNotMatch(await response.text(), /private/);
    });
      await t.test("missing shared secret prevents upstream requests", async () => {
      let calls = 0;

      globalThis.fetch = async () => {
        calls++;
        throw new Error("unexpected_fetch");
      };

      delete process.env.AI_DEMO_SHARED_SECRET;

      try {
        const response = await POST(
          request({ question: "enrollment" })
        );

        assert.equal(response.status, 503);
        assert.equal(calls, 0);
      } finally {
        process.env.AI_DEMO_SHARED_SECRET = testSecret;
      }
    });
        await t.test("backend rate limit returns sanitized 429", async () => {
      globalThis.fetch = async () =>
        Response.json(
          { detail: "private rate limit information" },
          { status: 429 }
        );

      const response = await POST(
        request({ question: "enrollment" })
      );

      assert.equal(response.status, 429);
      assert.doesNotMatch(await response.text(), /private/);
      assert.equal(
        response.headers.get("cache-control"),
        "no-store"
      );
    });
  } finally {
    globalThis.fetch = originalFetch;
    delete globalThis.__supabaseClaimsResult;
    delete globalThis.__supabaseSessionResult;
    delete globalThis.__supabaseAuthCalls;
    delete globalThis.__supabaseSessionThrows;
    delete globalThis.__supabaseClaimsThrows;

    if (originalBase === undefined) {
      delete process.env.AI_API_BASE_URL;
    } else {
      process.env.AI_API_BASE_URL = originalBase;
    }

    if (originalSecret === undefined) {
      delete process.env.AI_DEMO_SHARED_SECRET;
    } else {
      process.env.AI_DEMO_SHARED_SECRET = originalSecret;
    }
  }
});
