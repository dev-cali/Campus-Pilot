"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import PortalCardGrid, { type PortalItem } from "../components/portal-card-grid";
import styles from "./events.module.css";

const categories = ["All", "Academic", "Student Life", "Career", "Sports & Culture"] as const;
type Category = (typeof categories)[number];

// Fictional frontend-only demonstration information.
const events: (PortalItem & { category: Exclude<Category, "All"> })[] = [
  {
    "id": "orientation",
    "category": "Academic",
    "title": "New Student Orientation",
    "summary": "Explore campus resources and meet student support teams.",
    "icon": "event",
    "metadata": "Jan 18, 2027 · 9 AM–12 PM",
    "details": "A fictional orientation features a welcome session, campus tour and resource introductions.",
    "facts": [
      {
        "label": "Date",
        "value": "Jan 18, 2027"
      },
      {
        "label": "Time",
        "value": "9 AM–12 PM"
      },
      {
        "label": "Venue",
        "value": "Demo Auditorium"
      },
      {
        "label": "Admission",
        "value": "Free (sample)"
      }
    ],
    "nextSteps": [
      "9 AM: welcome session.",
      "10 AM: campus tour.",
      "11 AM: student services briefing."
    ]
  },
  {
    "id": "seminar",
    "category": "Academic",
    "title": "Research and Coding Workshop",
    "summary": "Practice introductory research and coding skills.",
    "icon": "event",
    "metadata": "Jan 21, 2027 · 1–4 PM",
    "details": "This sample workshop introduces project planning and basic programming through guided exercises.",
    "facts": [
      {
        "label": "Date",
        "value": "Jan 21, 2027"
      },
      {
        "label": "Time",
        "value": "1–4 PM"
      },
      {
        "label": "Venue",
        "value": "Demo Computer Lab"
      },
      {
        "label": "Capacity",
        "value": "30 participants"
      }
    ],
    "nextSteps": [
      "Bring a laptop in the fictional scenario.",
      "Complete the sample group exercise."
    ]
  },
  {
    "id": "organizations",
    "category": "Student Life",
    "title": "Student Organization Fair",
    "summary": "Explore student clubs and volunteer opportunities.",
    "icon": "event",
    "metadata": "Jan 27, 2027 · 10 AM–4 PM",
    "details": "Fictional organizations host booths, short introductions and sample activity demonstrations.",
    "facts": [
      {
        "label": "Date",
        "value": "Jan 27, 2027"
      },
      {
        "label": "Time",
        "value": "10 AM–4 PM"
      },
      {
        "label": "Venue",
        "value": "Demo Campus Plaza"
      },
      {
        "label": "Admission",
        "value": "Free (sample)"
      }
    ],
    "nextSteps": [
      "Browse example club booths.",
      "Ask about sample membership activities."
    ]
  },
  {
    "id": "career",
    "category": "Career",
    "title": "Internship and Career Fair",
    "summary": "Discover sample career pathways and employer talks.",
    "icon": "event",
    "metadata": "Feb 10, 2027 · 9 AM–3 PM",
    "details": "This fictional fair includes resume feedback, mock interviews and career presentations.",
    "facts": [
      {
        "label": "Date",
        "value": "Feb 10, 2027"
      },
      {
        "label": "Time",
        "value": "9 AM–3 PM"
      },
      {
        "label": "Venue",
        "value": "Demo Activity Center"
      },
      {
        "label": "Audience",
        "value": "All year levels"
      }
    ],
    "nextSteps": [
      "Prepare a sample resume without private details.",
      "Explore the mock interview session."
    ]
  },
  {
    "id": "sports",
    "category": "Sports & Culture",
    "title": "Campus Sports Festival",
    "summary": "A fictional day of friendly sports activities.",
    "icon": "event",
    "metadata": "Feb 19, 2027 · 8 AM–5 PM",
    "details": "Example activities include basketball, volleyball and recreational games for student teams.",
    "facts": [
      {
        "label": "Date",
        "value": "Feb 19, 2027"
      },
      {
        "label": "Time",
        "value": "8 AM–5 PM"
      },
      {
        "label": "Venue",
        "value": "Demo Sports Complex"
      },
      {
        "label": "Audience",
        "value": "Student teams"
      }
    ],
    "nextSteps": [
      "Review sample team schedules.",
      "Bring suitable sports clothing in the example."
    ]
  },
  {
    "id": "culture",
    "category": "Sports & Culture",
    "title": "Arts and Culture Showcase",
    "summary": "Explore student performances and creative work.",
    "icon": "event",
    "metadata": "Feb 26, 2027 · 2–6 PM",
    "details": "The sample showcase features music, dance, visual arts and short presentations.",
    "facts": [
      {
        "label": "Date",
        "value": "Feb 26, 2027"
      },
      {
        "label": "Time",
        "value": "2–6 PM"
      },
      {
        "label": "Venue",
        "value": "Demo Cultural Hall"
      },
      {
        "label": "Admission",
        "value": "Free (sample)"
      }
    ],
    "nextSteps": [
      "Browse the fictional exhibit.",
      "Attend the example performance program."
    ]
  }
];

export default function EventsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = events.filter((item) =>
    (category === "All" || item.category === category) &&
    [item.title, item.category, item.summary, item.details, item.metadata, ...item.facts.flatMap((fact) => [fact.label, fact.value]), ...(item.nextSteps ?? [])].join(" ").toLowerCase().includes(normalizedQuery)
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
          <section className={styles.featured} aria-labelledby="featured-title" style={{ backgroundImage: "linear-gradient(90deg, rgba(5,39,29,.96), rgba(5,39,29,.82) 48%, rgba(5,39,29,.32)), url('/images/campus-news.jpg')" }}>
            <span className={styles.preview}>FICTIONAL CAMPUS DEMO</span>
            <h2 id="featured-title">Discover what campus life has to offer</h2>
            <p>Explore realistic fictional examples with detailed information. These are not official university resources or active offers.</p>
            <a href="#event-list" className={styles.featuredLink}>Browse events ↓</a>
          </section>
          <section id="event-list" className={styles.listSection} aria-labelledby="list-title">
            <header className={styles.sectionHeading}>
              <p className={styles.eyebrow}>EXPLORE CAMPUS RESOURCES</p>
              <h2 id="list-title">Get involved</h2>
              <p>Choose any card for its full fictional details. Not official campus information.</p>
            </header>
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
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Fictional demo information</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching event topics</h3>
                <p>Try a different keyword or category.</p>
                <button type="button" className={styles.reset} onClick={resetFilters}>Clear filters</button>
              </div>
            ) : (
              <PortalCardGrid items={results} />
            )}
          </section>
        </section>
      </main>
      <footer className={styles.footer}>CampusPilot · Fictional portal demo · Not official campus information</footer>
    </div>
  );
}
