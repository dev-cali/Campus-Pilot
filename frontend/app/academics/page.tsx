"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import PortalCardGrid, { type PortalItem } from "../components/portal-card-grid";
import styles from "./academics.module.css";

const categories = ["All", "Academic Calendar", "Enrollment", "Academic Programs", "Academic Support"] as const;
type Category = (typeof categories)[number];

// Fictional frontend-only demonstration information.
const topics: (PortalItem & { category: Exclude<Category, "All"> })[] = [
  {
    "id": "calendar",
    "category": "Academic Calendar",
    "title": "Academic Calendar",
    "summary": "Explore a sample second-semester schedule.",
    "icon": "academic",
    "details": "The fictional calendar organizes enrollment, classes and assessment periods.",
    "facts": [
      {
        "label": "Enrollment",
        "value": "Jan 4–15, 2027"
      },
      {
        "label": "Classes begin",
        "value": "Jan 18, 2027"
      },
      {
        "label": "Midterms",
        "value": "Mar 8–12, 2027"
      },
      {
        "label": "Finals",
        "value": "May 17–21, 2027"
      }
    ],
    "nextSteps": [
      "Review sample dates when planning an example schedule.",
      "Verify real dates with the official calendar."
    ]
  },
  {
    "id": "enrollment",
    "category": "Enrollment",
    "title": "Enrollment and Registration",
    "summary": "Sample steps for choosing and registering subjects.",
    "icon": "academic",
    "details": "The fictional registration workflow includes advising, subject selection and confirmation.",
    "facts": [
      {
        "label": "Window",
        "value": "Jan 4–15, 2027"
      },
      {
        "label": "Office",
        "value": "Demo Registrar"
      },
      {
        "label": "Sample hours",
        "value": "8 AM–5 PM"
      },
      {
        "label": "Audience",
        "value": "Continuing students"
      }
    ],
    "nextSteps": [
      "Prepare sample previous-term grades.",
      "Review a proposed course load with an adviser."
    ]
  },
  {
    "id": "subjects",
    "category": "Academic Programs",
    "title": "Programs and Curriculum",
    "summary": "Explore an example computing curriculum.",
    "icon": "academic",
    "details": "This fictional four-year program includes programming, databases, systems and a capstone project.",
    "facts": [
      {
        "label": "Example program",
        "value": "BS Computer Science"
      },
      {
        "label": "Duration",
        "value": "4 years (sample)"
      },
      {
        "label": "Sample subjects",
        "value": "Programming, algorithms, databases"
      },
      {
        "label": "Office",
        "value": "Demo College of Computing"
      }
    ],
    "nextSteps": [
      "Review the example curriculum sequence.",
      "Confirm approved program offerings independently."
    ]
  },
  {
    "id": "grades",
    "category": "Academic Support",
    "title": "Grades and Academic Standing",
    "summary": "Illustrative information about academic progress.",
    "icon": "academic",
    "details": "The sample advising process reviews course results and identifies areas for learning support.",
    "facts": [
      {
        "label": "Sample grading scale",
        "value": "1.00–5.00"
      },
      {
        "label": "Review",
        "value": "End of each term"
      },
      {
        "label": "Office",
        "value": "Demo Academic Affairs"
      },
      {
        "label": "Status",
        "value": "Illustrative criteria only"
      }
    ],
    "nextSteps": [
      "Review a fictional grade report.",
      "Discuss learning goals with an actual adviser."
    ]
  },
  {
    "id": "advising",
    "category": "Academic Support",
    "title": "Academic Advising",
    "summary": "Sample guidance for course and study planning.",
    "icon": "academic",
    "details": "This fictional service includes individual consultations about academic workload and study strategies.",
    "facts": [
      {
        "label": "Window",
        "value": "Feb 1–5, 2027"
      },
      {
        "label": "Session",
        "value": "20 minutes (sample)"
      },
      {
        "label": "Venue",
        "value": "Demo Advising Hub"
      },
      {
        "label": "Audience",
        "value": "All year levels"
      }
    ],
    "nextSteps": [
      "List sample course questions.",
      "Review your example learning goals."
    ]
  },
  {
    "id": "graduation",
    "category": "Academic Calendar",
    "title": "Graduation Preparation",
    "summary": "Explore an illustrative graduation checklist.",
    "icon": "academic",
    "details": "The example process includes academic review, clearance and a rehearsal briefing.",
    "facts": [
      {
        "label": "Sample ceremony",
        "value": "Jun 18, 2027"
      },
      {
        "label": "Application window",
        "value": "Apr 5–16, 2027"
      },
      {
        "label": "Office",
        "value": "Demo Registrar"
      },
      {
        "label": "Venue",
        "value": "Demo Auditorium"
      }
    ],
    "nextSteps": [
      "Review sample curriculum completion.",
      "Confirm real graduation requirements separately."
    ]
  }
];

export default function AcademicsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = topics.filter((item) =>
    (category === "All" || item.category === category) &&
    [item.title, item.category, item.summary, item.details, item.metadata, ...item.facts.flatMap((fact) => [fact.label, fact.value]), ...(item.nextSteps ?? [])].join(" ").toLowerCase().includes(normalizedQuery)
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
          <section className={styles.featured} aria-labelledby="featured-title" style={{ backgroundImage: "linear-gradient(90deg, rgba(5,39,29,.96), rgba(5,39,29,.82) 48%, rgba(5,39,29,.32)), url('/images/important-notices.jpg')" }}>
            <span className={styles.preview}>FICTIONAL CAMPUS DEMO</span>
            <h2 id="featured-title">Plan your academic journey</h2>
            <p>Explore realistic fictional examples with detailed information. These are not official university resources or active offers.</p>
            <a href="#academic-list" className={styles.featuredLink}>Browse academic resources ↓</a>
          </section>
          <section id="academic-list" className={styles.listSection} aria-labelledby="list-title">
            <header className={styles.sectionHeading}>
              <p className={styles.eyebrow}>EXPLORE CAMPUS RESOURCES</p>
              <h2 id="list-title">Plan your academic journey</h2>
              <p>Choose any card for its full fictional details. Not official campus information.</p>
            </header>
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
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Fictional demo information</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching academic topics</h3>
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
