"use client";

import { useEffect, useId, useRef, useState } from "react";
import styles from "./portal-card-grid.module.css";

const iconPaths = {
  news: "M4 5h16v14H4z M8 9h8 M8 13h8 M8 16h5",
  notice: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4",
  academic: "M2 9l10-5 10 5-10 5z M6 11v6c3 3 9 3 12 0v-6 M22 9v7",
  event: "M4 6h16v15H4z M8 3v6 M16 3v6 M4 11h16 M8 15h2 M14 15h2",
  library: "M12 6C8 3 4 4 3 5v14c3-2 6-2 9 0 3-2 6-2 9 0V5c-1-1-5-2-9 1z M12 6v13",
  service: "M4 6h16v14H4z M8 6V3h8v3 M8 12h8 M12 8v8",
  policy: "M6 3h9l4 4v14H6z M14 3v5h5 M9 13h7 M9 17h7",
  scholarship: "M12 3l3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z",
  department: "M3 9l9-6 9 6 M5 10v10 M10 10v10 M14 10v10 M19 10v10 M3 21h18",
} as const;

export type PortalItem = {
  id: string;
  category: string;
  title: string;
  summary: string;
  icon: keyof typeof iconPaths;
  metadata?: string;
  details: string;
  facts: { label: string; value: string }[];
  nextSteps?: string[];
};

function ItemIcon({ name }: { name: PortalItem["icon"] }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={iconPaths[name]} />
    </svg>
  );
}

export default function PortalCardGrid({ items }: { items: readonly PortalItem[] }) {
  const [selected, setSelected] = useState<PortalItem | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const element = dialog.current;
    if (selected && element && !element.open) element.showModal();
  }, [selected]);

  return (
    <>
      <div className={styles.grid}>
        {items.map((item) => (
          <article key={item.id} className={styles.card}>
            <button type="button" className={styles.cardButton} onClick={() => setSelected(item)} aria-haspopup="dialog" aria-label={`View details: ${item.title}`}>
              <span className={styles.icon}><ItemIcon name={item.icon} /></span>
              <span className={styles.category}>{item.category} · Demo</span>
              <span className={styles.title}>{item.title}</span>
              <span className={styles.summary}>{item.summary}</span>
              {item.metadata && <span className={styles.metadata}>{item.metadata}</span>}
              <span className={styles.action}>View details <span aria-hidden="true">→</span></span>
            </button>
          </article>
        ))}
      </div>
      <dialog ref={dialog} className={styles.dialog} aria-labelledby={titleId} aria-describedby={descriptionId} onClose={() => setSelected(null)}>
        <div className={styles.dialogBody}>
          <div className={styles.dialogTop}>
            <span className={styles.demo}>FICTIONAL DEMO</span>
            <button type="button" className={styles.closeIcon} aria-label="Close details" onClick={() => dialog.current?.close()}>×</button>
          </div>
          <p className={styles.dialogCategory}>{selected?.category}</p>
          <h2 id={titleId}>{selected?.title ?? "Details"}</h2>
          <p id={descriptionId} className={styles.disclaimer}>Illustrative information only. Not an official university announcement or instruction.</p>
          {selected && <>
            <p className={styles.details}>{selected.details}</p>
            <dl className={styles.facts}>
              {selected.facts.map((fact) => <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>)}
            </dl>
            {!!selected.nextSteps?.length && <section className={styles.steps}>
              <h3>Sample guidance</h3>
              <ul>{selected.nextSteps.map((step) => <li key={step}>{step}</li>)}</ul>
            </section>}
          </>}
          <button type="button" className={styles.closeButton} onClick={() => dialog.current?.close()}>Close details</button>
        </div>
      </dialog>
    </>
  );
}
