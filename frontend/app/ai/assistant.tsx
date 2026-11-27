"use client";

import { useEffect, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";
import {
  parseAnswer,
  parseQuestion,
  statusCodes,
  statusLabels,
  type Answer,
} from "@/lib/ai-contract";
import CampusHeader from "../components/campus-header";
import "../home.css";
import styles from "./assistant.module.css";

type Category = "News" | "Scholarships" | "Policies" | "Events" | "Documents" | "Academics";
type ChatEntry = {
  id: string;
  question: string;
  answer?: Answer;
  error?: string;
};
type Conversation = {
  id: string;
  title: string;
  category: Category | null;
  entries: ChatEntry[];
};

const CATEGORIES: Category[] = ["News", "Scholarships", "Policies", "Events", "Documents", "Academics"];
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
  const [error, setError] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const active = useRef<AbortController | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => () => active.current?.abort(), []);


  const current = conversations.find((chat) => chat.id === currentId) ?? null;
  const entries = current?.entries ?? [];
  const visibleConversations = filterCategory && category
    ? conversations.filter((chat) => chat.category === category)
    : conversations;
  const shown = showAll ? visibleConversations : visibleConversations.slice(0, 7);

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [currentId, entries.length, pending]);

  function newChat() {
    if (pending) return;
    setCurrentId(null);
    setCategory(null);
    setQuestion("");
    setError("");
    inputRef.current?.focus();
  }

  function selectCategory(next: Category) {
    if (pending) return;
    setCategory((previous) => previous === next ? null : next);
    setCurrentId(null);
    setError("");
    inputRef.current?.focus();
  }

  function handleHeaderCategory(event: MouseEvent<HTMLAnchorElement>, next: Category | null) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    if (pending || category === next) return;
    if (next === null) newChat();
    else selectCategory(next);
  }

  function openConversation(chat: Conversation) {
    if (pending) return;
    setCurrentId(chat.id);
    setCategory(chat.category);
    setError("");
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (active.current) return;
    setError("");
    // Validate the visible value too: browser restoration can bypass onChange.
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

    const controller = new AbortController();
    active.current = controller;
    setPending(true);
    const timer = setTimeout(() => controller.abort(), 30000);
    let result: Answer | null = null;
    let failure = "";
    try {
      const response = await fetch("/api/ai/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: validated }),
        signal: controller.signal,
      });
      if (response.status === 422) {
        failure = "The question could not be validated. Check its length and try again.";
      } else {
        const parsed = parseAnswer(await response.json());
        if (!parsed || statusCodes[parsed.status] !== response.status) {
          throw new Error("invalid_response");
        }
        result = parsed;
      }
    } catch {
      failure = "We could not reach the AI service or read a valid response. Check that both demo servers are running, then try again.";
    } finally {
      clearTimeout(timer);
      active.current = null;
      setPending(false);
      setConversations((previous) => previous.map((chat) => chat.id === chatId ? {
        ...chat,
        entries: chat.entries.map((entry) => entry.id === entryId
          ? { ...entry, ...(result ? { answer: result } : {}), ...(failure ? { error: failure } : {}) }
          : entry),
      } : chat));
    }
  }

  return (
    <div className={`page ${styles.mobileShell}`}>
      <CampusHeader
        active="ai"
        onAssistantClick={(event) => handleHeaderCategory(event, null)}
      />

      <div className="layout">
        <aside className="savedpanel" aria-label="Conversation history">
          <div className="shead">
            <h2>Saved prompts</h2>
            <button type="button" className="filt" title="Filter by selected category"
              aria-pressed={filterCategory} onClick={() => setFilterCategory((value) => !value)}>
              <Icon name="filter" />
            </button>
          </div>
          <button type="button" className="newchat" onClick={newChat} disabled={pending}>
            <Icon name="plus" /> New chat
          </button>
          <ul id="saved">
            {shown.length === 0 && <li className="empty">No conversations yet. Ask something!</li>}
            {shown.map((chat) => <li key={chat.id} className={chat.id === currentId ? "sel" : ""}>
              <button type="button" className="qbtn" title={chat.title}
                onClick={() => openConversation(chat)} disabled={pending}>
                <span>{chat.title}</span>
              </button>
              <button type="button" className="del" aria-label={`Delete ${chat.title}`}
                disabled={pending} onClick={() => {
                  setConversations((previous) => previous.filter((item) => item.id !== chat.id));
                  if (currentId === chat.id) setCurrentId(null);
                }}>×</button>
            </li>)}
          </ul>
          <div className="sfoot">
            {visibleConversations.length > 7 && <button type="button" className="link"
              onClick={() => setShowAll((value) => !value)}>{showAll ? "Show less" : "View all"}</button>}
            <button type="button" className="link" disabled={pending || conversations.length === 0}
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
                disabled={pending}
              >
                <Icon name={item} /> {item}
              </button>
            ))}
          </nav>
          <section className="main">
            {entries.length === 0 && <div className="stage">
              <h2 className="news-heading">CampusPilot AI Assistant</h2>
              <p style={{ textAlign: "center", margin: "12px auto", maxWidth: 540 }}>
                Ask a question. Explore the evidence. Select a category above to focus your prompt.
              </p>
              <aside className={styles.notice}>
                <strong>Fictional data only.</strong> This academic demonstration does not provide
                official university advice. Do not enter private student information. A successful
                answer requires a configured provider; the assistant may safely decline when evidence is missing.
              </aside>
            </div>}
            {category && <div className="cathead"><h2>{category}</h2><p>Ask about {category.toLowerCase()} using available evidence.</p></div>}
            <div className={`chat${entries.length ? " on" : ""}`} ref={chatRef} aria-live="polite">
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
                </div>}
                {entry.error && <div className="msg" role="alert"><p className={styles.error}>{entry.error}</p></div>}
              </div>)}
              {pending && <div className="msg" role="status">Retrieving fictional sources and checking the response…</div>}
            </div>
            {error && <p className={styles.error} role="alert">{error}</p>}
            <form className="ask" onSubmit={ask} noValidate>
              <input ref={inputRef} id="question" name="question" type="text"
                placeholder={PLACEHOLDERS[category ?? "home"]}
                aria-label="Your university question" aria-describedby="question-help"
                aria-invalid={Boolean(error)} autoComplete="off" maxLength={2000}
                value={question} disabled={pending}
                onInput={(event) => setQuestion(event.currentTarget.value)}
                onFocus={(event) => setQuestion(event.currentTarget.value)}
                onChange={(event) => setQuestion(event.target.value)} />
              <button type="submit" aria-label="Ask CampusPilot" disabled={pending || !parseQuestion({ question })}>
                <Icon name="send" size={20} />
              </button>
            </form>
            <p id="question-help" className={styles.hint}>
              {Array.from(question).length.toLocaleString()} / 2,000 characters · Try enrollment or a scholarship GPA question to test missing evidence.
            </p>
          </section>
        </main>
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
              setConversations([]); setCurrentId(null); setConfirmOpen(false);
            }}>Clear history</button>
          </div>
        </div>}
      </div>
    </div>
  );
}
