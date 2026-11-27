"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import styles from "./departments.module.css";

const categories = ["All", "Academic", "Administration", "Student Services"] as const;
type Category = (typeof categories)[number];
type Department = { id: string; name: string; category?: Exclude<Category, "All">; summary?: string };
type LiveStatus = "idle" | "loading" | "ready" | "empty" | "error";

// Fictional directory examples, not verified offices at the university.
const previewDepartments: Department[] = [
  { id: "registrar", name: "Registrar's Office", category: "Administration", summary: "Example directory entry for enrollment, academic records, and document requests." },
  { id: "admissions", name: "Admissions Office", category: "Administration", summary: "Example entry for application and admission-related inquiries." },
  { id: "computing", name: "College of Computing", category: "Academic", summary: "Example entry for computing programs and academic inquiries." },
  { id: "engineering", name: "College of Engineering", category: "Academic", summary: "Example entry for engineering programs and academic inquiries." },
  { id: "student-affairs", name: "Student Affairs Office", category: "Student Services", summary: "Example entry for student organizations, activities, and support." },
  { id: "library", name: "University Library", category: "Student Services", summary: "Example entry for learning resources and library services." },
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

  const source = mode === "preview" ? previewDepartments : departments;
  const results = source.filter((department) =>
    (mode === "live" || category === "All" || department.category === category) &&
    `${department.name} ${department.category ?? ""} ${department.summary ?? ""}`.toLowerCase().includes(query.trim().toLowerCase())
  );

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
          <section className={styles.featured} aria-labelledby="directory-intro">
            <div className={styles.heroIcon}><OfficeIcon /></div>
            <div>
              <span className={styles.preview}>DIRECTORY PREVIEW</span>
              <h2 id="directory-intro">Find the right office</h2>
              <p>Browse sample departments or load names from the existing connected directory. Official contacts, services, and office hours have not been verified.</p>
            </div>
          </section>
          <section className={styles.listSection} aria-labelledby="directory-title">
            <h2 id="directory-title">Browse departments</h2>
            <div className={styles.filters} role="group" aria-label="Directory source">
              <button className={styles.filter} type="button" aria-pressed={mode === "preview"} onClick={() => { setMode("preview"); resetFilters(); }}>Sample directory</button>
              <button className={styles.filter} type="button" aria-pressed={mode === "live"} disabled={status === "loading"} onClick={loadDirectory}>{status === "loading" ? "Loading directory..." : "Load connected directory"}</button>
            </div>
            {mode === "preview" && <p className={styles.count}>Sample entries only — these are not confirmed university departments.</p>}
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
              <p role="status" className={styles.count}>{results.length} {results.length === 1 ? "department" : "departments"} · {mode === "preview" ? "Preview" : "Connected directory names"}</p>
              {results.length ? <div className={styles.grid}>
                {results.map((department) => <article key={department.id} className={styles.article}>
                  <span className={styles.officeIcon}><OfficeIcon /></span>
                  <span className={styles.category}>{department.category ?? "Directory entry"}</span>
                  <h3>{department.name}</h3>
                  <p>{department.summary ?? "Name supplied by the connected directory."}</p>
                  <details className={styles.details}>
                    <summary>View details</summary>
                    <dl className={styles.info}><dt>Services</dt><dd>{mode === "preview" ? "Illustrative description only" : "Not supplied"}</dd><dt>Contact information</dt><dd>Not available</dd><dt>Office hours</dt><dd>Not available</dd></dl>
                  </details>
                </article>)}
              </div> : <div className={styles.empty}><h3>No matching departments</h3><p>Try a different search or category.</p><button type="button" className={styles.reset} onClick={resetFilters}>Clear filters</button></div>}
            </>}
          </section>
        </section>
      </main>
      <footer className={styles.footer}>CampusPilot · Department directory</footer>
    </div>
  );
}
