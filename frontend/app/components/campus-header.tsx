
"use client";

import Link from "next/link";
import { useEffect, useState, type MouseEventHandler } from "react";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/utils/supabase/client";
import styles from "./campus-header.module.css";

type CampusHeaderProps = {
  active: "home" | "ai" | "policies";
  onPoliciesClick?: MouseEventHandler<HTMLAnchorElement>;
  onAssistantClick?: MouseEventHandler<HTMLAnchorElement>;
};

export default function CampusHeader({
  active,
  onPoliciesClick,
  onAssistantClick,
}: CampusHeaderProps) {
  const router = useRouter();

  // Initialize Supabase once.
  const [supabase] = useState(() => createClient());

  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);

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

    try {
      const { error } = await supabase.auth.signOut();

      if (error) {
        setIsSigningOut(false);
        return;
      }

      router.replace("/");
      router.refresh();
    } catch {
      setIsSigningOut(false);
    }
  };

  const fullName = user?.user_metadata?.full_name;

  const displayName =
    typeof fullName === "string" && fullName.trim()
      ? fullName
      : user?.email || "My Account";

  return (
    <header className={`top-header ${styles.header}`}>
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

        <Link href="/#announcements" className="home-btn">
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
          href="/ai?category=Policies"
          className="home-btn"
          prefetch={false}
          onClick={onPoliciesClick}
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
          <>
            <span
              className={styles.accountName}
              title={displayName}
            >
              {displayName}
            </span>

            <button
              type="button"
              className={styles.signInButton}
              onClick={handleSignOut}
              disabled={isSigningOut}
            >
              {isSigningOut ? "Signing out..." : "Sign Out"}
            </button>
          </>
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
