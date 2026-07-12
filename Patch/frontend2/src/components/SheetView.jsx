import React, { useEffect, useMemo, useRef, useState } from "react";
import { isBlackPitch, pitchName } from "../lib/noteMapping";

/*
 * SheetView – a real, playable grand staff.
 * -----------------------------------------
 * Time-proportional notation (like a scrolling score):
 *   – treble + bass staves with clefs, ledger lines, accidentals, stems
 *   – notes placed by real seconds on X and by diatonic step on Y
 *   – duration bars show how long each note is held
 *   – fixed playhead, the score scrolls under it, click to seek
 *   – hit / miss judgements from live practice are colored in place
 *
 * This intentionally renders time-proportional notation instead of
 * quantized bars: transcription timing is in seconds, and honest
 * spacing is more useful for practice than fake measure math.
 */

const PIXELS_PER_SECOND = 110;
const PLAYHEAD_RATIO = 0.24;
const STAFF_GAP = 9; // distance between staff lines
const HALF_STEP = STAFF_GAP / 2; // one diatonic step
const NOTE_RX = 5.4;
const NOTE_RY = 4.1;
const STEM_LENGTH = STAFF_GAP * 3.1;
const EDGE_PADDING_SECONDS = 1.5;

// Diatonic letter index (C=0 … B=6) for each pitch class, sharps spelling.
const LETTER_INDEX_BY_PITCH_CLASS = [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6];

const HAND_COLORS = {
  left: { head: "#1f7fd1", bar: "rgba(37, 140, 220, 0.28)", stem: "#17629f" },
  right: { head: "#c2418f", bar: "rgba(216, 82, 165, 0.26)", stem: "#8f2f6b" },
};

const JUDGEMENT_COLORS = {
  hit: { head: "#189a6c", bar: "rgba(38, 190, 130, 0.30)", stem: "#0f7550" },
  miss: { head: "#d24545", bar: "rgba(226, 90, 90, 0.26)", stem: "#a12f2f" },
};

function diatonicStep(pitch) {
  const midi = Number(pitch);
  const octave = Math.floor(midi / 12) - 1;
  const letterIndex = LETTER_INDEX_BY_PITCH_CLASS[((midi % 12) + 12) % 12];

  return octave * 7 + letterIndex;
}

const TREBLE_BOTTOM_STEP = diatonicStep(64); // E4 – bottom treble line
const BASS_BOTTOM_STEP = diatonicStep(43); // G2 – bottom bass line

function staffForNote(note) {
  if (note.hand === "left") return "bass";
  if (note.hand === "right") return "treble";

  return Number(note.pitch) >= 60 ? "treble" : "bass";
}

function noteY(note, trebleBottomY, bassBottomY) {
  const step = diatonicStep(note.pitch);

  if (staffForNote(note) === "treble") {
    return trebleBottomY - (step - TREBLE_BOTTOM_STEP) * HALF_STEP;
  }

  return bassBottomY - (step - BASS_BOTTOM_STEP) * HALF_STEP;
}

function ledgerSteps(note) {
  const step = diatonicStep(note.pitch);
  const onTreble = staffForNote(note) === "treble";

  const bottomStep = onTreble ? TREBLE_BOTTOM_STEP : BASS_BOTTOM_STEP;
  const topStep = bottomStep + 8; // 5 lines = 8 diatonic steps span

  const steps = [];

  if (step > topStep) {
    for (let s = topStep + 2; s <= step; s += 2) steps.push(s);
  } else if (step < bottomStep) {
    for (let s = bottomStep - 2; s >= step; s -= 2) steps.push(s);
  }

  return steps;
}

function StaffLines({ y, width }) {
  const lines = [];

  for (let index = 0; index < 5; index += 1) {
    const lineY = y - index * STAFF_GAP;
    lines.push(
      <line
        key={index}
        x1={0}
        x2={width}
        y1={lineY}
        y2={lineY}
        className="sheetview-staff-line"
      />
    );
  }

  return <g>{lines}</g>;
}

function SheetNote({ note, x, width, y, trebleBottomY, bassBottomY, judgement, isActive, showLabel }) {
  const hand =
    note.hand === "left" || note.hand === "right"
      ? note.hand
      : Number(note.pitch) < 60
        ? "left"
        : "right";

  const colors = JUDGEMENT_COLORS[judgement] || HAND_COLORS[hand];
  const onTreble = staffForNote(note) === "treble";
  const middleLineY = (onTreble ? trebleBottomY : bassBottomY) - 2 * STAFF_GAP;
  const stemUp = y > middleLineY;
  const accidental = isBlackPitch(note.pitch) ? "♯" : "";

  return (
    <g className={`sheetview-note ${isActive ? "is-active" : ""}`}>
      {/* Duration bar – how long the note is held */}
      <rect
        x={x}
        y={y - NOTE_RY}
        width={Math.max(width, 6)}
        height={NOTE_RY * 2}
        rx={NOTE_RY}
        fill={colors.bar}
      />

      {/* Ledger lines */}
      {ledgerSteps(note).map((step) => {
        const ledgerY = onTreble
          ? trebleBottomY - (step - TREBLE_BOTTOM_STEP) * HALF_STEP
          : bassBottomY - (step - BASS_BOTTOM_STEP) * HALF_STEP;

        return (
          <line
            key={step}
            x1={x - NOTE_RX - 3.4}
            x2={x + NOTE_RX + 3.4}
            y1={ledgerY}
            y2={ledgerY}
            className="sheetview-ledger-line"
          />
        );
      })}

      {/* Accidental */}
      {accidental && (
        <text x={x - NOTE_RX - 5.4} y={y + 3.6} className="sheetview-accidental">
          {accidental}
        </text>
      )}

      {/* Stem */}
      <line
        x1={stemUp ? x + NOTE_RX - 0.6 : x - NOTE_RX + 0.6}
        x2={stemUp ? x + NOTE_RX - 0.6 : x - NOTE_RX + 0.6}
        y1={y}
        y2={stemUp ? y - STEM_LENGTH : y + STEM_LENGTH}
        stroke={colors.stem}
        strokeWidth={1.4}
        strokeLinecap="round"
      />

      {/* Note head */}
      <ellipse
        cx={x}
        cy={y}
        rx={NOTE_RX}
        ry={NOTE_RY}
        fill={colors.head}
        transform={`rotate(-16 ${x} ${y})`}
        className="sheetview-note-head"
      />

      {isActive && (
        <ellipse
          cx={x}
          cy={y}
          rx={NOTE_RX + 3.4}
          ry={NOTE_RY + 3.4}
          className="sheetview-active-ring"
        />
      )}

      {showLabel && (
        <text x={x} y={y - NOTE_RY - 7} className="sheetview-note-label">
          {note.pitchName || pitchName(note.pitch)}
        </text>
      )}

      {judgement === "hit" && (
        <text x={x} y={y - NOTE_RY - 6} className="sheetview-judgement-mark hit">
          ✓
        </text>
      )}

      {judgement === "miss" && (
        <text x={x} y={y - NOTE_RY - 6} className="sheetview-judgement-mark miss">
          ✕
        </text>
      )}
    </g>
  );
}

export default function SheetView({
  notes = [],
  musicalTime = 0,
  durationSeconds = 0,
  onSeek,
  judgements = {},
  compact = false,
  noteDisplayMode = "letters",
}) {
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(720);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return undefined;

    const update = () => setContainerWidth(element.clientWidth || 720);
    update();

    const observer = new ResizeObserver(update);
    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  const height = compact ? 208 : 300;
  const trebleBottomY = compact ? 84 : 118;
  const bassBottomY = trebleBottomY + (compact ? 74 : 104);

  const playheadX = containerWidth * PLAYHEAD_RATIO;
  const scrollX = playheadX - musicalTime * PIXELS_PER_SECOND;

  const visibleFromTime =
    musicalTime - playheadX / PIXELS_PER_SECOND - EDGE_PADDING_SECONDS;
  const visibleToTime =
    musicalTime +
    (containerWidth - playheadX) / PIXELS_PER_SECOND +
    EDGE_PADDING_SECONDS;

  const visibleNotes = useMemo(() => {
    return notes.filter(
      (note) =>
        Number(note.end ?? note.start) >= visibleFromTime &&
        Number(note.start) <= visibleToTime
    );
  }, [notes, visibleFromTime, visibleToTime]);

  const gridSeconds = useMemo(() => {
    const from = Math.max(0, Math.floor(visibleFromTime));
    const to = Math.max(from, Math.ceil(Math.min(visibleToTime, durationSeconds + 2)));
    const seconds = [];

    for (let s = from; s <= to; s += 1) seconds.push(s);

    return seconds;
  }, [visibleFromTime, visibleToTime, durationSeconds]);

  function handleSeekClick(event) {
    if (!onSeek) return;

    const rect = containerRef.current.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const targetTime = musicalTime + (clickX - playheadX) / PIXELS_PER_SECOND;

    onSeek(Math.max(0, targetTime));
  }

  return (
    <div
      ref={containerRef}
      className={`sheetview-card ${compact ? "sheetview-card--compact" : ""}`}
      onClick={handleSeekClick}
      role="presentation"
    >
      <svg width="100%" height={height} className="sheetview-svg">
        {/* Fixed layer: staff lines across the full card */}
        <StaffLines y={trebleBottomY} width={containerWidth} />
        <StaffLines y={bassBottomY} width={containerWidth} />

        {/* Grand-staff brace hint */}
        <line
          x1={1.5}
          x2={1.5}
          y1={trebleBottomY - 4 * STAFF_GAP}
          y2={bassBottomY}
          className="sheetview-system-line"
        />

        {/* Scrolling layer: grid + notes */}
        <g transform={`translate(${scrollX}, 0)`}>
          {gridSeconds.map((second) => (
            <g key={second}>
              <line
                x1={second * PIXELS_PER_SECOND}
                x2={second * PIXELS_PER_SECOND}
                y1={trebleBottomY - 4 * STAFF_GAP - 8}
                y2={bassBottomY + 8}
                className={`sheetview-grid-line ${second % 5 === 0 ? "strong" : ""}`}
              />
              {second % 5 === 0 && (
                <text
                  x={second * PIXELS_PER_SECOND + 4}
                  y={bassBottomY + 22}
                  className="sheetview-grid-label"
                >
                  {second}s
                </text>
              )}
            </g>
          ))}

          {visibleNotes.map((note) => {
            const x = Number(note.start) * PIXELS_PER_SECOND;
            const width =
              Math.max(Number(note.end) - Number(note.start), 0.05) *
              PIXELS_PER_SECOND;
            const y = noteY(note, trebleBottomY, bassBottomY);
            const isActive =
              Number(note.start) <= musicalTime &&
              musicalTime <= Number(note.end);

            return (
              <SheetNote
                key={note.id ?? `${note.pitch}-${note.start}`}
                note={note}
                x={x}
                width={width}
                y={y}
                trebleBottomY={trebleBottomY}
                bassBottomY={bassBottomY}
                judgement={judgements[note.id]}
                isActive={isActive}
                showLabel={noteDisplayMode === "letters" && isActive}
              />
            );
          })}
        </g>

        {/* Fixed layer above notes: clefs + playhead */}
        <rect
          x={0}
          y={0}
          width={44}
          height={height}
          className="sheetview-clef-backdrop"
        />
        <text x={8} y={trebleBottomY - 2} className="sheetview-clef">
          𝄞
        </text>
        <text x={8} y={bassBottomY - 8} className="sheetview-clef sheetview-clef-bass">
          𝄢
        </text>
        <text x={40} y={trebleBottomY - 4 * STAFF_GAP - 12} className="sheetview-hand-tag right">
          R.H.
        </text>
        <text x={40} y={bassBottomY + 22} className="sheetview-hand-tag left">
          L.H.
        </text>

        <line
          x1={playheadX}
          x2={playheadX}
          y1={6}
          y2={height - 6}
          className="sheetview-playhead"
        />
        <circle cx={playheadX} cy={8} r={3.4} className="sheetview-playhead-cap" />
      </svg>
    </div>
  );
}
