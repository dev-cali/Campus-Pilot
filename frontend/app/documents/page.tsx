"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import PortalCardGrid, { type PortalItem } from "../components/portal-card-grid";
import styles from "./documents.module.css";

const categories = ["All", "Academic Records", "Enrollment", "Student Services", "Guides & Forms"] as const;
type Category = (typeof categories)[number];

// Fictional frontend-only demonstration information.
const documents: (PortalItem & { category: Exclude<Category, "All"> })[] = [
  {
    "id": "transcript",
    "category": "Academic Records",
    "title": "Transcript of Records",
    "summary": "Sample process for requesting an academic transcript.",
    "icon": "policy",
    "details": "An illustrative transcript summarizes completed courses, grades and academic credits. No official record is generated.",
    "facts": [
      {
        "label": "Issuing office",
        "value": "Demo Registrar"
      },
      {
        "label": "Sample fee",
        "value": "₱150"
      },
      {
        "label": "Processing",
        "value": "5 working days"
      },
      {
        "label": "Format",
        "value": "Printed or PDF (example)"
      }
    ],
    "nextSteps": [
      "Review the sample request checklist.",
      "Verify identity only through official channels."
    ]
  },
  {
    "id": "grades",
    "category": "Academic Records",
    "title": "Certification of Grades",
    "summary": "Example request for certified term grades.",
    "icon": "policy",
    "details": "The fictional service prepares a signed summary of grades for a selected term.",
    "facts": [
      {
        "label": "Office",
        "value": "Demo Registrar"
      },
      {
        "label": "Sample fee",
        "value": "₱75"
      },
      {
        "label": "Processing",
        "value": "3 working days"
      },
      {
        "label": "Requirement",
        "value": "Sample student ID"
      }
    ],
    "nextSteps": [
      "Select the example academic term.",
      "Confirm the actual request procedure."
    ]
  },
  {
    "id": "enrollment",
    "category": "Enrollment",
    "title": "Certificate of Enrollment",
    "summary": "Example proof of current enrollment.",
    "icon": "policy",
    "details": "A sample certificate confirms enrollment status for a fictional academic term.",
    "facts": [
      {
        "label": "Office",
        "value": "Demo Registrar"
      },
      {
        "label": "Sample fee",
        "value": "₱50"
      },
      {
        "label": "Processing",
        "value": "2 working days"
      },
      {
        "label": "Scope",
        "value": "Currently enrolled students (example)"
      }
    ],
    "nextSteps": [
      "Identify the intended purpose of the sample certificate.",
      "Do not upload real identity documents here."
    ]
  },
  {
    "id": "registration",
    "category": "Enrollment",
    "title": "Registration Form",
    "summary": "Illustrative course registration form.",
    "icon": "policy",
    "details": "The sample form includes program, year level, course selections and adviser approval fields.",
    "facts": [
      {
        "label": "Form ID",
        "value": "DEMO-REG-01"
      },
      {
        "label": "Office",
        "value": "Demo Registrar"
      },
      {
        "label": "Sample version",
        "value": "January 2027"
      },
      {
        "label": "Availability",
        "value": "Description only; no official download"
      }
    ],
    "nextSteps": [
      "Review the example fields.",
      "Obtain actual forms from official sources."
    ]
  },
  {
    "id": "clearance",
    "category": "Student Services",
    "title": "Student Clearance",
    "summary": "Sample checklist for office clearances.",
    "icon": "policy",
    "details": "The fictional process tracks library, laboratory and other service clearances before completion.",
    "facts": [
      {
        "label": "Form ID",
        "value": "DEMO-CLR-01"
      },
      {
        "label": "Office",
        "value": "Demo Student Services"
      },
      {
        "label": "Processing",
        "value": "3 working days (example)"
      },
      {
        "label": "Scope",
        "value": "End-of-term clearance"
      }
    ],
    "nextSteps": [
      "Review example office requirements.",
      "Confirm actual outstanding obligations separately."
    ]
  },
  {
    "id": "handbook",
    "category": "Guides & Forms",
    "title": "Student Handbook",
    "summary": "Illustrative guide to campus life and resources.",
    "icon": "policy",
    "details": "This example handbook outline covers academic procedures, student services and campus conduct.",
    "facts": [
      {
        "label": "Version",
        "value": "Demo 2027 edition"
      },
      {
        "label": "Office",
        "value": "Demo Student Affairs"
      },
      {
        "label": "Format",
        "value": "Guide outline"
      },
      {
        "label": "Availability",
        "value": "Not an official handbook"
      }
    ],
    "nextSteps": [
      "Explore the sample policy topics.",
      "Use the real approved handbook for decisions."
    ]
  }
];

export default function DocumentsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = documents.filter((item) =>
    (category === "All" || item.category === category) &&
    [item.title, item.category, item.summary, item.details, item.metadata, ...item.facts.flatMap((fact) => [fact.label, fact.value]), ...(item.nextSteps ?? [])].join(" ").toLowerCase().includes(normalizedQuery)
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
          <section className={styles.featured} aria-labelledby="featured-title" style={{ backgroundImage: "linear-gradient(90deg, rgba(5,39,29,.96), rgba(5,39,29,.82) 48%, rgba(5,39,29,.32)), url('/images/public-policies.jpg')" }}>
            <span className={styles.preview}>FICTIONAL CAMPUS DEMO</span>
            <h2 id="featured-title">Find the documents you need</h2>
            <p>Explore realistic fictional examples with detailed information. These are not official university resources or active offers.</p>
            <a href="#document-list" className={styles.featuredLink}>Browse documents ↓</a>
          </section>
          <section id="document-list" className={styles.listSection} aria-labelledby="list-title">
            <header className={styles.sectionHeading}>
              <p className={styles.eyebrow}>EXPLORE CAMPUS RESOURCES</p>
              <h2 id="list-title">Find your resources</h2>
              <p>Choose any card for its full fictional details. Not official campus information.</p>
            </header>
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
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "topic" : "topics"} · Fictional demo information</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching document topics</h3>
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
