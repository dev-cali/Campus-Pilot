"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import styles from "./documents.module.css";

const categories = ["All", "Academic Records", "Enrollment", "Student Services", "Guides & Forms"] as const;
type Category = (typeof categories)[number];

type DocumentTopic = {
  id: string;
  category: Exclude<Category, "All">;
  title: string;
  summary: string;
  focus: string;
};

// Illustrative topics only. No official forms or request procedures are asserted.
const documents: DocumentTopic[] = [
  { id: "transcript", category: "Academic Records", title: "Transcript of Records", summary: "Explore information about official academic transcripts.", focus: "Request procedures, applicable fees and release timelines." },
  { id: "grades", category: "Academic Records", title: "Certification of grades", summary: "Find the topic for requesting certified academic grades.", focus: "Required documents, request process and issuing office." },
  { id: "enrollment", category: "Enrollment", title: "Certificate of enrollment", summary: "Explore information about certificates of current enrollment.", focus: "Eligibility, requirements and official request channels." },
  { id: "registration", category: "Enrollment", title: "Registration and enrollment forms", summary: "Browse the topic of forms used for academic registration.", focus: "Current forms, submission instructions and applicable deadlines." },
  { id: "clearance", category: "Student Services", title: "Student clearance", summary: "Explore information about student clearance documents.", focus: "Clearance procedures and participating campus offices." },
  { id: "handbook", category: "Guides & Forms", title: "Student handbook", summary: "Find the topic for official student guides and resources.", focus: "Approved handbook, version and effective date." },
];

export default function DocumentsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = documents.filter((item) =>
    (category === "All" || item.category === category) &&
    `${item.title} ${item.category} ${item.summary} ${item.focus}`.toLowerCase().includes(normalizedQuery)
  );

  function resetFilters() {
    setQuery("");
    setCategory("All");
  }

  return (
    <div className="page">
      <CampusHeader active="documents" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="documents-title">
          <Link href="/" className={styles.back}>← Back to Home</Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>STUDENT RESOURCES</p>
            <h1 id="documents-title">Documents &amp; Forms</h1>
            <p>Find academic records, enrollment forms, student service documents, and campus guides in one place.</p>
          </div>
          <section className={styles.featured} aria-labelledby="featured-title">
            <span className={styles.preview}>FRONTEND PREVIEW</span>
            <h2 id="featured-title">Find the documents you need</h2>
            <p>Explore sample document topics below. Official files, request procedures, and download links will appear when approved campus resources are connected. No actual documents are available in this preview.</p>
            <a href="#document-list" className={styles.featuredLink}>Browse document topics ↓</a>
          </section>
          <section id="document-list" className={styles.listSection} aria-labelledby="list-title">
            <h2 id="list-title">Browse documents</h2>
            <label htmlFor="document-search" className={styles.searchLabel}>Search documents</label>
            <div className={styles.searchRow}>
              <input id="document-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by keyword..." className={styles.search} />
              {(query || category !== "All") && <button type="button" onClick={resetFilters} className={styles.reset}>Clear filters</button>}
            </div>
            <div className={styles.filters} role="group" aria-label="Filter document topics by category">
              {categories.map((item) => (
                <button type="button" key={item} className={styles.filter} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>
              ))}
            </div>
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Preview only</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching document topics</h3>
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
                    <div className={styles.availability}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M6 3h8l4 4v14H6zM14 3v5h4M9 13h6M9 17h6"/></svg>
                      <span>Official file not connected</span>
                    </div>
                    <details className={styles.details}>
                      <summary>View details</summary>
                      <dl>
                        <dt>Information to be provided</dt><dd>{item.focus}</dd>
                        <dt>Issuing office</dt><dd>Not yet verified.</dd>
                        <dt>Requirements and fees</dt><dd>Not yet verified.</dd>
                        <dt>Download or request</dt><dd>No official file or request link is connected yet.</dd>
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
