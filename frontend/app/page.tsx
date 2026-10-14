"use client";
import { useEffect, useState } from "react";

export default function Home() {
  const [departments, setDepartments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("https://campus-pilot-ziix.onrender.com/departments")
      .then((res) => res.json())
      .then((data) => {
        console.log("API Data:", data);
        setDepartments(data.departments || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Fetch error:", err);
        setLoading(false);
      });
  }, []);

  return (
    <main style={{ padding: "40px", fontFamily: "sans-serif", color: "#fff", background: "#111", minHeight: "100vh" }}>
      <h1>Campus Pilot - Sprint 1</h1>
      <p>Connecting frontend to FastAPI backend & database:</p>
      
      {loading ? (
        <p>Loading departments from database...</p>
      ) : (
        <ul style={{ marginTop: "20px" }}>
          {departments.length === 0 ? (
            <p>No departments found yet.</p>
          ) : (
            departments.map((dept) => (
              <li key={dept.id} style={{ marginBottom: "10px" }}>
                <strong>{dept.name}</strong>
              </li>
            ))
          )}
        </ul>
      )}
    </main>
  );
}