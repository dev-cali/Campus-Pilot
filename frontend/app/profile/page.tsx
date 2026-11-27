"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/utils/supabase/client";
import CampusHeader from "../components/campus-header";
import styles from "./profile.module.css";

type Profile = {
  displayName: string;
  program: string;
  bio: string;
};

function readProfile(user: User): Profile {
  const metadata = user.user_metadata;
  const name = metadata?.full_name;
  return {
    displayName: typeof name === "string" && name.trim() ? name.trim() : user.email || "My Account",
    program: typeof metadata?.campuspilot_program === "string" ? metadata.campuspilot_program : "",
    bio: typeof metadata?.campuspilot_bio === "string" ? metadata.campuspilot_bio : "",
  };
}

export default function ProfilePage() {
  const [supabase] = useState(() => createClient());
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [draft, setDraft] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [saveError, setSaveError] = useState(false);
  const accountId = useRef<string | null>(null);
  const generation = useRef(0);
  const savingRef = useRef(false);

  useEffect(() => {
    const current = ++generation.current;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      // Do not call asynchronous Supabase methods inside this callback.
      if (event === "SIGNED_OUT" || (accountId.current && session?.user.id !== accountId.current)) {
        generation.current += 1;
        accountId.current = null;
        setUser(null);
        setDraft(null);
        setMessage("");
        setSaving(false);
        setLoading(false);
        window.location.replace("/login?next=%2Fprofile");
      }
    });

    void supabase.auth.getUser().then(({ data, error }) => {
      if (generation.current !== current) return;
      if (error || !data.user || data.user.is_anonymous === true) {
        setLoadError(true);
        return;
      }
      accountId.current = data.user.id;
      setUser(data.user);
    }).catch(() => {
      if (generation.current === current) setLoadError(true);
    }).finally(() => {
      if (generation.current === current) setLoading(false);
    });

    return () => {
      generation.current += 1;
      accountId.current = null;
      subscription.unsubscribe();
    };
  }, [supabase]);

  const profile = user ? readProfile(user) : null;
  const initials = profile?.displayName.trim().split(/\s+/).slice(0, 2).map((part) => Array.from(part)[0]?.toUpperCase() ?? "").join("") || "?";

  function startEditing() {
    if (!profile || savingRef.current) return;
    setDraft({ ...profile });
    setMessage("");
    setSaveError(false);
  }

  function cancelEditing() {
    if (savingRef.current) return;
    setDraft(null);
    setSaveError(false);
    setMessage("Unsaved changes discarded.");
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft || !user || savingRef.current) return;
    const displayName = draft.displayName.trim();
    const program = draft.program.trim();
    const bio = draft.bio.trim();
    if (!displayName || displayName.length > 80 || program.length > 100 || bio.length > 300) {
      setSaveError(true);
      setMessage("Enter a display name of 1–80 characters and keep the optional fields within their limits.");
      return;
    }

    const current = generation.current;
    const expectedId = user.id;
    savingRef.current = true;
    setSaving(true);
    setSaveError(false);
    setMessage("");
    try {
      // Recheck the account before writing, in case the session changed.
      const { data: verified, error: verificationError } = await supabase.auth.getUser();
      if (generation.current !== current) return;
      if (verificationError || !verified.user || verified.user.is_anonymous === true || verified.user.id !== expectedId) {
        setSaveError(true);
        setMessage("Unable to verify your account. Please sign in again before saving.");
        return;
      }
      const { data, error } = await supabase.auth.updateUser({
        data: {
          full_name: displayName,
          campuspilot_program: program,
          campuspilot_bio: bio,
        },
      });
      if (generation.current !== current) return;
      if (error || !data.user || data.user.id !== expectedId) {
        setSaveError(true);
        setMessage("Unable to save your profile. Please try again.");
        return;
      }
      setUser(data.user);
      setDraft(null);
      setMessage("Your profile has been saved successfully.");
    } catch {
      if (generation.current === current) {
        setSaveError(true);
        setMessage("Unable to connect. Please try again later.");
      }
    } finally {
      savingRef.current = false;
      if (generation.current === current) setSaving(false);
    }
  }

  return (
    <div className="page">
      <CampusHeader active="profile" />
      <main className={styles.main}>
        <section className={`card ${styles.content}`} aria-labelledby="profile-title">
          <Link href="/" className={styles.back}>← Back to Home</Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>MY ACCOUNT</p>
            <h1 id="profile-title">My Profile</h1>
            <p>View and manage your campus profile.</p>
          </div>
          {loading ? (
            <p role="status" className={styles.notice}>Loading your account information…</p>
          ) : loadError || !user || !profile ? (
            <aside className={styles.notice} role="alert">
              <strong>Unable to load your profile.</strong>
              <p>Check your connection or sign in again.</p>
              <div className={styles.actions}>
                <button type="button" className={styles.secondary} onClick={() => window.location.reload()}>Try again</button>
                <Link href="/login?next=%2Fprofile" className={styles.back}>Sign in</Link>
              </div>
            </aside>
          ) : (
            <>
              <aside className={styles.notice}>
                <strong>Connected account</strong>
                <p>Your profile changes are saved to your CampusPilot account. Optional profile fields are self-reported; do not enter sensitive student records.</p>
              </aside>
              <div className={styles.grid}>
                <section className={styles.summary} aria-labelledby="summary-title">
                  <div className={styles.avatar} aria-hidden="true">{initials}</div>
                  <h2 id="summary-title">{profile.displayName}</h2>
                  <p>{user.email || "Email not available"}</p>
                  <p>{profile.program || "Academic program not provided"}</p>
                  <span className={styles.tag}>Personal profile</span>
                  <div className={styles.actions}>
                    {!draft && <button type="button" className={styles.primary} onClick={startEditing}>Edit profile</button>}
                  </div>
                </section>
                <section className={styles.details} aria-labelledby="details-title">
                  <h2 id="details-title">Profile information</h2>
                  {draft ? (
                    <form className={styles.form} onSubmit={saveProfile}>
                      <label htmlFor="display-name">Display name</label>
                      <input id="display-name" value={draft.displayName} onChange={(event) => setDraft({ ...draft, displayName: event.target.value })} required maxLength={80} autoComplete="name" disabled={saving} />
                      <label htmlFor="program">Academic program (optional)</label>
                      <input id="program" value={draft.program} onChange={(event) => setDraft({ ...draft, program: event.target.value })} maxLength={100} placeholder="Your academic program" autoComplete="off" disabled={saving} />
                      <label htmlFor="bio">About me (optional)</label>
                      <textarea id="bio" value={draft.bio} onChange={(event) => setDraft({ ...draft, bio: event.target.value })} maxLength={300} rows={4} placeholder="Write a short introduction." disabled={saving} />
                      <span className={styles.count}>{draft.bio.length}/300 characters</span>
                      <div className={styles.actions}>
                        <button type="submit" className={styles.primary} disabled={saving || !draft.displayName.trim()}>{saving ? "Saving…" : "Save changes"}</button>
                        <button type="button" className={styles.secondary} disabled={saving} onClick={cancelEditing}>Cancel</button>
                      </div>
                    </form>
                  ) : (
                    <dl className={styles.fields}>
                      <div><dt>Display name</dt><dd>{profile.displayName}</dd></div>
                      <div><dt>Academic program</dt><dd>{profile.program || "Not provided"}</dd></div>
                      <div><dt>About me</dt><dd>{profile.bio || "No introduction added yet."}</dd></div>
                    </dl>
                  )}
                  {message && <p role={saveError ? "alert" : "status"} className={saveError ? styles.error : styles.status}>{message}</p>}
                </section>
              </div>
              <section className={styles.accountNote} aria-labelledby="account-note-title">
                <h2 id="account-note-title">Account information</h2>
                <dl className={styles.fields}>
                  <div><dt>Registered email</dt><dd>{user.email || "Not available"}</dd></div>
                </dl>
                <p>Email and password changes are not included in this profile editor.</p>
                <Link href="/settings" className={styles.back}>Open account settings →</Link>
              </section>
            </>
          )}
        </section>
      </main>
      <footer className={styles.footer}>CampusPilot · Student &amp; Faculty Portal</footer>
    </div>
  );
}
