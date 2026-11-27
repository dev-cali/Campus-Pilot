"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { createClient } from "@/utils/supabase/client";
import styles from "./reset-password.module.css";

type PageStatus = "checking" | "ready" | "invalid" | "success";

export default function ResetPasswordPage() {
  const [status, setStatus] = useState<PageStatus>("checking");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const verifyRecoverySession = async () => {
      try {
        const supabase = createClient();
        const { data, error } = await supabase.auth.getUser();

        if (!isMounted) return;

        if (error || !data.user) {
          setStatus("invalid");
          return;
        }

        setStatus("ready");
      } catch {
        if (isMounted) {
          setStatus("invalid");
        }
      }
    };

    void verifyRecoverySession();

    return () => {
      isMounted = false;
    };
  }, []);

  const handlePasswordUpdate = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    if (isSubmitting) return;

    setFeedback("");

    if (password.length < 8) {
      setFeedback("Your password must contain at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setFeedback("Your passwords do not match.");
      return;
    }

    setIsSubmitting(true);

    try {
      const supabase = createClient();

      const { error } = await supabase.auth.updateUser({
        password,
      });

      if (error) {
        setFeedback(
          "Unable to update your password. Your recovery link may have expired. Please request a new one."
        );
        return;
      }

      // End the recovery session so the user can sign in with the new password.
      await supabase.auth.signOut();

      setPassword("");
      setConfirmPassword("");
      setStatus("success");
    } catch {
      setFeedback("Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="reset-title">
        <Link href="/" className={styles.brand} aria-label="CampusPilot home">
          <span className={styles.logo} aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
              <path d="M12 2l2.4 7.4h7.6l-6.2 4.5 2.4 7.4-6.2-4.5-6.2 4.5 2.4-7.4-6.2-4.5h7.6z" />
            </svg>
          </span>
          <span>CampusPilot</span>
        </Link>

        {status === "checking" && (
          <div className={styles.messageState} role="status">
            <span className={styles.spinner} aria-hidden="true" />
            <h1 id="reset-title">Verifying your recovery link</h1>
            <p>Please wait while we verify your password reset session.</p>
          </div>
        )}

        {status === "invalid" && (
          <div className={styles.messageState} role="alert">
            <div className={styles.statusIcon} aria-hidden="true">
              !
            </div>
            <h1 id="reset-title">Recovery link unavailable</h1>
            <p>
              This password reset link is invalid or has expired. Return to
              the login page and request a new password reset link.
            </p>
            <Link href="/login" className={styles.primaryLink}>
              Back to Login
            </Link>
          </div>
        )}

        {status === "ready" && (
          <>
            <div className={styles.heading}>
              <div className={styles.statusIcon} aria-hidden="true">
                <svg
                  width="25"
                  height="25"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="3" y="11" width="18" height="11" rx="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </div>
              <h1 id="reset-title">Create a New Password</h1>
              <p>Choose a new password for your CampusPilot account.</p>
            </div>

            <form className={styles.form} onSubmit={handlePasswordUpdate}>
              <div className={styles.formGroup}>
                <label htmlFor="newPassword">New Password</label>
                <div className={styles.passwordField}>
                  <input
                    id="newPassword"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(event) => {
                      setPassword(event.target.value);
                      setFeedback("");
                    }}
                    placeholder="At least 8 characters"
                    autoComplete="new-password"
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    className={styles.toggleButton}
                    onClick={() => setShowPassword((value) => !value)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-pressed={showPassword}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="confirmPassword">Confirm New Password</label>
                <div className={styles.passwordField}>
                  <input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(event) => {
                      setConfirmPassword(event.target.value);
                      setFeedback("");
                    }}
                    placeholder="Re-enter your new password"
                    autoComplete="new-password"
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    className={styles.toggleButton}
                    onClick={() =>
                      setShowConfirmPassword((value) => !value)
                    }
                    aria-label={
                      showConfirmPassword ? "Hide password" : "Show password"
                    }
                    aria-pressed={showConfirmPassword}
                  >
                    {showConfirmPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              {feedback && (
                <div className={styles.feedback} role="alert">
                  {feedback}
                </div>
              )}

              <button
                type="submit"
                className={styles.submitButton}
                disabled={isSubmitting}
              >
                {isSubmitting ? "Updating Password..." : "Update Password"}
              </button>
            </form>

            <p className={styles.passwordHint}>
              Your password must contain at least 8 characters.
            </p>
          </>
        )}

        {status === "success" && (
          <div className={styles.messageState} role="status">
            <div className={`${styles.statusIcon} ${styles.successIcon}`}>
              ✓
            </div>
            <h1 id="reset-title">Password Updated</h1>
            <p>
              Your password has been changed successfully. You can now sign
              in using your new password.
            </p>
            <Link href="/login" className={styles.primaryLink}>
              Return to Sign In
            </Link>
          </div>
        )}
      </section>

      <p className={styles.footer}>
        © {new Date().getFullYear()} CampusPilot. Student &amp; Faculty Portal.
      </p>
    </main>
  );
}
