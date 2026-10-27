"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { parseAnswer, parseQuestion, statusCodes, statusLabels, type Answer } from "@/lib/ai-contract";
import styles from "./assistant.module.css";

export default function Assistant() {
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState("");
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (active.current) return;
    setAnswer(null);
    setError("");
    const validated = parseQuestion({ question });
    if (!validated) {
      setError("Enter a question of 1–2,000 characters.");
      return;
    }
    const controller = new AbortController();
    active.current = controller;
    setPending(true);
    const timer = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch("/api/ai/ask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: validated }), signal: controller.signal,
      });
      if (response.status === 422) {
        setError("The question could not be validated. Check its length and try again.");
        return;
      }
      const parsed = parseAnswer(await response.json());
      if (!parsed || statusCodes[parsed.status] !== response.status) {
        throw new Error("invalid_response");
      }
      setAnswer(parsed);
    } catch {
      setError("We could not reach the AI service or read a valid response. Check that both demo servers are running, then try again.");
    } finally {
      clearTimeout(timer);
      active.current = null;
      setPending(false);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <Link className={styles.back} href="/">← CampusPilot home</Link>
        <header className={styles.header}>
          <p className={styles.eyebrow}>DEMO CAMPUS UNIVERSITY · SPRINT 3</p>
          <h1>CampusPilot AI Assistant</h1>
          <p>Ask a question. Explore the evidence.</p>
        </header>
        <aside className={styles.notice}>
          <strong>Fictional data only.</strong> This academic demonstration does not provide official
          university advice. Do not enter private student information. A successful answer requires
          a configured provider; the assistant may safely decline when evidence is missing.
        </aside>
        <form className={styles.card} onSubmit={ask} noValidate>
          <label htmlFor="question">Your university question</label>
          <textarea id="question" name="question" rows={4} value={question} disabled={pending}
            aria-describedby="question-help" aria-invalid={Boolean(error)}
            placeholder="What do fictional learners review for enrollment?"
            onChange={(event) => setQuestion(event.target.value)} />
          <div className={styles.actions}>
            <p id="question-help">{Array.from(question).length.toLocaleString()} / 2,000 characters</p>
            <button type="submit" disabled={pending}>{pending ? "Checking evidence…" : "Ask CampusPilot"}</button>
          </div>
          <p className={styles.hint}>Try asking about enrollment, or ask for a scholarship GPA to see how missing evidence is handled.</p>
        </form>
        {pending && <p role="status">Retrieving fictional sources and checking the response…</p>}
        {error && <p className={styles.error} role="alert">{error}</p>}
        {answer && <section className={styles.card} aria-live="polite" aria-atomic="true">
          <h2>{statusLabels[answer.status]}</h2>
          <p className={styles.answer}>{answer.answer}</p>
          {answer.status === "answered" && <div className={styles.sources}>
            <h3>Sources supplied by the backend</h3>
            <ol>
              {answer.citations.map((citation) => <li key={citation.evidence_id}>
                <strong>[{citation.evidence_id}] {citation.title}</strong>
                <p>Document {citation.document_id} · Page {citation.page_no} · Version {citation.version} · Chunk {citation.chunk_index}</p>
                <p className={styles.reference}>{citation.source_reference}</p>
              </li>)}
            </ol>
            <p className={styles.hint}>Source references are fictional identifiers, not links. Matching a quotation does not prove that it fully answers your question.</p>
          </div>}
        </section>}
      </div>
    </main>
  );
}
