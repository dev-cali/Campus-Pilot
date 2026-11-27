"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import styles from "./events.module.css";

const categories = ["All", "Academic", "Student Life", "Career", "Sports & Culture"] as const;
type Category = (typeof categories)[number];

type CampusEvent = {
  id: string;
  category: Exclude<Category, "All">;
  title: string;
  summary: string;
  focus: string;
};

// Sample event types only. No actual event, date or registration is asserted.
const events: CampusEvent[] = [
  { id: "orientation", category: "Academic", title: "Student orientation", summary: "Explore the type of session that introduces students to campus resources and academic life.", focus: "Orientation agenda and participating offices." },
  { id: "seminar", category: "Academic", title: "Academic seminars and workshops", summary: "Browse learning sessions and skills-development activities.", focus: "Workshop topics, speakers and participation requirements." },
  { id: "organizations", category: "Student Life", title: "Student organization fair", summary: "Discover the types of activities that help students explore campus organizations.", focus: "Participating organizations and activity schedules." },
  { id: "career", category: "Career", title: "Career fair", summary: "Explore opportunities to learn about careers, internships and professional development.", focus: "Participating employers and registration requirements." },
  { id: "sports", category: "Sports & Culture", title: "Campus sports activities", summary: "Browse the topic of recreational and competitive student sports.", focus: "Activity schedules, venues and participation guidelines." },
  { id: "culture", category: "Sports & Culture", title: "Arts and cultural activities", summary: "Explore campus performances, creative showcases and cultural programs.", focus: "Program details, participants and venue information." },
];

export default function EventsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = events.filter((item) =>
    (category === "All" || item.category === category) &&
    `${item.title} ${item.category} ${item.summary} ${item.focus}`.toLowerCase().includes(normalizedQuery)
  );

  function resetFilters() {
    setQuery("");
    setCategory("All");
  }

  return (
    <div className="page">
      <CampusHeader active="events" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="events-title">
          <Link href="/" className={styles.back}>← Back to Home</Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>CAMPUS LIFE</p>
            <h1 id="events-title">Campus Events</h1>
            <p>Explore academic activities, student programs, career opportunities, and campus events in one place.</p>
          </div>
          <section className={styles.featured} aria-labelledby="featured-title">
            <span className={styles.preview}>FRONTEND PREVIEW</span>
            <h2 id="featured-title">Discover what campus life has to offer</h2>
            <p>Browse sample event types below. These are not confirmed or scheduled university events. Official dates, venues, organizers, and registration details will appear when approved data is connected.</p>
            <a href="#event-list" className={styles.featuredLink}>Browse event topics ↓</a>
          </section>
          <section id="event-list" className={styles.listSection} aria-labelledby="list-title">
            <h2 id="list-title">Browse events</h2>
            <label htmlFor="event-search" className={styles.searchLabel}>Search events</label>
            <div className={styles.searchRow}>
              <input id="event-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by keyword..." className={styles.search} />
              {(query || category !== "All") && <button type="button" onClick={resetFilters} className={styles.reset}>Clear filters</button>}
            </div>
            <div className={styles.filters} role="group" aria-label="Filter event topics by category">
              {categories.map((item) => (
                <button type="button" key={item} className={styles.filter} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>
              ))}
            </div>
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Preview only</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching event topics</h3>
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
                    <div className={styles.schedule}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="4" y="5" width="16" height="16" rx="3"/><path d="M8 3v4M16 3v4M4 11h16"/></svg>
                      <span>Date not announced</span>
                    </div>
                    <details className={styles.details}>
                      <summary>View details</summary>
                      <dl>
                        <dt>Information to be provided</dt><dd>{item.focus}</dd>
                        <dt>Date and time</dt><dd>Not available.</dd>
                        <dt>Venue and organizer</dt><dd>Not yet verified.</dd>
                        <dt>Registration</dt><dd>No official registration link is connected yet.</dd>
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
