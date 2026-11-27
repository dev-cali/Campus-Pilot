import { parseAnswer, statusCodes, type Answer } from "./ai-contract";
import {
  AI_BROWSER_TIMEOUT_MS,
  AI_INVALID_RESPONSE,
  AI_NETWORK_FAILURE,
  AI_REQUEST_TIMEOUT,
  AI_SLOW_NOTICE_MS,
  aiFailureForStatus,
  type AiFailure,
} from "./ai-errors";
import type { AiRequestLifecycle, RequestLease } from "./ai-request-lifecycle";

export type AiRequestResult =
  | { kind: "answer"; answer: Answer }
  | { kind: "failure"; failure: AiFailure };

type RequestOptions = {
  lifecycle: AiRequestLifecycle;
  fetcher?: typeof fetch;
  timeoutMs?: number;
  slowNoticeMs?: number;
  onSlow?: () => void;
};

/** Make one browser request; cancellation and deadlines never trigger retries. */
export async function requestAiAnswer(
  question: string,
  lease: RequestLease,
  options: RequestOptions,
): Promise<AiRequestResult | null> {
  const fetcher = options.fetcher ?? fetch;
  const timeoutMs = options.timeoutMs ?? AI_BROWSER_TIMEOUT_MS;
  const slowNoticeMs = options.slowNoticeMs ?? AI_SLOW_NOTICE_MS;
  let timedOut = false;
  const slowTimer = setTimeout(() => {
    if (options.lifecycle.isCurrent(lease)) options.onSlow?.();
  }, slowNoticeMs);
  const deadline = setTimeout(() => {
    if (!options.lifecycle.isCurrent(lease)) return;
    timedOut = true;
    lease.controller.abort();
  }, timeoutMs);

  try {
    const response = await fetcher("/api/ai/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal: lease.controller.signal,
    });
    if (!options.lifecycle.isCurrent(lease)) return null;

    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      // Ignore the body; it may contain private upstream details.
    }
    if (!options.lifecycle.isCurrent(lease)) return null;

    const answer = parseAnswer(payload);
    if (answer && statusCodes[answer.status] === response.status) {
      return { kind: "answer", answer };
    }
    return {
      kind: "failure",
      failure: response.status === 200 ? AI_INVALID_RESPONSE : aiFailureForStatus(response.status),
    };
  } catch {
    if (!options.lifecycle.isCurrent(lease)) return null;
    return { kind: "failure", failure: timedOut ? AI_REQUEST_TIMEOUT : AI_NETWORK_FAILURE };
  } finally {
    clearTimeout(slowTimer);
    clearTimeout(deadline);
  }
}
