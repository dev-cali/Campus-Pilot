
"use client";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { createClient } from "@/utils/supabase/client";
import "../home.css";

export default function LoginPage() {
  const router = useRouter();
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const [loginEmail, setLoginEmail] = useState("");
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirmPassword, setRegConfirmPassword] = useState("");

  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showRegConfirmPassword, setShowRegConfirmPassword] = useState(false);

  const [registerFeedback, setRegisterFeedback] = useState("");
  const [registerFeedbackType, setRegisterFeedbackType] = useState<"error" | "info" | "">("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);

  const [loginFeedback, setLoginFeedback] = useState("");

  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetFeedback, setResetFeedback] = useState("");
  // UI-only demo: no real authentication is implemented yet.

  const handleLogin = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (isLoggingIn) return;

    setLoginFeedback("");

    if (!loginEmail.trim() || !loginPassword) {
      setLoginFeedback("Please enter your email and password.");
      return;
    }

    setIsLoggingIn(true);

    try {
      const supabase = createClient();

      const { data, error } = await supabase.auth.signInWithPassword({
        email: loginEmail.trim(),
        password: loginPassword,
      });

      if (error || !data.session) {
        setLoginFeedback(
          "Unable to sign in. Please check your credentials."
        );
        return;
      }

      const next = new URLSearchParams(
        window.location.search
      ).get("next");

      const destination =
        next && (next === "/ai" || next.startsWith("/ai?"))
          ? next
          : "/";

      router.replace(destination);
      router.refresh();
    } catch {
      setLoginFeedback(
        "Unable to connect. Please try again later."
      );
    } finally {
      setIsLoggingIn(false);
    }
  };


  const handleRegister = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    if (isRegistering) return;

    setRegisterFeedback("");
    setRegisterFeedbackType("");

    if (!regName.trim() || !regEmail.trim()) {
      setRegisterFeedback("Please complete all required fields.");
      setRegisterFeedbackType("error");
      return;
    }

    if (regPassword.length < 8) {
      setRegisterFeedback(
        "Password must contain at least 8 characters."
      );
      setRegisterFeedbackType("error");
      return;
    }

    if (regPassword !== regConfirmPassword) {
      setRegisterFeedback("Passwords do not match.");
      setRegisterFeedbackType("error");
      return;
    }

    setIsRegistering(true);

    try {
      const supabase = createClient();

      const { data, error } = await supabase.auth.signUp({
        email: regEmail.trim(),
        password: regPassword,
        options: {
          emailRedirectTo:
            `${window.location.origin}/auth/callback`,
          data: {
            full_name: regName.trim(),
          },
        },
      });

      if (error) {
        setRegisterFeedback(
          "Unable to register. Please check your details and try again."
        );
        setRegisterFeedbackType("error");
        return;
      }

      if (data.session) {
        router.replace("/");
        router.refresh();
        return;
      }

      setRegisterFeedback(
        "Check your email for a confirmation link to complete registration."
      );
      setRegisterFeedbackType("info");

      setRegPassword("");
      setRegConfirmPassword("");
    } catch {
      setRegisterFeedback(
        "Unable to connect. Please try again later."
      );
      setRegisterFeedbackType("error");
    } finally {
      setIsRegistering(false);
    }
  };  

  const handleSso = (provider: "Google" | "Facebook") => {
    alert(`${provider} authentication is not connected yet.`);
  };

  return (
    <div className="login-wrapper">
      <div className="brand-head">
        <div className="logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="#ffffff">
            <path d="M12 2l2.4 7.4h7.6l-6.2 4.5 2.4 7.4-6.2-4.5-6.2 4.5 2.4-7.4-6.2-4.5h7.6z" />
          </svg>
        </div>

        <h1 className="brand-title">CampusPilot</h1>
        <p className="brand-sub">Student &amp; Faculty Portal Access</p>
      </div>

      <div className="auth-tabs">
        <button
          type="button"
          className={`tab-btn ${activeTab === "login" ? "active" : ""}`}
          id="loginTab"
          onClick={() => setActiveTab("login")}
        >
          Sign In
        </button>

        <button
          type="button"
          className={`tab-btn ${activeTab === "register" ? "active" : ""}`}
          id="registerTab"
          onClick={() => setActiveTab("register")}
        >
          Register
        </button>
      </div>

      {/* LOGIN FORM */}
      <form
        className={`auth-form ${activeTab !== "login" ? "hidden" : ""}`}
        id="loginForm"
        onSubmit={handleLogin}
      >
        <div className="form-group">
          <label htmlFor="loginEmail">Email Address</label>
          <input
            type="email"
            id="loginEmail"
            className="input-field"
            placeholder="Enter your email address"
            value={loginEmail}
            onChange={(event) => setLoginEmail(event.target.value)}
            autoComplete="email"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="loginPassword">Password</label>

          <div className="password-field">
            <input
              type={showLoginPassword ? "text" : "password"}
              id="loginPassword"
              className="input-field"
              placeholder="Enter your password"
              value={loginPassword}
              onChange={(event) => setLoginPassword(event.target.value)}
              autoComplete="current-password"
              required
            />

            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowLoginPassword((value) => !value)}
              aria-label={showLoginPassword ? "Hide password" : "Show password"}
              aria-pressed={showLoginPassword}
            >
              {showLoginPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        <div className="form-options">
          <label className="remember-me">
            <input type="checkbox" defaultChecked /> Remember me
          </label>
          <button
            type="button"
            className="forgot-password-btn"
            onClick={() => {
              setResetEmail(loginEmail);
              setResetFeedback("");
              setShowForgotPassword(true);
            }}
          >
            Forgot password?
          </button>
        </div>
        {loginFeedback && (
          <div className="auth-feedback info" role="status">
            {loginFeedback}
          </div>
        )}
        <button
          type="submit"
          className="submit-btn"
          disabled={isLoggingIn}
        >
          {isLoggingIn ? "Signing in..." : "Sign In to CampusPilot"}
        </button>
      </form>

      {/* REGISTER FORM */}
      <form
        className={`auth-form ${activeTab !== "register" ? "hidden" : ""}`}
        id="registerForm"
        onSubmit={handleRegister}
      >
        <div className="form-group">
          <label htmlFor="regName">Full Name</label>
          <input
            type="text"
            id="regName"
            className="input-field"
            placeholder="Juan Dela Cruz"
            value={regName}
            onChange={(event) => setRegName(event.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="regEmail">Email Address</label>
          <input
            type="email"
            id="regEmail"
            className="input-field"
            placeholder="juandelacruz@gmail.com"
            value={regEmail}
            onChange={(event) => setRegEmail(event.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="regPass">Create Password</label>

          <div className="password-field">
            <input
              type={showRegPassword ? "text" : "password"}
              id="regPass"
              className="input-field"
              placeholder="At least 8 characters"
              value={regPassword}
              onChange={(event) => {
                setRegPassword(event.target.value);
                setRegisterFeedback("");
              }}
              autoComplete="new-password"
              required
            />

            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowRegPassword((value) => !value)}
              aria-label={showRegPassword ? "Hide password" : "Show password"}
              aria-pressed={showRegPassword}
            >
              {showRegPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="regConfirmPass">Confirm Password</label>

          <div className="password-field">
            <input
              type={showRegConfirmPassword ? "text" : "password"}
              id="regConfirmPass"
              className="input-field"
              placeholder="Re-enter your password"
              value={regConfirmPassword}
              onChange={(event) => {
                setRegConfirmPassword(event.target.value);
                setRegisterFeedback("");
              }}
              autoComplete="new-password"
              required
            />

            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowRegConfirmPassword((value) => !value)}
              aria-label={
                showRegConfirmPassword
                  ? "Hide confirmation password"
                  : "Show confirmation password"
              }
              aria-pressed={showRegConfirmPassword}
            >
              {showRegConfirmPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>
        {registerFeedback && (
          <div
            className={`auth-feedback ${registerFeedbackType}`}
            role={registerFeedbackType === "error" ? "alert" : "status"}
          >
            {registerFeedback}
          </div>
        )}
        <button
          type="submit"
          className="submit-btn"
          disabled={isRegistering}
        >
          {isRegistering ? "Creating account..." : "Create Account"}
        </button>
      </form>

      <div className="divider">OR</div>

      {/* GOOGLE & FACEBOOK SSO BUTTONS */}
      <div className="sso-group">
        <button
          type="button"
          className="sso-btn"
          id="googleSsoBtn"
          onClick={() => handleSso("Google")}
        >
          <svg width="18" height="18" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>
          Continue with Google
        </button>

        <button
          type="button"
          className="sso-btn"
          id="fbSsoBtn"
          onClick={() => handleSso("Facebook")}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="#1877F2"
          >
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
          </svg>
          Continue with Facebook
        </button>
      </div>

      {showForgotPassword && (
        <div className="forgot-modal-backdrop">
          <section
            className="forgot-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="forgot-modal-title"
          >
            <button
              type="button"
              className="forgot-modal-close"
              onClick={() => setShowForgotPassword(false)}
              aria-label="Close forgot password"
            >
              ×
            </button>

            <div className="forgot-modal-icon">
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="11" width="18" height="11" rx="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>

            <h2 id="forgot-modal-title">Forgot Password?</h2>

            <p className="forgot-modal-description">
              Enter your registered email address
              and we&apos;ll help you recover your account.
            </p>

            <form
              className="forgot-form"
              onSubmit={(event) => {
                event.preventDefault();
                setResetFeedback(
                  "Password recovery is not connected yet. This feature will be available after authentication integration."
                );
              }}
            >
              <div className="form-group">
                <label htmlFor="resetEmail">Email Address</label>

                <input
                  type="email"
                  id="resetEmail"
                  className="input-field"
                  placeholder="student@example.com"
                  value={resetEmail}
                  onChange={(event) => {
                    setResetEmail(event.target.value);
                    setResetFeedback("");
                  }}
                  autoComplete="email"
                  required
                />
              </div>

              <button type="submit" className="submit-btn">
                Send Reset Link
              </button>
            </form>

            {resetFeedback && (
              <div className="auth-feedback info" role="status">
                {resetFeedback}
              </div>
            )}

            <button
              type="button"
              className="forgot-back-btn"
              onClick={() => {
                setShowForgotPassword(false);
                setResetFeedback("");
              }}
            >
              ← Back to Sign In
            </button>
          </section>
        </div>
      )}

      <div className="guest-navigation">
        <Link href="/">← Continue as guest</Link>
      </div>

    </div>
  );
}

