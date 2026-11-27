"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import styles from "./scholarships.module.css";

const categories = ["All", "Academic", "Financial Aid", "Talent & Service", "External"] as const;
type Category = (typeof categories)[number];

type Scholarship = {
  id: string;
  category: Exclude<Category, "All">;
  title: string;
  summary: string;
  focus: string;
};

// Fictional browsing topics only. No actual scholarship availability is asserted.
const scholarships: Scholarship[] = [
  { id: "merit", category: "Academic", title: "Academic merit scholarships", summary: "Explore possible scholarships focused on academic achievement.", focus: "Academic records and achievement criteria, once verified." },
  { id: "entrance", category: "Academic", title: "Entrance scholarships", summary: "Browse the topic of scholarship opportunities for incoming students.", focus: "Admission and entry-level scholarship criteria, once verified." },
  { id: "need", category: "Financial Aid", title: "Need-based financial assistance", summary: "Explore financial support topics for students who need help with education costs.", focus: "Financial assistance eligibility and supporting documents, once verified." },
  { id: "athletics", category: "Talent & Service", title: "Athletic scholarships", summary: "Browse the topic of financial support associated with student athletics.", focus: "Athletic participation and selection criteria, once verified." },
  { id: "leadership", category: "Talent & Service", title: "Leadership and service scholarships", summary: "Explore scholarship topics related to leadership and community involvement.", focus: "Leadership and service records, once verified." },
  { id: "external", category: "External", title: "External scholarship programs", summary: "Browse the topic of scholarships administered by organizations outside the university.", focus: "Verified sponsor information and application procedures, once connected." },
];

export default function ScholarshipsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = scholarships.filter((item) =>
    (category === "All" || item.category === category) &&
    `${item.title} ${item.category} ${item.summary} ${item.focus}`.toLowerCase().includes(normalizedQuery)
  );

  function resetFilters() {
    setQuery("");
    setCategory("All");
  }

  return (
    <div className="page">
      <CampusHeader active="scholarships" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="scholarships-title">
          <Link href="/" className={styles.back}>← Back to Home</Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>STUDENT OPPORTUNITIES</p>
            <h1 id="scholarships-title">Scholarships &amp; Financial Aid</h1>
            <p>Explore scholarship categories, financial assistance topics, and student opportunities in one place.</p>
          </div>
          <section className={styles.featured} aria-labelledby="featured-title">
            <span className={styles.preview}>FRONTEND PREVIEW</span>
            <h2 id="featured-title">Find support for your education</h2>
            <p>Browse sample scholarship topics below. These are not confirmed university programs or open applications. Official opportunities, requirements, benefits, and deadlines will appear when approved data is connected.</p>
            <a href="#scholarship-list" className={styles.featuredLink}>Browse scholarship topics ↓</a>
          </section>
          <section id="scholarship-list" className={styles.listSection} aria-labelledby="list-title">
            <h2 id="list-title">Browse scholarships</h2>
            <label htmlFor="scholarship-search" className={styles.searchLabel}>Search scholarships</label>
            <div className={styles.searchRow}>
              <input id="scholarship-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by keyword..." className={styles.search} />
              {(query || category !== "All") && <button type="button" onClick={resetFilters} className={styles.reset}>Clear filters</button>}
            </div>
            <div className={styles.filters} role="group" aria-label="Filter scholarship topics by category">
              {categories.map((item) => (
                <button type="button" key={item} className={styles.filter} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>
              ))}
            </div>
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Preview only</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching scholarship topics</h3>
                <p>Try a different keyword or category.</p>
                <button type="button" className={styles.reset} onClick={resetFilters}>Clear filters</button>
              </div>
            ) : (
              <div className={styles.grid}>
                {results.map((item) => (
                  <article key={item.id} className={styles.article}>
                    <span className={styles.category}>{item.category} · Preview</span>
                    <h3>{item.title}</h3>
                    <p>{item.summary}</p>
                    <details className={styles.details}>
                      <summary>View details</summary>
                      <dl>
                        <dt>Information to be provided</dt><dd>{item.focus}</dd>
                        <dt>Eligibility and benefits</dt><dd>Not yet verified.</dd>
                        <dt>Application deadline</dt><dd>Not available.</dd>
                        <dt>How to apply</dt><dd>No official application link is connected yet.</dd>
                      </dl>
                    </details>
                  </article>
                ))}
              </div>
            )}
          </section>
        </section>
      </main>
      <footer className={styles.footer}>CampusPilot · Portal preview</footer>
    </div>
  );
}
