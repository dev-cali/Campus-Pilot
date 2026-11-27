"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { createClient } from "@/utils/supabase/client";
import CampusHeader from "../components/campus-header";
import styles from "./settings.module.css";

const notificationOptions = [
  { key: "news", title: "Campus announcements", description: "News and important campus notices." },
  { key: "events", title: "Event reminders", description: "Reminders for campus activities and programs." },
  { key: "scholarships", title: "Scholarship updates", description: "Updates about scholarship and financial aid opportunities." },
  { key: "academics", title: "Academic reminders", description: "Updates about academic resources and schedules." },
] as const;

type NotificationKey = (typeof notificationOptions)[number]["key"];
type Preferences = Record<NotificationKey, boolean> & { compact: boolean };
const defaults: Preferences = {
  news: true,
  events: false,
  scholarships: true,
  academics: true,
  compact: false,
};

const preferenceKeys = Object.keys(defaults) as (keyof Preferences)[];

function readPreferences(value: unknown): Preferences {
  const result = { ...defaults };
  if (typeof value !== "object" || value === null || Array.isArray(value)) return result;
  const record = value as Record<string, unknown>;
  for (const key of preferenceKeys) {
    const stored = record[key];
    if (typeof stored === "boolean") result[key] = stored;
  }
  return result;
}

export default function SettingsPage() {
  const [supabase] = useState(() => createClient());
  const [saved, setSaved] = useState<Preferences>(defaults);
  const [draft, setDraft] = useState<Preferences>(defaults);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const accountId = useRef<string | null>(null);
  const generation = useRef(0);
  const savingRef = useRef(false);
  const changed = preferenceKeys.some((key) => draft[key] !== saved[key]);

  useEffect(() => {
    const current = ++generation.current;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT" || (accountId.current && session?.user.id !== accountId.current)) {
        generation.current += 1;
        accountId.current = null;
        setReady(false);
        setLoading(false);
        setSaved({ ...defaults });
        setDraft({ ...defaults });
        setMessage("");
        window.location.replace("/login?next=%2Fsettings");
      }
    });
    void supabase.auth.getUser().then(({ data, error }) => {
      if (generation.current !== current) return;
      if (error || !data.user || data.user.is_anonymous === true) {
        setFailed(true);
        return;
      }
      accountId.current = data.user.id;
      const preferences = readPreferences(data.user.user_metadata?.campuspilot_preferences);
      setSaved(preferences);
      setDraft({ ...preferences });
      setReady(true);
    }).catch(() => {
      if (generation.current === current) setFailed(true);
    }).finally(() => {
      if (generation.current === current) setLoading(false);
    });
    return () => {
      generation.current += 1;
      accountId.current = null;
      subscription.unsubscribe();
    };
  }, [supabase]);

  function update(key: keyof Preferences, value: boolean) {
    if (savingRef.current || !ready) return;
    setDraft((previous) => ({ ...previous, [key]: value }));
    setMessage("");
    setFailed(false);
  }

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const expectedId = accountId.current;
    if (!ready || !expectedId || !changed || savingRef.current) return;
    const current = generation.current;
    const submitted = { ...draft };
    savingRef.current = true;
    setSaving(true);
    setFailed(false);
    setMessage("");
    try {
      const { data: verified, error: verifyError } = await supabase.auth.getUser();
      if (generation.current !== current) return;
      if (verifyError || !verified.user || verified.user.is_anonymous === true || verified.user.id !== expectedId) {
        setFailed(true);
        setMessage("Unable to verify your account. Sign in again before saving.");
        return;
      }
      const { data, error } = await supabase.auth.updateUser({
        data: { campuspilot_preferences: submitted },
      });
      if (generation.current !== current) return;
      if (error || !data.user || data.user.id !== expectedId) {
        setFailed(true);
        setMessage("Unable to save preferences. Your changes are still available to retry.");
        return;
      }
      const persisted = readPreferences(data.user.user_metadata?.campuspilot_preferences);
      if (preferenceKeys.some((key) => persisted[key] !== submitted[key])) {
        setFailed(true);
        setMessage("Could not confirm the saved preferences. Please try again.");
        return;
      }
      setSaved(persisted);
      setDraft({ ...persisted });
      setMessage("Your preferences have been saved to your account.");
    } catch {
      if (generation.current === current) {
        setFailed(true);
        setMessage("Unable to connect. Please try again.");
      }
    } finally {
      savingRef.current = false;
      if (generation.current === current) setSaving(false);
    }
  }

  function discard() {
    if (savingRef.current) return;
    setDraft({ ...saved });
    setFailed(false);
    setMessage("Unsaved changes discarded.");
  }

  function resetDefaults() {
    if (savingRef.current) return;
    setDraft({ ...defaults });
    setFailed(false);
    setMessage("Defaults selected. Save changes to apply them to your account.");
  }

  return (
    <div className="page">
      {/* Profile denotes the account area; the shared header has no Settings tab yet. */}
      <CampusHeader active="profile" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="settings-title">
          <nav className={styles.backLinks} aria-label="Account navigation">
            <Link href="/">← Back to Home</Link>
            <Link href="/profile">My Profile</Link>
          </nav>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>MY ACCOUNT</p>
            <h1 id="settings-title">Account Settings</h1>
            <p>Manage your notification preferences and personalize your CampusPilot experience.</p>
          </div>
          {loading ? (
            <p className={styles.notice} role="status">Loading your preferences…</p>
          ) : !ready ? (
            <aside className={styles.notice} role="alert">
              <strong>Unable to load your settings.</strong>
              <p>Check your connection or sign in again.</p>
              <div className={styles.actions}>
                <button type="button" className={styles.secondary} onClick={() => window.location.reload()}>Try again</button>
                <Link href="/login?next=%2Fsettings" className={styles.profileLink}>Sign in</Link>
              </div>
            </aside>
          ) : (
          <>
          <aside className={styles.notice}>
            <strong>Connected account</strong>
            <p>Preferences are saved to your account. Notifications are not delivered yet, and compact layout currently affects only the example cards.</p>
          </aside>
          <form className={styles.form} onSubmit={savePreferences} aria-busy={saving}>
            <fieldset className={styles.panel} disabled={saving}>
              <legend>Notifications</legend>
              <p className={styles.description}>Choose the types of updates you would like to receive when notifications are connected.</p>
              {notificationOptions.map(({ key, title, description }) => (
                <label className={styles.setting} key={key}>
                  <span><strong>{title}</strong><small>{description}</small></span>
                  <input type="checkbox" checked={draft[key]} onChange={(event) => update(key, event.target.checked)} />
                </label>
              ))}
            </fieldset>
            <fieldset className={styles.panel} disabled={saving}>
              <legend>Appearance</legend>
              <label className={styles.setting}>
                <span><strong>Compact layout</strong><small>Reduce spacing in the example cards below. This does not change other pages.</small></span>
                <input type="checkbox" checked={draft.compact} onChange={(event) => update("compact", event.target.checked)} />
              </label>
              <div className={`${styles.example} ${draft.compact ? styles.compact : ""}`} aria-label="Appearance preview">
                <div><strong>Campus news</strong><small>Example resource card</small></div>
                <div><strong>Academic resources</strong><small>Example resource card</small></div>
              </div>
            </fieldset>
            <div className={styles.actions}>
              <button type="submit" className={styles.primary} disabled={saving || !changed}>{saving ? "Saving…" : "Save changes"}</button>
              <button type="button" className={styles.secondary} onClick={discard} disabled={saving || !changed}>Discard changes</button>
              <button type="button" className={styles.secondary} onClick={resetDefaults} disabled={saving || preferenceKeys.every((key) => draft[key] === defaults[key])}>Reset to defaults</button>
            </div>
            <p role={failed ? "alert" : "status"} className={`${styles.status} ${failed ? styles.error : ""}`}>{message || (changed ? "You have unsaved changes." : "")}</p>
          </form>
          </>
          )}
          <section className={styles.account} aria-labelledby="account-title">
            <h2 id="account-title">Account and privacy</h2>
            <p>View and edit your account profile. Email and password changes and privacy requests will be connected in a later phase.</p>
            <Link className={styles.profileLink} href="/profile">View My Profile →</Link>
          </section>
        </section>
      </main>
      <footer className={styles.footer}>CampusPilot · Portal preview</footer>
    </div>
  );
}
