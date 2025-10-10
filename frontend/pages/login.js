import React, { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import api from "../api"; // <-- make sure frontend/api/index.js exists
import { LockKeyIcon } from "../assets/SVGIcon";
import styles from "../styles/auth/auth.module.css";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      console.log("🔹 Attempting login...");
      console.log("🔹 API Base URL =", api.defaults.baseURL);

      // ✅ Correct endpoint (Django backend via API)
      const res = await api.post("/auth/login/", { email, password });

      console.log("✅ Response:", res.data);

      if (res.data?.data === "Login successful") {
        alert("✅ Login successful!");
        router.push("/"); // redirect to home or dashboard
      } else {
        setError("Invalid credentials or unexpected response.");
      }
    } catch (err) {
      console.error("❌ Login error:", err.response?.data || err.message);
      setError("An unexpected error occurred during login.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.authRoot}>
      <div className={styles.loginContainer}>
        <div className={styles.formContainer}>
          <div className={styles.formHeader}>
            <LockKeyIcon />
            <h1>Login</h1>
          </div>

          {/* ✅ Login Form */}
          <form onSubmit={handleLogin}>
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              required
            />

            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />

            {error && <p style={{ color: "red" }}>{error}</p>}

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Logging in..." : "Log In"}
            </button>
          </form>

          <div className={styles.formFooter}>
            <Link href="#">Forgot credentials?</Link>
            <Link href="/register">Create an account</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
