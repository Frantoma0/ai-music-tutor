import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as Tone from "tone";
import "./styles.css";
import viewBlocksIcon from "./assets/view-blocks.png";
import viewSheetIcon from "./assets/view-sheet.png";
import viewMixIcon from "./assets/view-mix.png";
import HandsControl from "./components/HandsControl.jsx";
import { PianoKeyboard } from "./components/PianoKeyboard";
import { WaterfallCanvas } from "./components/WaterfallCanvas";
import SheetPreview from "./components/SheetPreview.jsx";
import { demoNotes } from "./lib/demoNotes";
import { DEFAULT_LESSON_JOB_ID, fetchLesson, mapLessonNotesToUiNotes } from "./api/lessonApi";

const FALLBACK_DURATION_SECONDS = 4.2;


function midiToToneNote(midiPitch) {
  return Tone.Frequency(midiPitch, "midi").toNote();
}

function App() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [tempo, setTempo] = useState(1);
  const [noteDisplayMode, setNoteDisplayMode] = useState("letters");
  const [keyboardLabelMode, setKeyboardLabelMode] = useState("c-only");
  const [viewMode, setViewMode] = useState("blocks");
  const [activeHand, setActiveHand] = React.useState("both");
  const [lesson, setLesson] = useState(null);
  const [lessonNotes, setLessonNotes] = useState(demoNotes);
  const [lessonLoadStatus, setLessonLoadStatus] = useState("loading");

  const lessonMeta = lesson?.meta ?? {};
  const lessonDurationSeconds =
    Number(lessonMeta.duration_s) ||
    Math.max(...lessonNotes.map((note) => Number(note.end ?? 0)), FALLBACK_DURATION_SECONDS);

  const lessonTitle = lessonMeta.title || "Morning Light";
  const lessonSubtitle = lesson
    ? `${lessonMeta.transcription_method || "Demo lesson"} · ${lessonMeta.detected_key || "Unknown key"} · ${lessonMeta.time_signature || "4/4"}`
    : "Demo lesson · C Major · 4/4";

  const musicalTime = currentTime * tempo;

  const visibleLessonNotes = React.useMemo(() => {
    return lessonNotes.filter((note) => {
      if (activeHand === "both") return true;
      return note.hand === activeHand;
    });
  }, [lessonNotes, activeHand]);

  const progressPercent = Math.max(
    0,
    Math.min(100, Math.round((musicalTime / Math.max(lessonDurationSeconds, 0.01)) * 100))
  );

  const reviewNoteCount = lessonNotes.filter(
    (note) => note.inCorrectionMask || note.in_correction_mask
  ).length;

  const unknownConfidenceCount = lessonNotes.filter(
    (note) => note.confidence === null || note.confidence === undefined
  ).length;

  const lastFrameRef = useRef(null);
  const synthRef = useRef(null);
  const triggeredNotesRef = useRef(new Set());

  // useEffect(() => {
  //   const reverb = new Tone.Reverb({
  //   decay: 3.2,
  //   wet: 0.26,
  // }).toDestination();

  // const compressor = new Tone.Compressor({
  //   threshold: -20,
  //   ratio: 2.6,
  //   attack: 0.035,
  //   release: 0.32,
  // }).connect(reverb);

  // const gain = new Tone.Gain(0.68).connect(compressor);

  // synthRef.current = new Tone.PolySynth(Tone.Synth, {
  //   maxPolyphony: 64,
  //   oscillator: {
  //     type: "triangle8",
  //   },
  //   envelope: {
  //     attack: 0.015,
  //     decay: 0.28,
  //     sustain: 0.28,
  //     release: 1.6,
  //   },
  // }).connect(gain);

  //   return () => {
  //     synthRef.current?.dispose();
  //   };
  // }, []);

  useEffect(() => {
    const reverb = new Tone.Reverb({
      decay: 3.6,
      wet: 0.18,
    }).toDestination();

    const compressor = new Tone.Compressor({
      threshold: -20,
      ratio: 2.4,
      attack: 0.035,
      release: 0.32,
    }).connect(reverb);

    const gain = new Tone.Gain(0.82).connect(compressor);

    const fallbackSynth = new Tone.PolySynth(Tone.Synth, {
      maxPolyphony: 64,
      oscillator: {
        type: "triangle8",
      },
      envelope: {
        attack: 0.015,
        decay: 0.28,
        sustain: 0.28,
        release: 1.6,
      },
    }).connect(gain);

    const pianoSampler = new Tone.Sampler({
      urls: {
        A0: "A0.mp3",
        C1: "C1.mp3",
        "D#1": "Ds1.mp3",
        "F#1": "Fs1.mp3",
        A1: "A1.mp3",
        C2: "C2.mp3",
        "D#2": "Ds2.mp3",
        "F#2": "Fs2.mp3",
        A2: "A2.mp3",
        C3: "C3.mp3",
        "D#3": "Ds3.mp3",
        "F#3": "Fs3.mp3",
        A3: "A3.mp3",
        C4: "C4.mp3",
        "D#4": "Ds4.mp3",
        "F#4": "Fs4.mp3",
        A4: "A4.mp3",
        C5: "C5.mp3",
        "D#5": "Ds5.mp3",
        "F#5": "Fs5.mp3",
        A5: "A5.mp3",
        C6: "C6.mp3",
        "D#6": "Ds6.mp3",
        "F#6": "Fs6.mp3",
        A6: "A6.mp3",
        C7: "C7.mp3",
        "D#7": "Ds7.mp3",
        "F#7": "Fs7.mp3",
        A7: "A7.mp3",
        C8: "C8.mp3",
      },
      baseUrl: "/samples/piano/",
      release: 1.4,
      onload: () => {
        console.log("Acoustic piano samples loaded");
        synthRef.current = pianoSampler;
        fallbackSynth.dispose();
      },
    }).connect(gain);

    synthRef.current = fallbackSynth;

    return () => {
      pianoSampler.dispose();
      fallbackSynth.dispose();
      gain.dispose();
      compressor.dispose();
      reverb.dispose();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadLesson() {
      try {
        const loadedLesson = await fetchLesson(DEFAULT_LESSON_JOB_ID);

        if (cancelled) return;

        setLesson(loadedLesson);
        setLessonNotes(mapLessonNotesToUiNotes(loadedLesson.notes));
        setLessonLoadStatus("loaded");
      } catch (error) {
        if (cancelled) return;

        console.warn("Using demoNotes fallback because lesson fetch failed:", error);
        setLesson(null);
        setLessonNotes(demoNotes);
        setLessonLoadStatus("fallback");
      }
    }

    loadLesson();

    return () => {
      cancelled = true;
    };
  }, []);

  function triggerNotesBetween(previousMusicalTime, nextMusicalTime) {
    const synth = synthRef.current;

    if (!synth) return;

    for (const note of visibleLessonNotes) {
      const alreadyTriggered = triggeredNotesRef.current.has(note.id);
      const isInWindow =
        note.start >= previousMusicalTime && note.start < nextMusicalTime;

      if (!alreadyTriggered && isInWindow) {
          const duration = Math.max((note.end - note.start) / tempo, 0.08);

          const normalizedVelocity = Math.min(
            0.95,
            Math.max(0.22, (note.velocity ?? 72) / 127)
          );

          const confidenceWeight =
            note.confidence === null || note.confidence === undefined
              ? 0.85
              : Math.min(1, Math.max(0.45, note.confidence));

          const expressiveVelocity = Math.pow(
            normalizedVelocity * confidenceWeight,
            0.82
          );

          synth.triggerAttackRelease(
            midiToToneNote(note.pitch),
            duration,
            undefined,
            expressiveVelocity
          );

          triggeredNotesRef.current.add(note.id);
        }
    }
  }

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

          const previousMusicalTime = time * tempo;
          const nextMusicalTime = next * tempo;

          triggerNotesBetween(previousMusicalTime, nextMusicalTime);

          if (next >= lessonDurationSeconds / tempo) {
            setIsPlaying(false);
            triggeredNotesRef.current.clear();
            return 0;
          }

          return next;
        });
      }

      frameId = requestAnimationFrame(tick);
    }

    frameId = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(frameId);
  }, [isPlaying, tempo, visibleLessonNotes, lessonDurationSeconds]);

  async function togglePlayback() {
    await Tone.start();

    lastFrameRef.current = null;

    if (!isPlaying && currentTime === 0) {
      triggeredNotesRef.current.clear();
    }

    setIsPlaying((value) => !value);
  }

  function resetPlayback() {
    lastFrameRef.current = null;
    triggeredNotesRef.current.clear();
    setIsPlaying(false);
    setCurrentTime(0);
  }

  function handleTempoChange(event) {
    setTempo(Number(event.target.value));
    lastFrameRef.current = null;
  }

  const stageStateClass = isPlaying ? "is-playing" : "";
return (
    <main className="app-shell">
      <section className="lesson-layout">
        <header className="top-player-bar">
          <div className="top-left">
            <button className="back-button" aria-label="Back">
              <svg
                className="back-arrow-icon"
                viewBox="0 0 24 24"
                aria-hidden="true"
                focusable="false"
              >
                <path
                  d="M14.8 6.5 9.3 12l5.5 5.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>

            <div>
              <p className="eyebrow">AI Music Tutor</p>
              <h1 className="lesson-title">{lessonTitle}</h1>
              <p className="lesson-subtitle">{lessonSubtitle}</p>
              {lessonLoadStatus === "fallback" && (
                <p className="lesson-load-status">Using local fallback notes</p>
              )}

              <div className="lesson-ai-summary" aria-label="AI lesson summary">
                <span>Review notes: {reviewNoteCount}</span>
                <span>Unknown confidence: {unknownConfidenceCount}</span>
              </div>
            </div>
          </div>

          <div className="top-center">
            <div className="view-switch view-switch-hero" role="tablist" aria-label="View mode">
              <button
                type="button"
                className={viewMode === "blocks" ? "active" : ""}
                onClick={() => setViewMode("blocks")}
                aria-pressed={viewMode === "blocks"}
              >
                <img src={viewBlocksIcon} alt="" className="view-mode-image" aria-hidden="true" />
                <span className="view-mode-label">Blocks</span>
              </button>

              <button
                type="button"
                className={viewMode === "sheet" ? "active" : ""}
                onClick={() => setViewMode("sheet")}
                aria-pressed={viewMode === "sheet"}
              >
                <img src={viewSheetIcon} alt="" className="view-mode-image" aria-hidden="true" />
                <span className="view-mode-label">Sheet</span>
              </button>

              <button
                type="button"
                className={viewMode === "mix" ? "active" : ""}
                onClick={() => setViewMode("mix")}
                aria-pressed={viewMode === "mix"}
              >
                <img src={viewMixIcon} alt="" className="view-mode-image" aria-hidden="true" />
                <span className="view-mode-label">Mix</span>
              </button>
            </div>
          </div>

          <div className="top-right">
            <div className="progress-pill">
              <div className="progress-meta">
                <span>Lesson Progress</span>
                <strong>{progressPercent}%</strong>
              </div>

              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
              </div>
            </div>

            <div className="status-pill">
              {isPlaying ? "Playing" : "Paused"} · {Math.round(tempo * 100)}%
            </div>
          </div>
        </header>

        <section className={`lesson-stage ${stageStateClass} view-mode-${viewMode}`}>
          {viewMode === "blocks" && (
            <>
              <div className="waterfall-frame">
                <WaterfallCanvas
                  notes={visibleLessonNotes}
                  currentTime={currentTime}
                  musicalTime={musicalTime}
                  tempo={tempo}
                  noteDisplayMode={noteDisplayMode}
                />
              </div>

              <PianoKeyboard
                notes={visibleLessonNotes}
                currentTime={currentTime}
                musicalTime={musicalTime}
                tempo={tempo}
                labelMode={keyboardLabelMode}
              />
            </>
          )}

          {viewMode === "sheet" && (
            <SheetPreview />
          )}

          {viewMode === "mix" && (
            <>
              <SheetPreview compact />

              <div className="waterfall-frame mix-waterfall-frame">
                <WaterfallCanvas
                  notes={visibleLessonNotes}
                  currentTime={currentTime}
                  musicalTime={musicalTime}
                  tempo={tempo}
                  noteDisplayMode={noteDisplayMode}
                />
              </div>

              <PianoKeyboard
                notes={visibleLessonNotes}
                currentTime={currentTime}
                musicalTime={musicalTime}
                tempo={tempo}
                labelMode={keyboardLabelMode}
              />
            </>
          )}
        </section>

        <footer className="controls-card">
          <div className="transport-group">
            <button className="primary-control" onClick={togglePlayback}>
              {isPlaying ? "Pause" : "Play"}
            </button>

            <button className="secondary-control" onClick={resetPlayback}>
              Reset
            </button>
          </div>

          <label className="tempo-control">
            <span>Tempo</span>
            <input
              type="range"
              min="0.25"
              max="1.5"
              step="0.05"
              value={tempo}
              onChange={handleTempoChange}
            />
            <strong>{Math.round(tempo * 100)}%</strong>
          </label>

        <div className="mini-control-pill" aria-label="Note display mode">
            <span className="mini-mode-label">Display</span>

            <div className="mini-mode-switch">
              <button
                type="button"
                className={noteDisplayMode === "blank" ? "active" : ""}
                onClick={() => setNoteDisplayMode("blank")}
              >
                Blank
              </button>

              <button
                type="button"
                className={noteDisplayMode === "letters" ? "active" : ""}
                onClick={() => setNoteDisplayMode("letters")}
              >
                A–G
              </button>

              <button
                type="button"
                className={noteDisplayMode === "symbol" ? "active" : ""}
                onClick={() => setNoteDisplayMode("symbol")}
              >
                ♪
              </button>
            </div>
          </div>

          <div className="mini-control-pill" aria-label="Keyboard label mode">
            <span className="mini-mode-label">Keys</span>

            <div className="mini-mode-switch">
              <button
                type="button"
                className={keyboardLabelMode === "off" ? "active" : ""}
                onClick={() => setKeyboardLabelMode("off")}
              >
                Off
              </button>

              <button
                type="button"
                className={keyboardLabelMode === "c-only" ? "active" : ""}
                onClick={() => setKeyboardLabelMode("c-only")}
              >
                C
              </button>

              <button
                type="button"
                className={keyboardLabelMode === "all" ? "active" : ""}
                onClick={() => setKeyboardLabelMode("all")}
              >
                All
              </button>
            </div>
          </div>

          <HandsControl
            activeHand={activeHand}
            onChange={setActiveHand}
          />

          <div className="confidence-legend">
          <span className="confidence-block-indicator" aria-hidden="true" />
          <span>Low confidence</span>
        </div>

          <div className="time-readout">
            {currentTime.toFixed(2)}s
          </div>
        </footer>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
