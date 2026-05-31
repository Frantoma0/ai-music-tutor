import React from "react";

const trebleNotes = [
  { x: 10, y: 66, label: "♪", active: true },
  { x: 17, y: 58, label: "♪" },
  { x: 24, y: 72, label: "♪" },
  { x: 33, y: 61, label: "♪" },
  { x: 42, y: 70, label: "♪" },
  { x: 51, y: 57, label: "♪" },
  { x: 60, y: 69, label: "♪" },
  { x: 70, y: 59, label: "♪" },
  { x: 79, y: 67, label: "♪" },
  { x: 88, y: 58, label: "♪" },
];

const bassNotes = [
  { x: 32, y: 74 },
  { x: 62, y: 71 },
  { x: 82, y: 73 },
];

export default function SheetPreview({ compact = false }) {
  return (
    <div className={`sheet-preview ${compact ? "sheet-preview--compact" : ""}`}>
      <div className="sheet-card">
        <div className="sheet-playhead" aria-hidden="true" />

        <div className="sheet-header-row">
          <span className="sheet-measure">1</span>
          <span className="sheet-chord sheet-chord-left">A</span>
          <span className="sheet-chord sheet-chord-right">C#m/G#</span>
        </div>

        <div className="sheet-system">
          <div className="sheet-clef treble">𝄞</div>
          <div className="sheet-time-signature">
            <span>4</span>
            <span>4</span>
          </div>

          <div className="sheet-staff sheet-staff-treble">
            {trebleNotes.map((note, index) => (
              <span
                key={index}
                className={`sheet-note ${note.active ? "is-active" : ""}`}
                style={{ left: `${note.x}%`, top: `${note.y}%` }}
              >
                {note.label}
              </span>
            ))}

            <span className="sheet-fingering" style={{ left: "64%" }}>1</span>
            <span className="sheet-fingering" style={{ left: "70%" }}>3</span>
            <span className="sheet-fingering" style={{ left: "76%" }}>5</span>
          </div>
        </div>

        <div className="sheet-system sheet-system-bass">
          <div className="sheet-clef bass">𝄢</div>
          <div className="sheet-time-signature">
            <span>4</span>
            <span>4</span>
          </div>

          <div className="sheet-staff sheet-staff-bass">
            {bassNotes.map((note, index) => (
              <span
                key={index}
                className="sheet-bass-note"
                style={{ left: `${note.x}%`, top: `${note.y}%` }}
              />
            ))}

            <span className="sheet-slur" aria-hidden="true" />
          </div>
        </div>

        <div className="sheet-barline barline-1" />
        <div className="sheet-barline barline-2" />
        <div className="sheet-barline barline-3" />

        <div className="sheet-caption">
          Concept preview · Sheet rendering planned for a future version
        </div>
      </div>
    </div>
  );
}
