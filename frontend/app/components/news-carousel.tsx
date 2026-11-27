"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import styles from "./news-carousel.module.css";

type Slide = {
  badge: string;
  title: string;
  subtitle: string;
  icon: "news" | "notice" | "policy";
  image: string;
  href: string;
  action: string;
};

// These are clearly labeled design previews, not real university announcements.
const slides: Slide[] = [
  {
    badge: "PREVIEW",
    title: "Campus News",
    subtitle: "Official campus updates will appear here.",
    icon: "news",
    image: "/images/campus-news.jpg",
    href: "/news",
    action: "Explore campus news",
  },
  {
    badge: "PREVIEW",
    title: "Important Notices",
    subtitle: "Public notices will be displayed here.",
    icon: "notice",
    image: "/images/important-notices.jpg",
    href: "/news",
    action: "View announcements",
  },
  {
    badge: "PREVIEW",
    title: "Public Policies",
    subtitle: "Policy updates will be linked here.",
    icon: "policy",
    image: "/images/public-policies.jpg",
    href: "/policies",
    action: "Explore policies",
  },
];

function SlideIcon({ name }: { name: Slide["icon"] }) {
  const common = {
    width: 34,
    height: 34,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };

  if (name === "notice") {
    return <svg {...common}><path d="M12 3 2.8 19h18.4L12 3Z" /><path d="M12 9v4M12 16h.01" /></svg>;
  }

  if (name === "policy") {
    return <svg {...common}><path d="M6 3h9l4 4v14H6z" /><path d="M14 3v5h5M9 13h7M9 17h7" /></svg>;
  }

  return <svg {...common}><path d="M4 4h16v16H4z" /><path d="M8 8h8M8 12h8M8 16h5" /></svg>;
}

const ROTATION_MS = 5000;

type CarouselState = {
  active: number;
  previous: number | null;
  direction: "next" | "previous";
  revision: number;
};

function moveTo(state: CarouselState, target: number, direction: CarouselState["direction"]): CarouselState {
  return {
    active: target,
    previous: target === state.active ? state.previous : state.active,
    direction: target === state.active ? state.direction : direction,
    revision: state.revision + 1,
  };
}

export default function NewsCarousel() {
  const [state, setState] = useState<CarouselState>({
    active: 0,
    previous: null,
    direction: "next",
    revision: 0,
  });
  const [paused, setPaused] = useState(false);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    if (paused || hovered || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setTimeout(() => {
      setState((current) => moveTo(current, (current.active + 1) % slides.length, "next"));
    }, ROTATION_MS);
    return () => window.clearTimeout(timer);
  }, [paused, hovered, state.revision]);

  function showPrevious() {
    setState((current) => moveTo(current, (current.active - 1 + slides.length) % slides.length, "previous"));
  }

  function showNext() {
    setState((current) => moveTo(current, (current.active + 1) % slides.length, "next"));
  }

  function showSlide(index: number) {
    setState((current) => index === current.active ? current : moveTo(current, index, index > current.active ? "next" : "previous"));
  }

  function renderSlide(index: number, outgoing: boolean) {
    const slide = slides[index];
    const motion = state.previous === null ? "" : outgoing
      ? state.direction === "next" ? styles.exitLeft : styles.exitRight
      : state.direction === "next" ? styles.enterRight : styles.enterLeft;

    return (
      <div
        key={`${state.revision}-${outgoing ? "out" : "in"}`}
        className={`${styles.slide} ${styles[slide.icon]} ${motion} ${outgoing ? styles.outgoing : ""}`}
        style={{ backgroundImage: `url("${slide.image}")` }}
        role="group"
        aria-roledescription="slide"
        aria-label={`${index + 1} of ${slides.length}`}
        aria-hidden={outgoing || undefined}
      >
        <div className={styles.slideContent}>
          <div className={styles.eyebrow}>
            <SlideIcon name={slide.icon} />
            <p className={styles.slideLabel}>{slide.badge}</p>
          </div>
          <h3>{slide.title}</h3>
          <p className={styles.subtitle}>{slide.subtitle}</p>
          {outgoing ? (
            <span className={styles.cta}>{slide.action} <span aria-hidden="true">→</span></span>
          ) : (
            <Link href={slide.href} className={styles.cta} onFocus={() => setPaused(true)}>
              {slide.action} <span aria-hidden="true">→</span>
            </Link>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={styles.carousel}
      role="region"
      aria-roledescription="carousel"
      aria-label="Campus news preview"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button type="button" className={styles.playButton} onClick={() => setPaused((value) => !value)} aria-label={paused ? "Resume automatic slideshow" : "Pause automatic slideshow"}>
        {paused ? "Play" : "Pause"}
      </button>

      <div className={styles.viewport} aria-live={paused ? "polite" : "off"}>
        {state.previous !== null && renderSlide(state.previous, true)}
        {renderSlide(state.active, false)}
      </div>

      <button type="button" className={`${styles.arrow} ${styles.prev}`} onClick={showPrevious} aria-label="Previous preview">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m15 18-6-6 6-6" />
        </svg>
      </button>
      <button type="button" className={`${styles.arrow} ${styles.next}`} onClick={showNext} aria-label="Next preview">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m9 18 6-6-6-6" />
        </svg>
      </button>

      <div className={styles.carouselDots} aria-label="Choose preview slide">
        {slides.map((slide, index) => (
          <button
            type="button"
            key={slide.title}
            className={`${styles.carouselDot} ${index === state.active ? styles.carouselDotActive : ""}`}
            onClick={() => showSlide(index)}
            aria-label={`Show slide ${index + 1}: ${slide.title}`}
            aria-current={index === state.active ? "true" : undefined}
          />
        ))}
      </div>
    </div>
  );
}
