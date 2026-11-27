"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState, type MouseEventHandler } from "react";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/utils/supabase/client";
import styles from "./campus-header.module.css";
import accountStyles from "./account-menu.module.css";

type CampusHeaderProps = {
  active: "home" | "news" | "ai" | "policies" | "departments" | "scholarships" | "events" | "documents" | "academics" | "profile" | "settings";
  onPoliciesClick?: MouseEventHandler<HTMLAnchorElement>;
  onAssistantClick?: MouseEventHandler<HTMLAnchorElement>;
};

export default function CampusHeader({
  active,
  onAssistantClick,
}: CampusHeaderProps) {
  const router = useRouter();

  // Initialize Supabase once.
  const [supabase] = useState(() => createClient());

  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [signOutError, setSignOutError] = useState("");
  const accountRef = useRef<HTMLDivElement>(null);
  const accountButtonRef = useRef<HTMLButtonElement>(null);
  const accountMenuId = useId();

  useEffect(() => {
    if (!accountOpen) return;

    function handleOutside(event: PointerEvent) {
      if (event.target instanceof Node && !accountRef.current?.contains(event.target)) {
        setAccountOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setAccountOpen(false);
        accountButtonRef.current?.focus();
      }
    }

    document.addEventListener("pointerdown", handleOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("pointerdown", handleOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [accountOpen]);

  // Initialize Supabase and monitor authentication changes.
  useEffect(() => {
    let mounted = true;
    let authEventReceived = false;

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      authEventReceived = true;

      if (!mounted) return;

      setUser(session?.user ?? null);
      if (!session?.user) setAccountOpen(false);
      setAuthReady(true);
    });

    // Verify the current authenticated user.
    void supabase.auth
      .getUser()
      .then(({ data, error }) => {
        if (!mounted || authEventReceived) return;

        setUser(error ? null : data.user);
        setAuthReady(true);
      })
      .catch(() => {
        if (!mounted || authEventReceived) return;

        setUser(null);
        setAuthReady(true);
      });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [supabase]);

  // Sign out the current Supabase user.
  const handleSignOut = async () => {
    if (isSigningOut) return;

    setIsSigningOut(true);
    setSignOutError("");

    try {
      const { error } = await supabase.auth.signOut();

      if (error) {
        setSignOutError("Unable to sign out. Please try again.");
        return;
      }

      setAccountOpen(false);
      router.replace("/");
      router.refresh();
    } catch {
      setSignOutError("Unable to sign out. Please try again.");
    } finally {
      setIsSigningOut(false);
    }
  };

  const fullName = user?.user_metadata?.full_name;

  const displayName =
    typeof fullName === "string" && fullName.trim()
      ? fullName
      : user?.email || "My Account";

  const initials = displayName.trim().split(/\s+/).slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase()).join("") || "U";

  return (
    <header className={`top-header ${styles.header} ${accountStyles.headerLayer}`}>
      <div className="brand-section">
        <Link
          href="/"
          className={`brand ${styles.brand}`}
          aria-label="CampusPilot home"
        >
          <span className="logo" aria-hidden="true">
            <svg
              width="19"
              height="19"
              viewBox="0 0 24 24"
              fill="#ffffff"
            >
              <path d="M12 2l2.4 7.4h7.6l-6.2 4.5 2.4 7.4-6.2-4.5-6.2 4.5 2.4-7.4-6.2-4.5h7.6z" />
            </svg>
          </span>

          <span>CampusPilot</span>
        </Link>
      </div>

      <nav className="nav-bar" aria-label="Main navigation">
        <Link
          href="/"
          className="home-btn"
          aria-current={active === "home" ? "page" : undefined}
        >
          Home
        </Link>

        <Link
          href="/news"
          className="home-btn"
          aria-current={active === "news" ? "page" : undefined}
        >
          News &amp; Announcements
        </Link>

        <Link
          href="/ai"
          className="home-btn"
          prefetch={false}
          onClick={onAssistantClick}
          aria-current={active === "ai" ? "page" : undefined}
        >
          AI Assistant
        </Link>

        <Link
          href="/policies"
          className="home-btn"
          prefetch={false}
          aria-current={
            active === "policies" ? "page" : undefined
          }
        >
          Policies
        </Link>
      </nav>

      <div className={styles.authActions}>
        {!authReady ? (
          <span
            className={styles.authPlaceholder}
            aria-hidden="true"
          />
        ) : user ? (
          <div className={accountStyles.account} ref={accountRef}>
            <button
              ref={accountButtonRef}
              type="button"
              className={accountStyles.trigger}
              aria-label={`Account options for ${displayName}`}
              aria-expanded={accountOpen}
              aria-controls={accountMenuId}
              onClick={() => {
                setAccountOpen((open) => !open);
                setSignOutError("");
              }}
            >
              <span className={accountStyles.avatar} aria-hidden="true">{initials}</span>
              <span className={accountStyles.name} title={displayName}>{displayName}</span>
              <svg className={accountStyles.chevron} viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="m6 9 6 6 6-6" />
              </svg>
            </button>
            <div id={accountMenuId} className={accountStyles.dropdown} hidden={!accountOpen}>
              <div className={accountStyles.identity}>
                <strong>{displayName}</strong>
                {user.email && <small>{user.email}</small>}
              </div>
              <nav aria-label="Account navigation" className={accountStyles.links}>
                <Link href="/profile" prefetch={false} className={accountStyles.item}
                  aria-current={active === "profile" ? "page" : undefined}
                  onClick={() => setAccountOpen(false)}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="12" cy="8" r="3"/><path d="M5 20v-2a7 7 0 0 1 14 0v2"/></svg>
                  My Profile
                </Link>
                <Link href="/settings" prefetch={false} className={accountStyles.item}
                  aria-current={active === "settings" ? "page" : undefined}
                  onClick={() => setAccountOpen(false)}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/><circle cx="8" cy="7" r="2" fill="white"/><circle cx="15" cy="12" r="2" fill="white"/><circle cx="10" cy="17" r="2" fill="white"/></svg>
                  Settings
                </Link>
              </nav>
              <button type="button" className={`${accountStyles.item} ${accountStyles.signOut}`} onClick={handleSignOut} disabled={isSigningOut}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M10 4H5v16h5M10 12h10m-4-4 4 4-4 4"/></svg>
                {isSigningOut ? "Signing out..." : "Sign Out"}
              </button>
              {signOutError && <p className={accountStyles.error} role="alert">{signOutError}</p>}
            </div>
          </div>
        ) : (
          <Link
            href="/login"
            className={styles.signInButton}
          >
            Sign In / Register
          </Link>
        )}
      </div>
    </header>
  );
}
