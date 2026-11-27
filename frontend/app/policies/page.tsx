"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import styles from "./policies.module.css";

const categories = ["All", "Academic", "Student Conduct", "Campus Services", "Privacy"] as const;
type Category = (typeof categories)[number];

type PolicyTopic = {
  id: string;
  category: Exclude<Category, "All">;
  title: string;
  summary: string;
  details: string;
};

// Preview topics only. No official rules, dates, or document links are asserted.
const topics: PolicyTopic[] = [
  { id: "enrollment", category: "Academic", title: "Enrollment and registration", summary: "Find information about registration and enrollment procedures.", details: "An approved enrollment policy or handbook can be linked here when available." },
  { id: "attendance", category: "Academic", title: "Attendance and academic requirements", summary: "Explore academic expectations and attendance-related information.", details: "Official attendance requirements and academic procedures will be shown after verified documents are connected." },
  { id: "conduct", category: "Student Conduct", title: "Student code of conduct", summary: "Explore student responsibilities and campus conduct topics.", details: "This is a directory topic, not a statement of the university's conduct rules. The approved student handbook is not yet connected." },
  { id: "integrity", category: "Student Conduct", title: "Academic integrity", summary: "Find information about academic honesty and responsible learning.", details: "Official academic integrity rules and procedures can be made available here after document approval." },
  { id: "services", category: "Campus Services", title: "Campus facilities and services", summary: "Explore information about campus resources and services.", details: "Verified campus service guidelines and facility-use documents will appear here when available." },
  { id: "privacy", category: "Privacy", title: "Data privacy and information handling", summary: "Locate privacy-related information and notices.", details: "No official privacy notice is connected to this preview. Approved notices will be linked when available." },
];

export default function PoliciesPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = topics.filter((topic) =>
    (category === "All" || topic.category === category) &&
    `${topic.title} ${topic.category} ${topic.summary} ${topic.details}`.toLowerCase().includes(normalizedQuery)
  );

  function resetFilters() {
    setQuery("");
    setCategory("All");
  }

  return (
    <div className="page">
      <CampusHeader active="policies" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="policies-title">
          <Link href="/" className={styles.back}>← Back to Home</Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>CAMPUS RESOURCES</p>
            <h1 id="policies-title">University Policies</h1>
            <p>Browse policy topics, student guidelines, and academic resources in one place.</p>
          </div>
          <section className={styles.featured} aria-labelledby="featured-title">
            <span className={styles.preview}>FRONTEND PREVIEW</span>
            <h2 id="featured-title">Find the information you need</h2>
            <p>This directory contains sample topics, not official university policies. Approved documents will be linked when available. You can also sign in to explore the AI Assistant&apos;s policy category.</p>
            <Link href="/ai?category=Policies" prefetch={false} className={styles.featuredLink}>Explore policies with AI →</Link>
          </section>
          <section className={styles.listSection} aria-labelledby="list-title">
            <h2 id="list-title">Browse policy topics</h2>
            <label htmlFor="policy-search" className={styles.searchLabel}>Search policies</label>
            <div className={styles.searchRow}>
              <input id="policy-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by keyword..." className={styles.search} />
              {(query || category !== "All") && <button type="button" onClick={resetFilters} className={styles.reset}>Clear filters</button>}
            </div>
            <div className={styles.filters} role="group" aria-label="Filter policy topics by category">
              {categories.map((item) => (
                <button type="button" key={item} className={styles.filter} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>
              ))}
            </div>
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Preview only</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching policy topics</h3>
                <p>Try a different keyword or category.</p>
                <button type="button" className={styles.reset} onClick={resetFilters}>Clear filters</button>
              </div>
            ) : (
              <div className={styles.grid}>
                {results.map((topic) => (
                  <article key={topic.id} className={styles.article}>
                    <span className={styles.category}>{topic.category} · Preview</span>
                    <h3>{topic.title}</h3>
                    <p>{topic.summary}</p>
                    <details className={styles.details}>
                      <summary>View details</summary>
                      <p>{topic.details}</p>
                    </details>
                  </article>
                ))}
              </div>
            )}
          </section>
        </section>
      </main>
      <footer className={styles.footer}>CampusPilot · Public portal preview</footer>
    </div>
  );
}
