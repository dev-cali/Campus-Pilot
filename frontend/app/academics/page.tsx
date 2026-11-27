"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import styles from "./academics.module.css";

const categories = ["All", "Academic Calendar", "Enrollment", "Academic Programs", "Academic Support"] as const;
type Category = (typeof categories)[number];

type AcademicTopic = {
  id: string;
  category: Exclude<Category, "All">;
  title: string;
  summary: string;
  focus: string;
};

// Sample topics only; no official dates, requirements, or programs are asserted.
const topics: AcademicTopic[] = [
  { id: "calendar", category: "Academic Calendar", title: "Academic calendar", summary: "Explore semester schedules and important academic dates.", focus: "Official term dates, examination periods and holidays." },
  { id: "enrollment", category: "Enrollment", title: "Enrollment and registration", summary: "Find information about enrolling and registering for classes.", focus: "Enrollment periods, registration steps and official requirements." },
  { id: "subjects", category: "Academic Programs", title: "Programs and curriculum", summary: "Explore academic programs and curriculum information.", focus: "Approved program offerings, course descriptions and curriculum guides." },
  { id: "grades", category: "Academic Support", title: "Grades and academic standing", summary: "Explore grading and academic progress information.", focus: "Official grading system and academic standing requirements." },
  { id: "advising", category: "Academic Support", title: "Academic advising", summary: "Find information about academic guidance and learning support.", focus: "Advising services, contacts and appointment procedures." },
  { id: "graduation", category: "Academic Calendar", title: "Graduation information", summary: "Explore graduation schedules and preparation topics.", focus: "Official graduation dates, eligibility and application procedures." },
];

export default function AcademicsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = topics.filter((item) =>
    (category === "All" || item.category === category) &&
    `${item.title} ${item.category} ${item.summary} ${item.focus}`.toLowerCase().includes(normalizedQuery)
  );

  function resetFilters() {
    setQuery("");
    setCategory("All");
  }

  return (
    <div className="page">
      <CampusHeader active="academics" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="academics-title">
          <Link href="/" className={styles.back}>← Back to Home</Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>ACADEMIC RESOURCES</p>
            <h1 id="academics-title">Academics</h1>
            <p>Explore academic calendars, enrollment information, academic programs, and student learning resources.</p>
          </div>
          <section className={styles.featured} aria-labelledby="featured-title">
            <span className={styles.preview}>FRONTEND PREVIEW</span>
            <h2 id="featured-title">Plan your academic journey</h2>
            <p>Explore sample academic topics below. Official schedules, program information, and requirements will appear once approved campus resources are connected.</p>
            <a href="#academic-list" className={styles.featuredLink}>Browse academic topics ↓</a>
          </section>
          <section id="academic-list" className={styles.listSection} aria-labelledby="list-title">
            <h2 id="list-title">Browse academic resources</h2>
            <label htmlFor="academic-search" className={styles.searchLabel}>Search academic resources</label>
            <div className={styles.searchRow}>
              <input id="academic-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by keyword..." className={styles.search} />
              {(query || category !== "All") && <button type="button" onClick={resetFilters} className={styles.reset}>Clear filters</button>}
            </div>
            <div className={styles.filters} role="group" aria-label="Filter academic topics by category">
              {categories.map((item) => (
                <button type="button" key={item} className={styles.filter} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>
              ))}
            </div>
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Preview only</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching academic topics</h3>
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
                      <span>Official information not connected</span>
                    </div>
                    <details className={styles.details}>
                      <summary>View details</summary>
                      <dl>
                        <dt>Information to be provided</dt><dd>{item.focus}</dd>
                        <dt>Responsible office</dt><dd>Not yet verified.</dd>
                        <dt>Dates and requirements</dt><dd>Not yet verified.</dd>
                        <dt>Official resource</dt><dd>No official resource link is connected yet.</dd>
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
