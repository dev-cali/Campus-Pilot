"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import PortalCardGrid, { type PortalItem } from "../components/portal-card-grid";
import styles from "./departments.module.css";

const categories = ["All", "Academic", "Administration", "Student Services"] as const;
type Category = (typeof categories)[number];
type Department = { id: string; name: string; category?: Exclude<Category, "All">; summary?: string };
type LiveStatus = "idle" | "loading" | "ready" | "empty" | "error";

// Fictional directory examples, not verified offices at the university.
const previewDepartments: (PortalItem & { category: Exclude<Category, "All"> })[] = [
  {
    "id": "registrar",
    "category": "Administration",
    "title": "Registrar's Office",
    "summary": "Sample academic records and enrollment services.",
    "icon": "department",
    "details": "The fictional registrar manages enrollment records, academic certifications and transcript requests.",
    "facts": [
      {
        "label": "Location",
        "value": "Demo Administration Building, ground floor"
      },
      {
        "label": "Hours",
        "value": "8 AM–5 PM, weekdays"
      },
      {
        "label": "Services",
        "value": "Registration, transcripts, certifications"
      },
      {
        "label": "Contact",
        "value": "No real contact provided"
      }
    ],
    "nextSteps": [
      "Review the sample document checklist.",
      "Use verified university channels for actual requests."
    ]
  },
  {
    "id": "admissions",
    "category": "Administration",
    "title": "Admissions Office",
    "summary": "Sample assistance for prospective students.",
    "icon": "department",
    "details": "The fictional office provides application guidance and program information.",
    "facts": [
      {
        "label": "Location",
        "value": "Demo Administration Building, room 102"
      },
      {
        "label": "Hours",
        "value": "8 AM–5 PM, weekdays"
      },
      {
        "label": "Services",
        "value": "Application guidance, program inquiries"
      },
      {
        "label": "Contact",
        "value": "No real contact provided"
      }
    ],
    "nextSteps": [
      "Review example admission requirements.",
      "Confirm official deadlines independently."
    ]
  },
  {
    "id": "computing",
    "category": "Academic",
    "title": "College of Computing",
    "summary": "Explore sample computing programs and academic support.",
    "icon": "department",
    "details": "The fictional college offers computing courses, advising and project consultations.",
    "facts": [
      {
        "label": "Location",
        "value": "Demo Technology Building, room 201"
      },
      {
        "label": "Hours",
        "value": "9 AM–4 PM, weekdays"
      },
      {
        "label": "Services",
        "value": "Program advising, lab inquiries"
      },
      {
        "label": "Contact",
        "value": "No real contact provided"
      }
    ],
    "nextSteps": [
      "Prepare sample course questions.",
      "Check real program offerings with the institution."
    ]
  },
  {
    "id": "engineering",
    "category": "Academic",
    "title": "College of Engineering",
    "summary": "Sample engineering program and laboratory guidance.",
    "icon": "department",
    "details": "The fictional college coordinates engineering courses, laboratory activities and design projects.",
    "facts": [
      {
        "label": "Location",
        "value": "Demo Engineering Building, room 205"
      },
      {
        "label": "Hours",
        "value": "9 AM–4 PM, weekdays"
      },
      {
        "label": "Services",
        "value": "Course advising, laboratory inquiries"
      },
      {
        "label": "Contact",
        "value": "No real contact provided"
      }
    ],
    "nextSteps": [
      "Review example lab schedules.",
      "Confirm actual laboratory guidelines."
    ]
  },
  {
    "id": "student-affairs",
    "category": "Student Services",
    "title": "Student Affairs Office",
    "summary": "Sample student organization and support services.",
    "icon": "department",
    "details": "The fictional office assists student groups, provides general referrals and coordinates campus activities.",
    "facts": [
      {
        "label": "Location",
        "value": "Demo Student Center, ground floor"
      },
      {
        "label": "Hours",
        "value": "9 AM–4 PM, weekdays"
      },
      {
        "label": "Services",
        "value": "Organizations, activities, referrals"
      },
      {
        "label": "Contact",
        "value": "No real contact provided"
      }
    ],
    "nextSteps": [
      "Explore sample student services.",
      "Use official channels for personal concerns."
    ]
  },
  {
    "id": "library",
    "category": "Student Services",
    "title": "University Library",
    "summary": "Sample study areas and learning resources.",
    "icon": "department",
    "details": "The fictional library provides reading spaces, book lending and collaborative study desks.",
    "facts": [
      {
        "label": "Location",
        "value": "Demo Library Building"
      },
      {
        "label": "Hours",
        "value": "8 AM–7 PM, weekdays"
      },
      {
        "label": "Services",
        "value": "Study spaces, lending, research guidance"
      },
      {
        "label": "Contact",
        "value": "No real contact provided"
      }
    ],
    "nextSteps": [
      "Review example room-use guidelines.",
      "Confirm real opening hours independently."
    ]
  }
];

function parseDepartments(value: unknown): Department[] {
  if (!value || typeof value !== "object" || !("departments" in value) || !Array.isArray(value.departments)) {
    throw new Error("invalid_directory");
  }
  const names = new Set<string>();
  const result: Department[] = [];
  for (const item of value.departments as unknown[]) {
    if (!item || typeof item !== "object" || !("name" in item) || typeof item.name !== "string" || !item.name.trim()) {
      throw new Error("invalid_department");
    }
    const name = item.name.trim();
    const key = name.toLowerCase();
    if (names.has(key)) continue;
    names.add(key);
    result.push({ id: key, name });
  }
  return result;
}

function OfficeIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 21v-5h6v5M8 7h2m4 0h2M8 11h2m4 0h2"/></svg>;
}

export default function DepartmentsPage() {
  const [mode, setMode] = useState<"preview" | "live">("preview");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const [departments, setDepartments] = useState<Department[]>([]);
  const [status, setStatus] = useState<LiveStatus>("idle");
  const [notice, setNotice] = useState("");

  const normalizedQuery = query.trim().toLowerCase();
  const previewResults = previewDepartments.filter((item) =>
    (category === "All" || item.category === category) &&
    [item.title, item.category, item.summary, item.details, ...item.facts.flatMap((fact) => [fact.label, fact.value]), ...(item.nextSteps ?? [])].join(" ").toLowerCase().includes(normalizedQuery)
  );
  const liveResults = departments.filter((item) => item.name.toLowerCase().includes(normalizedQuery));
  const resultCount = mode === "preview" ? previewResults.length : liveResults.length;

  function resetFilters() {
    setQuery("");
    setCategory("All");
  }

  async function loadDirectory() {
    if (status === "loading") return;
    setMode("live");
    resetFilters();
    setStatus("loading");
    setDepartments([]);
    setNotice("");
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      // Preserve the original Sprint 1 endpoint. Do not send session tokens or credentials.
      const response = await fetch("https://campus-pilot-ziix.onrender.com/departments", {
        credentials: "omit", cache: "no-store", redirect: "error", signal: controller.signal,
      });
      if (response.status === 401 || response.status === 403) {
        setNotice("The connected directory requires authorized API access. Live integration is not configured here yet.");
        setStatus("error");
        return;
      }
      if (!response.ok) throw new Error("directory_unavailable");
      const data = parseDepartments(await response.json());
      setDepartments(data);
      setStatus(data.length ? "ready" : "empty");
    } catch {
      setNotice("The connected directory could not be loaded. You can retry or return to the sample directory.");
      setStatus("error");
    } finally {
      clearTimeout(timer);
    }
  }

  return (
    <div className="page">
      <CampusHeader active="departments" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="departments-title">
          <Link href="/" className={styles.back}>← Back to Home</Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>CAMPUS DIRECTORY</p>
            <h1 id="departments-title">Departments</h1>
            <p>Explore academic departments, administrative offices, and student services in one place.</p>
          </div>
          <section className={styles.featured} aria-labelledby="directory-intro" style={{ backgroundImage: "linear-gradient(90deg, rgba(5,39,29,.96), rgba(5,39,29,.82) 48%, rgba(5,39,29,.32)), url('/images/important-notices.jpg')" }}>
            <div className={styles.heroIcon}><OfficeIcon /></div>
            <div>
              <span className={styles.preview}>CAMPUS DIRECTORY</span>
              <h2 id="directory-intro">Find the right office</h2>
              <p>Browse sample departments or load names from the existing connected directory. Official contacts, services, and office hours have not been verified.</p>
            </div>
          </section>
          <section className={styles.listSection} aria-labelledby="directory-title">
            <header className={styles.sectionHeading}><p className={styles.eyebrow}>EXPLORE CAMPUS OFFICES</p><h2 id="directory-title">Find campus support</h2><p>Explore fictional office details, or load connected names separately.</p></header>
            <div className={styles.filters} role="group" aria-label="Directory source">
              <button className={styles.filter} type="button" aria-pressed={mode === "preview"} onClick={() => { setMode("preview"); resetFilters(); }}>Sample directory</button>
              <button className={styles.filter} type="button" aria-pressed={mode === "live"} disabled={status === "loading"} onClick={loadDirectory}>{status === "loading" ? "Loading directory..." : "Load connected directory"}</button>
            </div>
            {mode === "preview" && <p className={styles.count}>Fictional demo entries only — not confirmed university departments.</p>}
            {mode === "live" && status === "loading" && <p role="status" className={styles.count}>Loading department names...</p>}
            {mode === "live" && status === "error" && <div className={styles.empty} role="status"><h3>Directory unavailable</h3><p>{notice}</p><button type="button" className={styles.reset} onClick={loadDirectory}>Retry</button></div>}
            {mode === "live" && status === "empty" && <div className={styles.empty} role="status"><h3>No departments returned</h3><p>The connected directory returned an empty list.</p></div>}
            {(mode === "preview" || (mode === "live" && status === "ready")) && <>
              <label htmlFor="department-search" className={styles.searchLabel}>Search departments</label>
              <div className={styles.searchRow}>
                <input id="department-search" type="search" className={styles.search} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by department name..." />
                {(query || category !== "All") && <button type="button" className={styles.reset} onClick={resetFilters}>Clear filters</button>}
              </div>
              {mode === "preview" && <div className={styles.filters} role="group" aria-label="Filter departments by category">
                {categories.map((item) => <button type="button" key={item} className={styles.filter} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}
              </div>}
              <p role="status" className={styles.count}>{resultCount} {resultCount === 1 ? "department" : "departments"} · {mode === "preview" ? "Preview" : "Connected directory names"}</p>
              {resultCount ? (mode === "preview" ? <PortalCardGrid items={previewResults} /> : <div className={styles.grid}>
                {liveResults.map((department) => <details key={department.id} className={styles.article}><summary className={styles.liveSummary}>
                  <span className={styles.officeIcon}><OfficeIcon /></span>
                  <span className={styles.category}>{department.category ?? "Directory entry"}</span>
                  <span className={styles.liveTitle}>{department.name}</span>
                  <span>Name supplied by the connected directory.</span><span className={styles.liveAction}>View details</span></summary>
                    <dl className={styles.info}><dt>Services</dt><dd>Not supplied</dd><dt>Contact information</dt><dd>Not available</dd><dt>Office hours</dt><dd>Not available</dd></dl>
                  </details>)}
              </div>) : <div className={styles.empty}><h3>No matching departments</h3><p>Try a different search or category.</p><button type="button" className={styles.reset} onClick={resetFilters}>Clear filters</button></div>}
            </>}
          </section>
        </section>
      </main>
      <footer className={styles.footer}>CampusPilot · Department directory</footer>
    </div>
  );
}
