"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type MouseEvent, type ReactNode } from "react";
import Link from "next/link";
import {
  parseQuestion,
  statusLabels,
  type Answer,
} from "@/lib/ai-contract";
import {
  AI_INVALID_RESPONSE,
  type AiFailure,
  type AiFailureAction,
} from "@/lib/ai-errors";
import { requestAiAnswer } from "@/lib/ai-request";
import { shouldSubmitOnEnter } from "@/lib/ai-composer";
import { AiRequestLifecycle, type RequestLease } from "@/lib/ai-request-lifecycle";
import CampusHeader from "../components/campus-header";
import "../home.css";
import styles from "./assistant.module.css";

type Category = "News" | "Scholarships" | "Policies" | "Events" | "Documents" | "Academics";
type ChatEntry = {
  id: string;
  question: string;
  answer?: Answer;
  error?: string;
  errorAction?: AiFailureAction;
};
type Conversation = {
  id: string;
  title: string;
  category: Category | null;
  entries: ChatEntry[];
};

const CATEGORIES: Category[] = ["News", "Scholarships", "Policies", "Events", "Documents", "Academics"];
const SUGGESTED_QUESTIONS = [
  "When does Term A enrollment open?",
  "What GPA and unit minimum apply to Lakbay?",
  "How do I request a transcript?",
  "How much is tuition for 18 units before scholarships?",
];
const PLACEHOLDERS: Record<Category | "home", string> = {
  home: "Ask CampusPilot...",
  News: "Ask about campus news...",
  Scholarships: "Ask about scholarships...",
  Policies: "Ask about policies...",
  Events: "Ask about events...",
  Documents: "Ask about documents...",
  Academics: "Ask about academics...",
};

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const common = {
    width: size, height: size, viewBox: "0 0 24 24", fill: "none",
    stroke: "currentColor", strokeWidth: 2,
    strokeLinecap: "round" as const, strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };
  const shapes: Record<string, ReactNode> = {
    filter: <path d="M4 7h16M7 12h10M10 17h4" />,
    plus: <path d="M12 5v14M5 12h14" />,
    send: <><path d="M3 4l18 8-18 8 3-8z" /><path d="M6 12h15" /></>,
    News: <><path d="M4 4h16v16H4z" /><path d="M8 8h8M8 12h8M8 16h5" /></>,
    Scholarships: <><circle cx="12" cy="12" r="9" /><path d="M12 6v12M15 9c-3-2-6 0-6 2s6 1 6 4-4 3-6 1" /></>,
    Policies: <><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M9 8h6M9 12h6M9 16h3" /></>,
    Events: <><rect x="4" y="5" width="16" height="16" rx="3" /><path d="M8 3v4M16 3v4M4 11h16" /></>,
    Documents: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v4h4M9 13h6M9 17h6" /></>,
    Academics: <><path d="M2 9l10-5 10 5-10 5z" /><path d="M6 12v5c3 2 9 2 12 0v-5M22 9v6" /></>,
  };
  return <svg {...common}>{shapes[name] ?? null}</svg>;
}

export default function Assistant({
  initialCategory = null,
}: {
  initialCategory?: Category | null;
}) {
  const [category, setCategory] = useState<Category | null>(initialCategory);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [slowRequest, setSlowRequest] = useState(false);
  const [error, setError] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const requestLifecycle = useRef(new AiRequestLifecycle());
  const activeRequest = useRef<{
    lease: RequestLease;
    chatId: string;
    entryId: string;
  } | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => () => {
    requestLifecycle.current.cancel();
    activeRequest.current = null;
  }, []);


  const current = conversations.find((chat) => chat.id === currentId) ?? null;
  const entries = current?.entries ?? [];
  const visibleConversations = filterCategory && category
    ? conversations.filter((chat) => chat.category === category)
    : conversations;
  const shown = showAll ? visibleConversations : visibleConversations.slice(0, 7);
  const questionLength = Array.from(question).length;
  const questionTooLong = questionLength > 2000;
  const questionError = error || (questionTooLong ? "Questions must be no longer than 2,000 characters." : "");
  const latestEntry = entries.at(-1);
  const citationCount = latestEntry?.answer?.citations.length ?? 0;
  const citationAnnouncement = citationCount === 0 ? "No source citations."
    : citationCount === 1 ? "1 source citation."
      : `${citationCount} source citations.`;
  const liveAnnouncement = pending
    ? slowRequest ? "This request is taking longer than usual." : "Processing your question."
    : latestEntry?.answer
      ? `${statusLabels[latestEntry.answer.status]}. ${citationAnnouncement}`
      : "";

  function updateEntry(chatId: string, entryId: string, update: Partial<ChatEntry>) {
    setConversations((previous) => previous.map((chat) => chat.id === chatId ? {
      ...chat,
      entries: chat.entries.map((entry) => entry.id === entryId ? { ...entry, ...update } : entry),
    } : chat));
  }

  function cancelActiveRequest(message?: string, action?: AiFailureAction) {
    const request = activeRequest.current;
    const lease = requestLifecycle.current.cancel();
    if (!request || !lease || lease.id !== request.lease.id) return;

    activeRequest.current = null;
    setPending(false);
    setSlowRequest(false);
    if (message) updateEntry(request.chatId, request.entryId, { error: message, errorAction: action });
  }

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [currentId, entries.length, pending]);

  function newChat() {
    cancelActiveRequest(
      "Waiting stopped because you started a new chat. The backend may still be processing; you can retry this question later.",
      "retry",
    );
    setCurrentId(null);
    setCategory(null);
    setQuestion("");
    setError("");
    inputRef.current?.focus();
  }

  function selectCategory(next: Category) {
    cancelActiveRequest(
      "Waiting stopped because you changed the selected category. The backend may still be processing; you can retry this question later.",
      "retry",
    );
    setCategory((previous) => previous === next ? null : next);
    setCurrentId(null);
    setError("");
    inputRef.current?.focus();
  }

  function handleHeaderCategory(event: MouseEvent<HTMLAnchorElement>, next: Category | null) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    if (category === next) return;
    if (next === null) newChat();
    else selectCategory(next);
  }

  function openConversation(chat: Conversation) {
    cancelActiveRequest(
      "Waiting stopped because you opened another conversation. The backend may still be processing; you can retry this question later.",
      "retry",
    );
    setCurrentId(chat.id);
    setCategory(chat.category);
    setError("");
  }

  async function sendQuestion(chatId: string, entryId: string, submittedQuestion: string) {
    const lease = requestLifecycle.current.begin();
    if (!lease) return;

    activeRequest.current = { lease, chatId, entryId };
    setPending(true);
    setSlowRequest(false);
    setError("");
    let result: Answer | null = null;
    let failure: AiFailure | null = null;

    try {
      const outcome = await requestAiAnswer(submittedQuestion, lease, {
        lifecycle: requestLifecycle.current,
        onSlow: () => setSlowRequest(true),
      });
      if (outcome?.kind === "answer") result = outcome.answer;
      else if (outcome?.kind === "failure") failure = outcome.failure;
    } catch {
      if (requestLifecycle.current.isCurrent(lease)) failure = AI_INVALID_RESPONSE;
    } finally {
      if (requestLifecycle.current.finish(lease)) {
        activeRequest.current = null;
        setPending(false);
        setSlowRequest(false);
        updateEntry(chatId, entryId, {
          ...(result ? { answer: result, error: undefined, errorAction: undefined } : {}),
          ...(failure ? { error: failure.message, errorAction: failure.action } : {}),
        });
      }
    }
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (requestLifecycle.current.isBusy()) return;

    setError("");
    const submittedQuestion = inputRef.current?.value ?? question;
    setQuestion(submittedQuestion);
    const validated = parseQuestion({ question: submittedQuestion });
    if (!validated) {
      setError("Enter a question of 1–2,000 characters.");
      return;
    }

    const chatId = currentId ?? crypto.randomUUID();
    const entryId = crypto.randomUUID();
    const newEntry: ChatEntry = { id: entryId, question: validated };
    if (!currentId) {
      setConversations((previous) => [
        { id: chatId, title: validated, category, entries: [newEntry] },
        ...previous,
      ]);
      setCurrentId(chatId);
    } else {
      setConversations((previous) => previous.map((chat) =>
        chat.id === chatId ? { ...chat, entries: [...chat.entries, newEntry] } : chat
      ));
    }
    setQuestion("");
    await sendQuestion(chatId, entryId, validated);
  }

  async function retryQuestion(chatId: string, entryId: string, originalQuestion: string) {
    if (requestLifecycle.current.isBusy()) return;
    updateEntry(chatId, entryId, { answer: undefined, error: undefined, errorAction: undefined });
    await sendQuestion(chatId, entryId, originalQuestion);
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (!shouldSubmitOnEnter({
      key: event.key,
      shiftKey: event.shiftKey,
      isComposing: event.nativeEvent.isComposing,
      keyCode: event.nativeEvent.keyCode,
      pending,
    })) return;
    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }

  return (
    <div className={`page ${styles.page} ${styles.mobileShell}`}>
      <CampusHeader
        active="ai"
        onAssistantClick={(event) => handleHeaderCategory(event, null)}
      />

      <div className="layout">
        <aside className="savedpanel" aria-label="Conversation history">
          <div className="shead">
            <h2>Saved prompts</h2>
            <button type="button" className="filt" title="Filter by selected category"
              aria-label={filterCategory ? "Show all conversations" : "Filter conversations by category"}
              aria-pressed={filterCategory} onClick={() => setFilterCategory((value) => !value)}>
              <Icon name="filter" />
            </button>
          </div>
          <button type="button" className="newchat" onClick={newChat}>
            <Icon name="plus" /> New chat
          </button>
          <ul id="saved">
            {shown.length === 0 && <li className="empty">No conversations yet. Ask something!</li>}
            {shown.map((chat) => <li key={chat.id} className={chat.id === currentId ? "sel" : ""}>
              <button type="button" className="qbtn" title={chat.title}
                onClick={() => openConversation(chat)}>
                <span>{chat.title}</span>
              </button>
              <button type="button" className="del" aria-label={`Delete ${chat.title}`}
                onClick={() => {
                  if (activeRequest.current?.chatId === chat.id) {
                    cancelActiveRequest(
                      "Waiting stopped because this conversation was deleted. The backend may still be processing.",
                    );
                  }
                  setConversations((previous) => previous.filter((item) => item.id !== chat.id));
                  if (currentId === chat.id) setCurrentId(null);
                }}>×</button>
            </li>)}
          </ul>
          <div className="sfoot">
            {visibleConversations.length > 7 && <button type="button" className="link"
              onClick={() => setShowAll((value) => !value)}>{showAll ? "Show less" : "View all"}</button>}
            <button type="button" className="link" disabled={conversations.length === 0}
              onClick={() => setConfirmOpen(true)}>Clear</button>
          </div>
        </aside>

        <main className="card">
          <nav className={styles.categoryNav} aria-label="Assistant categories">
            {CATEGORIES.map((item) => (
              <button
                key={item}
                type="button"
                className="cat"
                aria-pressed={category === item}
                onClick={() => selectCategory(item)}
              >
                <Icon name={item} /> {item}
              </button>
            ))}
          </nav>
          <section className="main">
            {entries.length === 0 && <div className="stage">
              <h2 className="news-heading">CampusPilot AI Assistant</h2>
              <p style={{ textAlign: "center", margin: "12px auto", maxWidth: 540 }}>
                Ask a question and explore the evidence. Categories help frame your prompt; they do not filter the backend sources.
              </p>
              <div className={styles.suggestions} role="group" aria-label="Suggested questions">
                {SUGGESTED_QUESTIONS.map((suggestion) => (
                  <button key={suggestion} type="button" onClick={() => {
                    setQuestion(suggestion);
                    inputRef.current?.focus();
                  }}>{suggestion}</button>
                ))}
              </div>
              <aside className={styles.notice}>
                <strong>Fictional data only.</strong> This academic demonstration does not provide
                official university advice. Do not enter private student information. A successful
                answer requires a configured provider; the assistant may safely decline when evidence is missing.
              </aside>
            </div>}
            {category && <div className="cathead"><h2>{category}</h2><p>Use this category to frame your prompt. The backend uses its available public evidence.</p></div>}
            <div className={`chat${entries.length ? " on" : ""}`} ref={chatRef} aria-live="off" aria-busy={pending}>
              {entries.map((entry) => <div key={entry.id} style={{ display: "flex", flexDirection: "column" }}>
                <div className="msg me">{entry.question}</div>
                {entry.answer && <div className="msg">
                  <strong>{statusLabels[entry.answer.status]}</strong>
                  <p className={styles.answer}>{entry.answer.answer}</p>
                  {entry.answer.status === "answered" && <div className={styles.sources}>
                    <h3>Sources supplied by the backend</h3>
                    <ol>{entry.answer.citations.map((citation) => <li key={citation.evidence_id}>
                      <strong>[{citation.evidence_id}] {citation.title}</strong>
                      <p>Document {citation.document_id} · Page {citation.page_no} · Version {citation.version} · Chunk {citation.chunk_index}</p>
                      <p className={styles.reference}>{citation.source_reference}</p>
                    </li>)}</ol>
                    <p className={styles.hint}>Source references are fictional identifiers, not links. Matching a quotation does not prove that it fully answers your question.</p>
                  </div>}
                  {entry.answer.status === "unavailable" && <button type="button" className={styles.retry}
                    disabled={pending} onClick={() => void retryQuestion(currentId ?? "", entry.id, entry.question)}>
                    Retry this question
                  </button>}
                </div>}
                {entry.error && <div className="msg" role="alert">
                  <p className={styles.error}>{entry.error}</p>
                  {entry.errorAction === "signIn" && <Link className={styles.retry} href="/login">Sign in again</Link>}
                  {entry.errorAction === "retry" && <button type="button" className={styles.retry}
                    disabled={pending} onClick={() => void retryQuestion(currentId ?? "", entry.id, entry.question)}>
                    Try again
                  </button>}
                </div>}
              </div>)}
              {pending && <div className={`msg ${styles.pending}`}>
                <span>{slowRequest ? "This is taking longer than usual. Please keep waiting or stop waiting." : "Processing your question…"}</span>
                <button type="button" className={styles.stop} onClick={() => cancelActiveRequest(
                  "Waiting stopped. The backend may still be processing; you can retry this question manually.", "retry",
                )}>Stop waiting</button>
              </div>}
            </div>
            {questionError && <p id="question-error" className={styles.error} role="alert">{questionError}</p>}
            <form className="ask" onSubmit={ask} noValidate>
              <textarea ref={inputRef} id="question" name="question" rows={1}
                placeholder={PLACEHOLDERS[category ?? "home"]}
                aria-label="Your university question"
                aria-describedby={questionError ? "question-help question-error" : "question-help"}
                aria-invalid={Boolean(questionError)} autoComplete="off"
                value={question} disabled={pending}
                onChange={(event) => {
                  setQuestion(event.target.value);
                  if (error) setError("");
                }}
                onKeyDown={handleComposerKeyDown} />
              <button type="submit" aria-label="Ask CampusPilot" disabled={pending || !parseQuestion({ question })}>
                <Icon name="send" size={20} />
              </button>
            </form>
            <p id="question-help" className={styles.hint}>
              {questionLength.toLocaleString()} / 2,000 characters · Enter to send, Shift+Enter for a new line.
            </p>
          </section>
        </main>
      </div>

      <div className={styles.srOnly} role="status" aria-live="polite" aria-atomic="true">
        {liveAnnouncement}
      </div>

      <div className={`modal-overlay${confirmOpen ? " open" : ""}`}
        onMouseDown={(event) => { if (event.target === event.currentTarget) setConfirmOpen(false); }}>
        {confirmOpen && <div className="modal-card" role="dialog" aria-modal="true"
          aria-labelledby="clear-title" aria-describedby="clear-description">
          <h3 id="clear-title">Clear History?</h3>
          <p id="clear-description">Clear all conversations from this page session?</p>
          <div className="modal-actions">
            <button type="button" className="mbtn mbtn-cancel" onClick={() => setConfirmOpen(false)}>Cancel</button>
            <button type="button" className="mbtn mbtn-danger" onClick={() => {
              cancelActiveRequest("Waiting stopped because the conversation history was cleared.");
              setConversations([]); setCurrentId(null); setConfirmOpen(false);
            }}>Clear history</button>
          </div>
        </div>}
      </div>
    </div>
  );
}
