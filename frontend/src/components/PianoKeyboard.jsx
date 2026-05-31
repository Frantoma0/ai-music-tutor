import React from "react";
import {
  confidenceLevel,
  handForPitch,
  pitchName,
  LOWEST_PITCH,
  HIGHEST_PITCH,
} from "../lib/noteMapping";

const BLACK_PITCH_CLASSES = new Set([1, 3, 6, 8, 10]);

function isBlackKey(pitch) {
  return BLACK_PITCH_CLASSES.has(pitch % 12);
}

function isInCorrectionMask(note) {
  return Boolean(note?.inCorrectionMask || note?.in_correction_mask);
}

function visualConfidenceLevel(note) {
  if (isInCorrectionMask(note)) {
    return "low";
  }

  if (note?.confidence === null || note?.confidence === undefined) {
    return "unknown";
  }

  return confidenceLevel(note.confidence);
}

function visualHandForNote(note) {
  if (note?.hand === "left" || note?.hand === "right") {
    return note.hand;
  }

  return handForPitch(note.pitch);
}

function activeNotesAtTime(notes, musicalTime) {
  return notes.filter((note) => {
    return note.start <= musicalTime && musicalTime <= note.end;
  });
}

function keyClassName(pitch, activeByPitch) {
  const activeNote = activeByPitch.get(pitch);
  const classes = ["piano-key", isBlackKey(pitch) ? "black-key" : "white-key"];

  if (activeNote) {
    classes.push("active");

    const hand = visualHandForNote(activeNote);
    const confidence = visualConfidenceLevel(activeNote);

    classes.push(hand === "left" ? "active-left" : "active-right");
    classes.push(`confidence-${confidence}`);
  }

  return classes.join(" ");
}

function shouldShowOctaveLabel(pitch) {
  return pitch % 12 === 0;
}

export function PianoKeyboard({ notes, musicalTime = 0 }) {
  const activeNotes = activeNotesAtTime(notes, musicalTime);
  const activeByPitch = new Map();

  for (const note of activeNotes) {
    activeByPitch.set(note.pitch, note);
  }

  const whitePitches = [];
  const blackPitches = [];

  for (let pitch = LOWEST_PITCH; pitch <= HIGHEST_PITCH; pitch += 1) {
    if (isBlackKey(pitch)) {
      blackPitches.push(pitch);
    } else {
      whitePitches.push(pitch);
    }
  }

  const pitchToWhiteIndex = new Map();
  let whiteIndex = 0;

  for (let pitch = LOWEST_PITCH; pitch <= HIGHEST_PITCH; pitch += 1) {
    if (!isBlackKey(pitch)) {
      pitchToWhiteIndex.set(pitch, whiteIndex);
      whiteIndex += 1;
    }
  }

  return (
    <div className="piano-keyboard" aria-label="Piano keyboard">
      <div className="white-key-row">
        {whitePitches.map((pitch) => {
          return (
            <div key={pitch} className={keyClassName(pitch, activeByPitch)}>
              {shouldShowOctaveLabel(pitch) && (
                <span className="key-label">
                  {pitchName(pitch)}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div className="black-key-row">
        {blackPitches.map((pitch) => {
          const previousWhite = pitch - 1;
          const whiteSlot = pitchToWhiteIndex.get(previousWhite);

          if (whiteSlot === undefined) {
            return null;
          }

          const leftPercent = ((whiteSlot + 0.72) / whitePitches.length) * 100;

          return (
            <div
              key={pitch}
              className={keyClassName(pitch, activeByPitch)}
              style={{ left: `${leftPercent}%` }}
            />
          );
        })}
      </div>
    </div>
  );
}
