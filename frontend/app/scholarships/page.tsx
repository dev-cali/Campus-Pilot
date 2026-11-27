"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import PortalCardGrid, { type PortalItem } from "../components/portal-card-grid";
import styles from "./scholarships.module.css";

const categories = ["All", "Academic", "Financial Aid", "Talent & Service", "External"] as const;
type Category = (typeof categories)[number];

// Fictional frontend-only demonstration information.
const scholarships: (PortalItem & { category: Exclude<Category, "All"> })[] = [
  {
    "id": "merit",
    "category": "Academic",
    "title": "Academic Excellence Grant",
    "summary": "Merit-based tuition support for high-achieving students.",
    "icon": "scholarship",
    "details": "In this example, a review panel evaluates academic performance at the end of each term.",
    "facts": [
      {
        "label": "Benefit",
        "value": "50% tuition discount"
      },
      {
        "label": "Eligibility",
        "value": "Sample GWA of 1.75 or better"
      },
      {
        "label": "Application window",
        "value": "Jan 4–15, 2027"
      },
      {
        "label": "Office",
        "value": "Demo Financial Aid Office"
      }
    ],
    "nextSteps": [
      "Prepare a sample grade report and application checklist.",
      "Review the fictional renewal criteria each semester."
    ]
  },
  {
    "id": "entrance",
    "category": "Academic",
    "title": "Freshman Entrance Award",
    "summary": "Sample tuition assistance for incoming first-year students.",
    "icon": "scholarship",
    "details": "The fictional award recognizes incoming students with strong secondary school grades.",
    "facts": [
      {
        "label": "Benefit",
        "value": "25% tuition discount"
      },
      {
        "label": "Eligibility",
        "value": "Incoming first-year students; sample average 90%"
      },
      {
        "label": "Deadline",
        "value": "Jan 22, 2027"
      },
      {
        "label": "Office",
        "value": "Demo Admissions Office"
      }
    ],
    "nextSteps": [
      "Prepare a sample high-school grade report.",
      "Confirm actual entrance awards with the institution."
    ]
  },
  {
    "id": "need",
    "category": "Financial Aid",
    "title": "Student Access Grant",
    "summary": "Need-based assistance for education expenses.",
    "icon": "scholarship",
    "details": "A fictional committee reviews a student budget and financial circumstances to allocate limited assistance.",
    "facts": [
      {
        "label": "Benefit",
        "value": "₱8,000 per semester"
      },
      {
        "label": "Eligibility",
        "value": "Demonstrated financial need in the sample scenario"
      },
      {
        "label": "Window",
        "value": "Jan 11–29, 2027"
      },
      {
        "label": "Office",
        "value": "Demo Financial Aid Office"
      }
    ],
    "nextSteps": [
      "Review the sample budget worksheet.",
      "Do not submit private financial records to this demo."
    ]
  },
  {
    "id": "athletics",
    "category": "Talent & Service",
    "title": "Varsity Athlete Award",
    "summary": "Tuition support for student athletes.",
    "icon": "scholarship",
    "details": "This example recognizes participation in a fictional varsity program while maintaining academic progress.",
    "facts": [
      {
        "label": "Benefit",
        "value": "25% tuition discount"
      },
      {
        "label": "Eligibility",
        "value": "Sample varsity roster and passing grades"
      },
      {
        "label": "Review",
        "value": "Each semester"
      },
      {
        "label": "Office",
        "value": "Demo Sports Office"
      }
    ],
    "nextSteps": [
      "Review sample training and attendance expectations.",
      "Ask the real sports office about current programs."
    ]
  },
  {
    "id": "leadership",
    "category": "Talent & Service",
    "title": "Leadership and Service Award",
    "summary": "Support for student leaders and volunteers.",
    "icon": "scholarship",
    "details": "A fictional committee considers leadership projects, service hours and a reflection essay.",
    "facts": [
      {
        "label": "Benefit",
        "value": "₱5,000 semester allowance"
      },
      {
        "label": "Eligibility",
        "value": "40 sample service hours"
      },
      {
        "label": "Deadline",
        "value": "Feb 5, 2027"
      },
      {
        "label": "Office",
        "value": "Demo Student Affairs"
      }
    ],
    "nextSteps": [
      "Prepare an example activity portfolio.",
      "Outline your sample community project."
    ]
  },
  {
    "id": "external",
    "category": "External",
    "title": "Community Partner Grant",
    "summary": "Illustrative award from an external sponsor.",
    "icon": "scholarship",
    "details": "The example depicts an independent fictional education foundation offering assistance to students.",
    "facts": [
      {
        "label": "Sponsor",
        "value": "Demo Community Learning Foundation"
      },
      {
        "label": "Benefit",
        "value": "₱10,000 annual grant"
      },
      {
        "label": "Window",
        "value": "Feb 1–19, 2027"
      },
      {
        "label": "Availability",
        "value": "Illustrative only; no real application"
      }
    ],
    "nextSteps": [
      "Review a sample personal statement.",
      "Verify real sponsors through official channels."
    ]
  }
];

export default function ScholarshipsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = scholarships.filter((item) =>
    (category === "All" || item.category === category) &&
    [item.title, item.category, item.summary, item.details, item.metadata, ...item.facts.flatMap((fact) => [fact.label, fact.value]), ...(item.nextSteps ?? [])].join(" ").toLowerCase().includes(normalizedQuery)
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
          <section className={styles.featured} aria-labelledby="featured-title" style={{ backgroundImage: "linear-gradient(90deg, rgba(5,39,29,.96), rgba(5,39,29,.82) 48%, rgba(5,39,29,.32)), url('/images/campus-news.jpg')" }}>
            <span className={styles.preview}>FICTIONAL CAMPUS DEMO</span>
            <h2 id="featured-title">Find support for your education</h2>
            <p>Explore realistic fictional examples with detailed information. These are not official university resources or active offers.</p>
            <a href="#scholarship-list" className={styles.featuredLink}>Browse scholarships ↓</a>
          </section>
          <section id="scholarship-list" className={styles.listSection} aria-labelledby="list-title">
            <header className={styles.sectionHeading}>
              <p className={styles.eyebrow}>EXPLORE CAMPUS RESOURCES</p>
              <h2 id="list-title">Explore financial opportunities</h2>
              <p>Choose any card for its full fictional details. Not official campus information.</p>
            </header>
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
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Fictional demo information</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching scholarship topics</h3>
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
