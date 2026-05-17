import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return (
    <main className="app-shell">
      <section className="card">
        <p className="eyebrow">AI Music Tutor</p>
        <h1>Explainable Piano Transcription Correction</h1>
        <p>
          Frontend is running. Backend health will be connected after Docker
          Compose is up.
        </p>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
