"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import styles from "./news.module.css";

const categories = ["All", "Campus News", "Announcements", "Academic", "Events"] as const;
type Category = (typeof categories)[number];

type NewsItem = {
  id: string;
  category: Exclude<Category, "All">;
  title: string;
  summary: string;
  details: string;
};

// Fictional examples for the frontend preview; not official announcements.
const news: NewsItem[] = [
  {
    id: "campus",
    category: "Campus News",
    title: "Campus news overview",
    summary: "A preview of where university news and campus stories will appear.",
    details: "Once an approved news source is connected, this section can display official university updates and links to their sources.",
  },
  {
    id: "general",
    category: "Announcements",
    title: "General announcements",
    summary: "A sample card for important notices and student reminders.",
    details: "Official notices, service updates, and reminders can be published here. This sample does not announce an actual change or deadline.",
  },
  {
    id: "academic",
    category: "Academic",
    title: "Academic updates",
    summary: "A preview of academic calendar and enrollment announcements.",
    details: "Verified enrollment schedules, academic deadlines, and other academic notices will be shown when an approved source is available.",
  },
  {
    id: "events",
    category: "Events",
    title: "Campus events",
    summary: "A sample listing for campus activities and university programs.",
    details: "Event dates, venues, and registration information can appear here after official event information is connected. No actual event is scheduled by this preview.",
  },
];

export default function NewsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = news.filter((item) => {
    const matchesCategory = category === "All" || item.category === category;
    const searchable = `${item.title} ${item.category} ${item.summary} ${item.details}`.toLowerCase();
    return matchesCategory && searchable.includes(normalizedQuery);
  });

  function resetFilters() {
    setQuery("");
    setCategory("All");
  }

  return (
    <div className="page">
      <CampusHeader active="news" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="news-title">
          <Link href="/" className={styles.back}>← Back to Home</Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>STAY INFORMED</p>
            <h1 id="news-title">News &amp; Announcements</h1>
            <p>Browse campus updates, important notices, academic information, and events.</p>
          </div>

          <section className={styles.featured} aria-labelledby="featured-title">
            <span className={styles.preview}>FRONTEND PREVIEW</span>
            <h2 id="featured-title">Your campus, in one place</h2>
            <p>Official announcements will appear here once an approved campus news source is connected.</p>
            <a href="#news-list" className={styles.featuredLink}>Browse sample announcements ↓</a>
          </section>

          <section id="news-list" className={styles.listSection} aria-labelledby="list-title">
            <h2 id="list-title">Browse announcements</h2>
            <label htmlFor="news-search" className={styles.searchLabel}>Search announcements</label>
            <div className={styles.searchRow}>
              <input id="news-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by keyword..." className={styles.search} />
              {(query || category !== "All") && <button type="button" onClick={resetFilters} className={styles.reset}>Clear filters</button>}
            </div>
            <div className={styles.filters} role="group" aria-label="Filter announcements by category">
              {categories.map((item) => (
                <button type="button" key={item} className={styles.filter} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>
              ))}
            </div>
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "result" : "results"} · Sample content only</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching announcements</h3>
                <p>Try another keyword or clear your filters.</p>
                <button type="button" className={styles.reset} onClick={resetFilters}>Show all announcements</button>
              </div>
            ) : (
              <div className={styles.grid}>
                {results.map((item) => (
                  <article key={item.id} className={styles.article}>
                    <span className={styles.category}>{item.category} · Preview</span>
                    <h3>{item.title}</h3>
                    <p>{item.summary}</p>
                    <details className={styles.details}>
                      <summary>Read more</summary>
                      <p>{item.details}</p>
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
