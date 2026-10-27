// Mirrors ai/demo_api.py and ai/answer_service.py. This module contains no secrets.
export type AnswerStatus = "answered" | "insufficient_evidence" | "unavailable" | "denied";
export type Citation = {
  evidence_id: string;
  document_id: number;
  page_no: number;
  chunk_index: number;
  title: string;
  version: string;
  source_reference: string;
};
export type Answer = {
  status: AnswerStatus;
  answer: string;
  citations: Citation[];
  fictional: true;
};

export const statusLabels: Record<AnswerStatus, string> = {
  answered: "Answer from fictional sources",
  insufficient_evidence: "Not enough evidence",
  unavailable: "AI service unavailable",
  denied: "Request not permitted",
};
export const statusCodes: Record<AnswerStatus, number> = {
  answered: 200, insufficient_evidence: 200, unavailable: 503, denied: 403,
};

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function text(value: unknown, limit: number): value is string {
  return typeof value === "string" && value.trim().length > 0 && Array.from(value).length <= limit;
}
function integer(value: unknown, minimum: number): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= minimum;
}

export function parseQuestion(value: unknown): string | null {
  if (!record(value) || Object.keys(value).length !== 1 || !text(value.question, 2000)) return null;
  return value.question.trim();
}

export function parseAnswer(value: unknown): Answer | null {
  if (!record(value) || value.fictional !== true || !text(value.answer, 4000) ||
      typeof value.status !== "string" || !Object.hasOwn(statusCodes, value.status) ||
      !Array.isArray(value.citations) || value.citations.length > 3) return null;
  const status = value.status as AnswerStatus;
  if ((status === "answered") !== (value.citations.length > 0)) return null;
  const citations: Citation[] = [];
  const seen = new Set<string>();
  for (const item of value.citations) {
    if (!record(item) || !text(item.evidence_id, 20) || seen.has(item.evidence_id) ||
        !integer(item.document_id, 1) || !integer(item.page_no, 1) || !integer(item.chunk_index, 0) ||
        !text(item.title, 2000) || !text(item.version, 200) || !text(item.source_reference, 4000)) return null;
    seen.add(item.evidence_id);
    // Select only the fields in the actual backend citation contract.
    citations.push({ evidence_id: item.evidence_id, document_id: item.document_id,
      page_no: item.page_no, chunk_index: item.chunk_index, title: item.title,
      version: item.version, source_reference: item.source_reference });
  }
  return { status, answer: value.answer, citations, fictional: true };
}
