
"use client";

import { useEffect, useState } from "react";

type Department = {
  id?: number;
  name: string;
};

type DepartmentsResponse = {
  departments?: Department[];
};

export default function Home() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("https://campus-pilot-ziix.onrender.com/departments")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error: ${res.status}`);
        }
        return res.json() as Promise<DepartmentsResponse>;
      })
      .then((data) => {
        console.log("API Data:", data);
        setDepartments(
          Array.isArray(data.departments) ? data.departments : []
        );
      })
      .catch((err) => {
        console.error("Fetch error:", err);
        setDepartments([]);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <main
      style={{
        padding: "40px",
        fontFamily: "sans-serif",
        color: "#fff",
        background: "#111",
        minHeight: "100vh",
      }}
    >
      <h1>Campus Pilot - Sprint 1</h1>
      <p>Connecting frontend to FastAPI backend & database:</p>

      {loading ? (
        <p>Loading departments from database...</p>
      ) : departments.length === 0 ? (
        <p>No departments found yet.</p>
      ) : (
        <ul style={{ marginTop: "20px" }}>
          {departments.map((dept) => (
            <li key={dept.id ?? dept.name} style={{ marginBottom: "10px" }}>
              <strong>{dept.name}</strong>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
