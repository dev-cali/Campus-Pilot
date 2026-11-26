import Link from "next/link";
import type { ReactNode } from "react";
import NewsCarousel from "./news-carousel";
import CampusHeader from "./campus-header";
import styles from "./home-dashboard.module.css";

type FeatureIconName = "news" | "assistant" | "policy" | "scholarship" | "event" | "document" | "academic" | "department";

type FeatureLink = {
  label: string;
  description: string;
  href: string;
  icon: FeatureIconName;
};

const publicFeatures: FeatureLink[] = [
  {
    label: "News & Announcements",
    description: "Check the public campus updates area.",
    href: "#announcements",
    icon: "news",
  },
  {
    label: "AI Assistant",
    description: "Ask questions and explore available information.",
    href: "/ai",
    icon: "assistant",
  },
  {
    label: "Policies",
    description: "Explore policy information through the AI Assistant.",
    href: "/ai?category=Policies",
    icon: "policy",
  },
];

const protectedFeatures: FeatureLink[] = [
  {
    label: "Scholarships",
    description: "Scholarship opportunities and requirements.",
    href: "/scholarships",
    icon: "scholarship",
  },
  {
    label: "Events",
    description: "Campus activities and event information.",
    href: "/events",
    icon: "event",
  },
  {
    label: "Documents",
    description: "Student forms and document services.",
    href: "/documents",
    icon: "document",
  },
  {
    label: "Academics",
    description: "Academic information and student resources.",
    href: "/academics",
    icon: "academic",
  },
  {
    label: "Departments",
    description: "Department directory and information.",
    href: "/departments",
    icon: "department",
  },
];

function FeatureIcon({ name }: { name: FeatureIconName }) {
  const common = {
    width: 19,
    height: 19,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };

  const shapes: Record<FeatureIconName, ReactNode> = {
    news: <><path d="M4 4h16v16H4z" /><path d="M8 8h8M8 12h8M8 16h5" /></>,
    assistant: <><path d="M12 3a8 8 0 0 0-8 8v3a3 3 0 0 0 3 3h1v-6H7a5 5 0 0 1 10 0h-1v6h1a3 3 0 0 0 3-3v-3a8 8 0 0 0-8-8Z" /><path d="M9 20h6" /></>,
    policy: <><path d="M6 3h9l4 4v14H6z" /><path d="M14 3v5h5M9 13h7M9 17h7" /></>,
    scholarship: <><circle cx="12" cy="12" r="9" /><path d="M12 6v12M15 9c-3-2-6 0-6 2s6 1 6 4-4 3-6 1" /></>,
    event: <><rect x="4" y="5" width="16" height="16" rx="3" /><path d="M8 3v4M16 3v4M4 11h16" /></>,
    document: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v4h4M9 13h6M9 17h6" /></>,
    academic: <><path d="m2 9 10-5 10 5-10 5z" /><path d="M6 12v5c3 2 9 2 12 0v-5M22 9v6" /></>,
    department: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M9 20v-5h6v5M8 8h2M14 8h2M8 11h2M14 11h2" /></>,
  };

  return <svg {...common}>{shapes[name]}</svg>;
}

function protectedHref(path: string) {
  return `/login?next=${encodeURIComponent(path)}`;
}

export default function HomeDashboard() {
  return (
    <div className={`page ${styles.page}`}>
      <CampusHeader active="home" />

      <main className="layout">
        <aside className={`savedpanel ${styles.explorePanel}`} aria-label="CampusPilot features">
          <div className="shead">
            <h2>Explore</h2>
          </div>

          <nav className={styles.featureNav} aria-label="Campus features">
            {publicFeatures.map((feature) => (
              <Link href={feature.href} className={styles.featureNavLink} key={feature.label}>
                <FeatureIcon name={feature.icon} />
                <span>{feature.label}</span>
              </Link>
            ))}
            {protectedFeatures.map((feature) => (
              <Link
                href={protectedHref(feature.href)}
                className={styles.featureNavLink}
                key={feature.label}
              >
                <FeatureIcon name={feature.icon} />
                <span>{feature.label}</span>
              </Link>
            ))}
          </nav>

        </aside>

        <section className={`card ${styles.dashboardCard}`}>
          <div className={styles.dashboardContent}>
            <section className={styles.welcomeSection}>
              <p className={styles.eyebrow}>STUDENT &amp; FACULTY PORTAL</p>
              <h1>Welcome to CampusPilot</h1>
              <p>
                Your starting point for campus updates, public policies, and AI-powered
                assistance. Explore campus resources in one place.
              </p>
            </section>

            <section className={styles.announcementsSection} id="announcements" aria-labelledby="announcements-title">
              <div className={styles.sectionHeading}>
                <div>
                  <p className={styles.eyebrow}>STAY INFORMED</p>
                  <h2 className="news-heading" id="announcements-title">News &amp; Announcements</h2>
                </div>
                <span className={styles.previewBadge}>Preview</span>
              </div>

              <NewsCarousel />

              <p className={styles.contentNotice}>
                Preview slides only. Live announcements will appear here once an approved
                campus news source is connected.
              </p>
            </section>

            <section className={styles.quickAccessSection} aria-labelledby="quick-access-title">
              <div className={styles.sectionHeading}>
                <div>
                  <p className={styles.eyebrow}>GET STARTED</p>
                  <h2 id="quick-access-title">Public features</h2>
                </div>
              </div>

              <div className={styles.quickAccessGrid}>
                {publicFeatures.map((feature) => (
                  <Link href={feature.href} className={styles.quickAccessCard} key={feature.label}>
                    <span className={styles.quickAccessIcon}><FeatureIcon name={feature.icon} /></span>
                    <span className={styles.quickAccessText}>
                      <strong>{feature.label}</strong>
                      <small>{feature.description}</small>
                    </span>
                    <span className={styles.cardArrow} aria-hidden="true">↗</span>
                  </Link>
                ))}
              </div>
            </section>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        CampusPilot <span aria-hidden="true">·</span> Public portal preview
      </footer>
    </div>
  );
}
