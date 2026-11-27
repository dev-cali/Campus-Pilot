import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const moduleUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const loadTypeScript = async (path, imports = {}) => {
  const source = await readFile(new URL(path, import.meta.url), "utf8");
  let javascript = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  for (const [specifier, targetUrl] of Object.entries(imports)) {
    javascript = javascript.replaceAll(JSON.stringify(specifier), JSON.stringify(targetUrl));
  }
  return import(moduleUrl(javascript));
};

const { AiRequestLifecycle } = await loadTypeScript("../lib/ai-request-lifecycle.ts");
const { shouldSubmitOnEnter } = await loadTypeScript("../lib/ai-composer.ts");
const errors = await loadTypeScript("../lib/ai-errors.ts");
const contractSource = await readFile(new URL("../lib/ai-contract.ts", import.meta.url), "utf8");
const contractJavascript = ts.transpileModule(contractSource, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const contractUrl = moduleUrl(contractJavascript);
const errorSource = await readFile(new URL("../lib/ai-errors.ts", import.meta.url), "utf8");
const errorJavascript = ts.transpileModule(errorSource, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const errorUrl = moduleUrl(errorJavascript);
const lifecycleSource = await readFile(new URL("../lib/ai-request-lifecycle.ts", import.meta.url), "utf8");
const lifecycleJavascript = ts.transpileModule(lifecycleSource, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const lifecycleUrl = moduleUrl(lifecycleJavascript);
const { requestAiAnswer } = await loadTypeScript("../lib/ai-request.ts", {
  "./ai-contract": contractUrl,
  "./ai-errors": errorUrl,
  "./ai-request-lifecycle": lifecycleUrl,
});
const answerPayload = {
  status: "answered", answer: "Fictional evidence answer.", fictional: true,
  citations: [{ evidence_id: "e1", document_id: 107, page_no: 1, chunk_index: 0,
    title: "Fictional Academic Calendar", version: "v1", source_reference: "fictional://demo-campus/107/v1" }],
};
const jsonResponse = (status, body) => new Response(JSON.stringify(body), {
  status, headers: { "Content-Type": "application/json" },
});

test("request lifecycle is single-flight and ignores cancelled late completions", () => {
  const lifecycle = new AiRequestLifecycle();
  const first = lifecycle.begin();
  assert.ok(first);
  assert.equal(lifecycle.begin(), null);
  assert.equal(lifecycle.isCurrent(first), true);

  const cancelled = lifecycle.cancel();
  assert.equal(cancelled, first);
  assert.equal(first.controller.signal.aborted, true);
  assert.equal(lifecycle.isCurrent(first), false);
  assert.equal(lifecycle.finish(first), false);

  const second = lifecycle.begin();
  assert.ok(second);
  assert.ok(second.id > first.id);
  assert.equal(lifecycle.finish(first), false);
  assert.equal(lifecycle.finish(second), true);
  const third = lifecycle.begin();
  assert.ok(third);
  lifecycle.cancel();
});

test("request deadlines fit the proxy and configured function limits", () => {
  assert.ok(errors.AI_BROWSER_TIMEOUT_MS > 75_000);
  assert.ok(errors.AI_BROWSER_TIMEOUT_MS < 120_000);
  assert.ok(errors.AI_SLOW_NOTICE_MS < errors.AI_BROWSER_TIMEOUT_MS);
});

test("composer submits on Enter, preserves Shift+Enter, and ignores IME composition", () => {
  const base = { key: "Enter", shiftKey: false, isComposing: false, pending: false };
  assert.equal(shouldSubmitOnEnter(base), true);
  assert.equal(shouldSubmitOnEnter({ ...base, shiftKey: true }), false);
  assert.equal(shouldSubmitOnEnter({ ...base, isComposing: true }), false);
  assert.equal(shouldSubmitOnEnter({ ...base, keyCode: 229 }), false);
  assert.equal(shouldSubmitOnEnter({ ...base, pending: true }), false);
  assert.equal(shouldSubmitOnEnter({ ...base, key: "a" }), false);
});

test("HTTP failures have safe, distinct next steps", () => {
  assert.equal(errors.aiFailureForStatus(401).action, "signIn");
  assert.match(errors.aiFailureForStatus(401).message, /sign in/i);
  assert.equal(errors.aiFailureForStatus(422).action, undefined);
  assert.match(errors.aiFailureForStatus(422).message, /2,000-character/);
  assert.equal(errors.aiFailureForStatus(403).action, undefined);
  assert.equal(errors.aiFailureForStatus(429).action, "retry");
  for (const status of [502, 503, 504]) {
    const failure = errors.aiFailureForStatus(status);
    assert.equal(failure.action, "retry");
    assert.match(failure.message, /temporarily unavailable|taking too long/i);
  }
  for (const failure of [errors.AI_NETWORK_FAILURE, errors.AI_INVALID_RESPONSE, errors.AI_REQUEST_TIMEOUT]) {
    assert.equal(failure.action, "retry");
    assert.doesNotMatch(failure.message, /provider payload|stack trace|api key|bearer/i);
  }
});

test("request wrapper validates successful contract and preserves insufficiency separately", async () => {
  const lifecycle = new AiRequestLifecycle();
  const successLease = lifecycle.begin();
  let requestBody;
  const success = await requestAiAnswer("question", successLease, {
    lifecycle,
    fetcher: async (_url, options) => {
      requestBody = JSON.parse(options.body);
      assert.equal(options.method, "POST");
      assert.equal(options.signal, successLease.controller.signal);
      return jsonResponse(200, answerPayload);
    },
  });
  assert.deepEqual(requestBody, { question: "question" });
  assert.equal(success.kind, "answer");
  assert.equal(success.answer.citations[0].document_id, 107);
  assert.equal(lifecycle.finish(successLease), true);

  const unsupportedLease = lifecycle.begin();
  const unsupported = await requestAiAnswer("unsupported", unsupportedLease, {
    lifecycle,
    fetcher: async () => jsonResponse(200, {
      status: "insufficient_evidence", answer: "No verified evidence.", fictional: true, citations: [],
    }),
  });
  assert.equal(unsupported.kind, "answer");
  assert.equal(unsupported.answer.status, "insufficient_evidence");
  assert.equal(lifecycle.finish(unsupportedLease), true);

  const deniedLease = lifecycle.begin();
  const denied = await requestAiAnswer("restricted request", deniedLease, {
    lifecycle,
    fetcher: async () => jsonResponse(403, {
      status: "denied", answer: "This public demo cannot provide that information.", fictional: true, citations: [],
    }),
  });
  assert.equal(denied.kind, "answer");
  assert.equal(denied.answer.status, "denied");
  lifecycle.finish(deniedLease);

  const unavailableLease = lifecycle.begin();
  const unavailable = await requestAiAnswer("supported request", unavailableLease, {
    lifecycle,
    fetcher: async () => jsonResponse(503, {
      status: "unavailable", answer: "The fictional demo cannot verify an answer right now.", fictional: true, citations: [],
    }),
  });
  assert.equal(unavailable.kind, "answer");
  assert.equal(unavailable.answer.status, "unavailable");
  lifecycle.finish(unavailableLease);
});

test("request wrapper sanitizes HTTP errors, malformed bodies, and network failures", async () => {
  const lifecycle = new AiRequestLifecycle();
  for (const [status, expectedAction] of [[401, "signIn"], [429, "retry"], [503, "retry"], [504, "retry"]]) {
    const lease = lifecycle.begin();
    const outcome = await requestAiAnswer("question", lease, {
      lifecycle, fetcher: async () => jsonResponse(status, { detail: "PRIVATE_BACKEND_DETAIL" }),
    });
    assert.equal(outcome.kind, "failure");
    assert.equal(outcome.failure.action, expectedAction);
    assert.doesNotMatch(outcome.failure.message, /PRIVATE_BACKEND_DETAIL/);
    lifecycle.finish(lease);
  }

  const invalidLease = lifecycle.begin();
  const invalid = await requestAiAnswer("question", invalidLease, {
    lifecycle, fetcher: async () => new Response("PRIVATE_INVALID_BODY", { status: 200 }),
  });
  assert.equal(invalid.failure.message, errors.AI_INVALID_RESPONSE.message);
  lifecycle.finish(invalidLease);

  const networkLease = lifecycle.begin();
  const network = await requestAiAnswer("question", networkLease, {
    lifecycle, fetcher: async () => { throw new Error("PRIVATE_NETWORK_DETAIL"); },
  });
  assert.equal(network.failure.message, errors.AI_NETWORK_FAILURE.message);
  assert.doesNotMatch(network.failure.message, /PRIVATE_NETWORK_DETAIL/);
  lifecycle.finish(networkLease);
});

test("request deadline announces slowness and aborts without retrying", async () => {
  const lifecycle = new AiRequestLifecycle();
  const lease = lifecycle.begin();
  let slowNotice = false;
  const outcome = await requestAiAnswer("question", lease, {
    lifecycle,
    slowNoticeMs: 2,
    timeoutMs: 12,
    onSlow: () => { slowNotice = true; },
    fetcher: async (_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")), { once: true });
    }),
  });
  assert.equal(slowNotice, true);
  assert.equal(lease.controller.signal.aborted, true);
  assert.equal(outcome.kind, "failure");
  assert.equal(outcome.failure.message, errors.AI_REQUEST_TIMEOUT.message);
  assert.equal(lifecycle.finish(lease), true);
});

test("superseded response is discarded after cancellation", async () => {
  const lifecycle = new AiRequestLifecycle();
  const lease = lifecycle.begin();
  let resolveFetch;
  const response = requestAiAnswer("old question", lease, {
    lifecycle,
    fetcher: () => new Promise((resolve) => { resolveFetch = resolve; }),
  });
  lifecycle.cancel();
  resolveFetch(jsonResponse(200, answerPayload));
  assert.equal(await response, null);
  assert.equal(lifecycle.finish(lease), false);
});
