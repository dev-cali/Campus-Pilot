
"use client";

import { useState, type FormEvent } from "react";
import "./login.css";

export default function LoginPage() {
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const [loginEmail, setLoginEmail] = useState("");
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");

  // UI-only demo: no real authentication is implemented yet.
  const handleLogin = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    // Connect this to your backend authentication endpoint later.
    alert("Sign In UI ready. Authentication is not connected yet.");
  };

  const handleRegister = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    // Connect this to your backend registration endpoint later.
    alert("Registration UI ready. Authentication is not connected yet.");
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
          <label htmlFor="loginEmail">Username</label>
          <input
            type="text"
            id="loginEmail"
            className="input-field"
            placeholder="brianreynes@gmail.com"
            value={loginEmail}
            onChange={(event) => setLoginEmail(event.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="loginPassword">Password</label>
          <input
            type="password"
            id="loginPassword"
            className="input-field"
            placeholder="••••••••"
            required
          />
        </div>

        <div className="form-options">
          <label className="remember-me">
            <input type="checkbox" defaultChecked /> Remember me
          </label>
          <span>Forgot password?</span>
        </div>

        <button type="submit" className="submit-btn">
          Sign In to CampusPilot
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
            placeholder="brianreynes@gmail.com"
            value={regEmail}
            onChange={(event) => setRegEmail(event.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="regPass">Create Password</label>
          <input
            type="password"
            id="regPass"
            className="input-field"
            placeholder="At least 8 characters"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="regConfirmPass">Confirmed Password</label>
          <input
            type="password"
            id="regConfirmPass"
            className="input-field"
            placeholder="At least 8 characters"
            required
          />
        </div>

        <button type="submit" className="submit-btn">
          Create Account
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
    </div>
  );
}
