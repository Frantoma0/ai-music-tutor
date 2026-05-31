export const LOWEST_PITCH = 36; // C2
export const HIGHEST_PITCH = 84; // C6
export const MIDDLE_C = 60; // C4

const NOTE_NAMES = [
  "C",
  "C#",
  "D",
  "D#",
  "E",
  "F",
  "F#",
  "G",
  "G#",
  "A",
  "A#",
  "B",
];

export function pitchToX(pitch, width) {
  const pitchRange = HIGHEST_PITCH - LOWEST_PITCH;
  const normalized = (pitch - LOWEST_PITCH) / pitchRange;
  return normalized * width;
}

export function pitchName(pitch) {
  return NOTE_NAMES[pitch % 12];
}

export function confidenceLevel(confidence) {
  if (confidence >= 0.8) return "high";
  if (confidence >= 0.6) return "medium";
  return "low";
}

export function handForPitch(pitch) {
  return pitch < MIDDLE_C ? "left" : "right";
}

export function noteDisplayContent(note, mode) {
  if (mode === "blank") return "";
  if (mode === "symbol") return "♪";
  return note.pitchName || pitchName(note.pitch);
}
