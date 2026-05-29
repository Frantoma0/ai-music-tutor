import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

import { WaterfallCanvas } from "./components/WaterfallCanvas";
import { demoNotes } from "./lib/demoNotes";

const DEMO_DURATION_SECONDS = 4.2;

function App() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [tempo, setTempo] = useState(1);
  const lastFrameRef = useRef(null);

  useEffect(() => {
    let frameId;

    function tick(timestamp) {
      if (lastFrameRef.current === null) {
        lastFrameRef.current = timestamp;
      }

      const deltaSeconds = (timestamp - lastFrameRef.current) / 1000;
      lastFrameRef.current = timestamp;

      if (isPlaying) {
        setCurrentTime((time) => {
          const next = time + deltaSeconds;

          if (next >= DEMO_DURATION_SECONDS / tempo) {
            setIsPlaying(false);
            return 0;
          }

          return next;
        });
      }

      frameId = requestAnimationFrame(tick);
    }

    frameId = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(frameId);
  }, [isPlaying, tempo]);

  function togglePlayback() {
    lastFrameRef.current = null;
    setIsPlaying((value) => !value);
  }

  function resetPlayback() {
    lastFrameRef.current = null;
    setIsPlaying(false);
    setCurrentTime(0);
  }

  return (
    <main className="app-shell">
      <section className="lesson-layout">
        <div className="lesson-header">
          <div>
            <p className="eyebrow">AI Music Tutor</p>
            <h1>Waterfall Lesson Prototype</h1>
            <p>
              Първи синхронен spike: падащи ноти, playback clock и tempo control.
            </p>
          </div>

          <div className="status-pill">
            {isPlaying ? "Playing" : "Paused"} · {tempo.toFixed(2)}x
          </div>
        </div>

        <div className="waterfall-frame">
          <WaterfallCanvas
            notes={demoNotes}
            currentTime={currentTime}
            tempo={tempo}
          />
        </div>

        <div className="controls-card">
          <button onClick={togglePlayback}>
            {isPlaying ? "Pause" : "Play"}
          </button>

          <button className="secondary" onClick={resetPlayback}>
            Reset
          </button>

          <label className="tempo-control">
            <span>Tempo</span>
            <input
              type="range"
              min="0.25"
              max="1.5"
              step="0.05"
              value={tempo}
              onChange={(event) => {
                setTempo(Number(event.target.value));
                lastFrameRef.current = null;
              }}
            />
            <strong>{Math.round(tempo * 100)}%</strong>
          </label>

          <div className="time-readout">
            Time: {currentTime.toFixed(2)}s
          </div>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
