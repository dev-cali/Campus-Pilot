"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import PortalCardGrid, { type PortalItem } from "../components/portal-card-grid";
import styles from "./policies.module.css";

const categories = ["All", "Academic", "Student Conduct", "Campus Services", "Privacy"] as const;
type Category = (typeof categories)[number];

// Fictional frontend-only demonstration information.
const topics: (PortalItem & { category: Exclude<Category, "All"> })[] = [
  {
    "id": "enrollment",
    "category": "Academic",
    "title": "Enrollment and registration",
    "summary": "Sample steps for confirming course registration.",
    "icon": "policy",
    "details": "This fictional policy illustrates advising, course selection, and registration confirmation before classes begin.",
    "facts": [
      {
        "label": "Policy ID",
        "value": "DEMO-AC-01"
      },
      {
        "label": "Sample effective date",
        "value": "Jan 4, 2027"
      },
      {
        "label": "Responsible office",
        "value": "Demo Registrar"
      },
      {
        "label": "Scope",
        "value": "Continuing students"
      }
    ],
    "nextSteps": [
      "Review the sample course checklist.",
      "Confirm the actual registration policy separately."
    ]
  },
  {
    "id": "attendance",
    "category": "Academic",
    "title": "Class attendance guidelines",
    "summary": "An example attendance and absence reporting policy.",
    "icon": "policy",
    "details": "In this illustrative policy, students notify instructors about absences and coordinate missed activities.",
    "facts": [
      {
        "label": "Policy ID",
        "value": "DEMO-AC-02"
      },
      {
        "label": "Sample attendance target",
        "value": "80% of meetings"
      },
      {
        "label": "Office",
        "value": "Demo Academic Affairs"
      },
      {
        "label": "Scope",
        "value": "Undergraduate classes"
      }
    ],
    "nextSteps": [
      "Discuss missed activities with the instructor.",
      "Use verified school rules for actual attendance decisions."
    ]
  },
  {
    "id": "conduct",
    "category": "Student Conduct",
    "title": "Student code of conduct",
    "summary": "Example standards for respectful campus behavior.",
    "icon": "policy",
    "details": "This fictional code encourages respectful communication, responsible facility use and reporting concerns through appropriate channels.",
    "facts": [
      {
        "label": "Policy ID",
        "value": "DEMO-SC-01"
      },
      {
        "label": "Review cycle",
        "value": "Annual (sample)"
      },
      {
        "label": "Office",
        "value": "Demo Student Affairs"
      },
      {
        "label": "Scope",
        "value": "Campus activities"
      }
    ],
    "nextSteps": [
      "Review the example expectations.",
      "Refer actual concerns to official university channels."
    ]
  },
  {
    "id": "integrity",
    "category": "Student Conduct",
    "title": "Academic integrity",
    "summary": "Illustrative guidance on original work and citations.",
    "icon": "policy",
    "details": "The fictional policy describes acknowledging sources, completing independent work when required and discussing collaboration boundaries.",
    "facts": [
      {
        "label": "Policy ID",
        "value": "DEMO-SC-02"
      },
      {
        "label": "Scope",
        "value": "Coursework and assessments"
      },
      {
        "label": "Office",
        "value": "Demo Academic Affairs"
      },
      {
        "label": "Sample process",
        "value": "Instructor review and student response"
      }
    ],
    "nextSteps": [
      "Cite sources in sample assignments.",
      "Check actual course instructions about collaboration."
    ]
  },
  {
    "id": "services",
    "category": "Campus Services",
    "title": "Campus facility use",
    "summary": "Sample guidelines for reserving shared spaces.",
    "icon": "policy",
    "details": "In this fictional scenario, student groups book rooms, observe capacity limits and leave spaces ready for other users.",
    "facts": [
      {
        "label": "Policy ID",
        "value": "DEMO-CS-01"
      },
      {
        "label": "Booking lead time",
        "value": "2 working days (sample)"
      },
      {
        "label": "Office",
        "value": "Demo Facilities Desk"
      },
      {
        "label": "Scope",
        "value": "Study and activity rooms"
      }
    ],
    "nextSteps": [
      "Review the example room-use checklist.",
      "Confirm real booking procedures with facility staff."
    ]
  },
  {
    "id": "privacy",
    "category": "Privacy",
    "title": "Data privacy and information handling",
    "summary": "Example privacy principles for student records.",
    "icon": "policy",
    "details": "This illustrative entry describes limited collection, authorized access and reporting suspected privacy issues. It is not a legal notice.",
    "facts": [
      {
        "label": "Policy ID",
        "value": "DEMO-PR-01"
      },
      {
        "label": "Scope",
        "value": "Illustrative student information"
      },
      {
        "label": "Office",
        "value": "Demo Privacy Desk"
      },
      {
        "label": "Status",
        "value": "Not an official privacy policy"
      }
    ],
    "nextSteps": [
      "Avoid entering real personal information in the demo.",
      "Read the actual institution privacy notice."
    ]
  }
];

export default function PoliciesPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = topics.filter((topic) =>
    (category === "All" || topic.category === category) &&
    [topic.title, topic.category, topic.summary, topic.details, topic.metadata, ...topic.facts.flatMap((fact) => [fact.label, fact.value]), ...(topic.nextSteps ?? [])].join(" ").toLowerCase().includes(normalizedQuery)
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
          <section className={styles.featured} aria-labelledby="featured-title" style={{ backgroundImage: "linear-gradient(90deg, rgba(5,39,29,.96), rgba(5,39,29,.82) 48%, rgba(5,39,29,.32)), url('/images/public-policies.jpg')" }}>
            <span className={styles.preview}>FICTIONAL CAMPUS DEMO</span>
            <h2 id="featured-title">Find the information you need</h2>
            <p>Explore realistic fictional examples with detailed information. These are not official university resources or active offers.</p>
            <Link href="/ai?category=Policies" prefetch={false} className={styles.featuredLink}>Explore policies with AI →</Link>
          </section>
          <section className={styles.listSection} aria-labelledby="list-title">
            <header className={styles.sectionHeading}>
              <p className={styles.eyebrow}>EXPLORE CAMPUS RESOURCES</p>
              <h2 id="list-title">Student guidelines</h2>
              <p>Choose any card for its full fictional details. Not official campus information.</p>
            </header>
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
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Fictional demo information</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching policy topics</h3>
                <p>Try a different keyword or category.</p>
                <button type="button" className={styles.reset} onClick={resetFilters}>Clear filters</button>
              </div>
            ) : (
              <PortalCardGrid items={results} />
            )}
          </section>
        </section>
      </main>
      <footer className={styles.footer}>CampusPilot · Public portal preview</footer>
    </div>
  );
}
