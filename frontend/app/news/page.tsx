"use client";

import Link from "next/link";
import { useState } from "react";
import CampusHeader from "../components/campus-header";
import PortalCardGrid, { type PortalItem } from "../components/portal-card-grid";
import styles from "./news.module.css";

const categories = ["All", "Campus News", "Announcements", "Academic", "Events"] as const;
type Category = (typeof categories)[number];
type NewsItem = PortalItem & { category: Exclude<Category, "All"> };

// Fictional frontend-only examples. Never publish as verified campus information.
const news: NewsItem[] = [
  {
    id: "enrollment", category: "Academic", icon: "academic",
    title: "Second semester enrollment", summary: "Review a sample enrollment schedule, registration checklist and advising arrangements.", metadata: "Jan 4–15, 2027 · Sample schedule",
    details: "In this fictional scenario, continuing students complete academic advising before choosing their second-semester classes. Registration is organized by year level to reduce waiting times at the registrar.",
    facts: [{ label: "Sample dates", value: "January 4–15, 2027" }, { label: "Location", value: "Demo Registrar's Office" }, { label: "Audience", value: "Continuing students" }, { label: "Hours", value: "8 AM–5 PM (sample)" }],
    nextSteps: ["Prepare a sample registration checklist and previous term grades.", "Review the proposed course load with an academic adviser."],
  },
  {
    id: "library", category: "Campus News", icon: "library",
    title: "Library learning spaces", summary: "Discover a sample expansion of collaborative study areas and individual reading spaces.", metadata: "Jan 11, 2027 · Sample opening",
    details: "The fictional campus library introduces twelve collaborative study desks and a quiet reading zone. Students in this example can reserve study areas in two-hour sessions and use the space for group projects.",
    facts: [{ label: "Sample opening", value: "January 11, 2027" }, { label: "Location", value: "Demo Library, second floor" }, { label: "Capacity", value: "48 seats" }, { label: "Sample hours", value: "8 AM–7 PM, weekdays" }],
    nextSteps: ["Review the sample room-use guidelines.", "Keep noise low in designated quiet zones."],
  },
  {
    id: "id", category: "Announcements", icon: "notice",
    title: "Student ID renewal", summary: "Learn about a sample ID renewal window and the documents needed for a replacement card.", metadata: "Jan 6–22, 2027 · Sample notice",
    details: "This fictional announcement illustrates how a student services office might organize renewal of expired or damaged IDs. The sample process includes verification, a photo update and card collection.",
    facts: [{ label: "Sample period", value: "January 6–22, 2027" }, { label: "Office", value: "Demo Student Services Center" }, { label: "Processing", value: "3–5 working days (example)" }, { label: "Audience", value: "Students needing ID renewal" }],
    nextSteps: ["Prepare a sample proof of enrollment and previous ID.", "Confirm actual renewal procedures with your institution, not this demo."],
  },
  {
    id: "innovation", category: "Events", icon: "event",
    title: "Campus Innovation Week", summary: "Explore a sample three-day program of student research, workshops and technology exhibits.", metadata: "Jan 20–22, 2027 · Sample event",
    details: "In this fictional event, student teams present prototypes, attend introductory coding workshops and exchange ideas with faculty mentors. A project showcase closes the program on the final afternoon.",
    facts: [{ label: "Sample dates", value: "January 20–22, 2027" }, { label: "Venue", value: "Demo University Activity Center" }, { label: "Admission", value: "Free in this example" }, { label: "Participants", value: "Students and faculty" }],
    nextSteps: ["Sample day 1: project exhibits and opening program.", "Sample day 2: technology workshops.", "Sample day 3: presentations and recognition."],
  },
  {
    id: "advising", category: "Academic", icon: "academic",
    title: "Academic advising week", summary: "See how sample advising sessions help students plan courses and academic goals.", metadata: "Feb 1–5, 2027 · Sample schedule",
    details: "This illustrative advising week includes short one-on-one consultations for course planning, academic progress and study strategies. Each student is assigned a twenty-minute consultation in the fictional scenario.",
    facts: [{ label: "Sample dates", value: "February 1–5, 2027" }, { label: "Venue", value: "Demo College Advising Hub" }, { label: "Session length", value: "20 minutes" }, { label: "Audience", value: "All year levels" }],
    nextSteps: ["List possible courses and questions before a sample consultation.", "Discuss workload and academic goals with an adviser."],
  },
  {
    id: "services", category: "Announcements", icon: "service",
    title: "Student support desk", summary: "Find out how a sample support desk handles general campus inquiries and referrals.", metadata: "Jan 12, 2027 · Sample service",
    details: "The fictional student support desk assists with general campus questions, referrals to offices and navigation of student resources. It does not collect personal documents through this demo page.",
    facts: [{ label: "Sample launch", value: "January 12, 2027" }, { label: "Location", value: "Demo Student Center, ground floor" }, { label: "Sample hours", value: "9 AM–4 PM, weekdays" }, { label: "Services", value: "General inquiries and referrals" }],
    nextSteps: ["Identify the type of assistance needed.", "Contact the actual university's verified support channels for real requests."],
  },
];

export default function NewsPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const normalizedQuery = query.trim().toLowerCase();
  const results = news.filter((item) => {
    const matchesCategory = category === "All" || item.category === category;
    const searchable = [item.title, item.category, item.summary, item.details, item.metadata, ...item.facts.flatMap((fact) => [fact.label, fact.value]), ...(item.nextSteps ?? [])].join(" ").toLowerCase();
    return matchesCategory && searchable.includes(normalizedQuery);
  });

  function resetFilters() { setQuery(""); setCategory("All"); }

  return (
    <div className="page">
      <CampusHeader active="news" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="news-title">
          <Link href="/" className={styles.back}>← Back to Home</Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>STAY INFORMED</p>
            <h1 id="news-title">News &amp; Announcements</h1>
            <p>Explore campus stories, student reminders and academic updates.</p>
          </div>
          <section className={styles.featured} aria-labelledby="featured-title" style={{ backgroundImage: "linear-gradient(90deg, rgba(5,39,29,.96), rgba(5,39,29,.85) 43%, rgba(5,39,29,.25)), url('/images/campus-news.jpg')" }}>
            <span className={styles.preview}>FICTIONAL CAMPUS DEMO</span>
            <h2 id="featured-title">Your campus, in one place.</h2>
            <p>Explore sample stories, upcoming activities and student services in a more connected campus experience.</p>
            <a href="#news-list" className={styles.featuredLink}>Explore announcements ↓</a>
          </section>
          <section id="news-list" className={styles.listSection} aria-labelledby="list-title">
            <header className={styles.sectionHeading}>
              <p className={styles.eyebrow}>WHAT&apos;S HAPPENING</p>
              <h2 id="list-title">Around campus</h2>
              <p>Choose any card to explore its full details. All content below is fictional and for demonstration only.</p>
            </header>
            <label htmlFor="news-search" className={styles.searchLabel}>Search announcements</label>
            <div className={styles.searchRow}>
              <input id="news-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search news, dates or activities..." className={styles.search} />
              {(query || category !== "All") && <button type="button" onClick={resetFilters} className={styles.reset}>Clear filters</button>}
            </div>
            <div className={styles.filters} role="group" aria-label="Filter announcements by category">
              {categories.map((item) => <button type="button" key={item} className={styles.filter} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}
            </div>
            <p className={styles.count} role="status">{results.length} {results.length === 1 ? "result" : "results"} · Fictional demo information</p>
            {results.length === 0 ? (
              <div className={styles.empty}>
                <h3>No matching announcements</h3><p>Try another keyword or clear your filters.</p>
                <button type="button" className={styles.reset} onClick={resetFilters}>Show all announcements</button>
              </div>
            ) : <PortalCardGrid items={results} />}
          </section>
        </section>
      </main>
      <footer className={styles.footer}>CampusPilot · Public portal demo · Not official campus information</footer>
    </div>
  );
}
