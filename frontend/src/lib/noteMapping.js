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

const BLACK_PITCH_CLASSES = new Set([1, 3, 6, 8, 10]);

export function pitchClass(pitch) {
  const value = Number(pitch) % 12;
  return value < 0 ? value + 12 : value;
}

export function pitchOctave(pitch) {
  return Math.floor(Number(pitch) / 12) - 1;
}

export function isBlackPitch(pitch) {
  return BLACK_PITCH_CLASSES.has(pitchClass(pitch));
}

export function buildPitchRange() {
  const pitches = [];

  for (let pitch = LOWEST_PITCH; pitch <= HIGHEST_PITCH; pitch += 1) {
    pitches.push(pitch);
  }

  return pitches;
}

export function getKeyboardPitchLayout() {
  const allPitches = buildPitchRange();

  const whitePitches = allPitches.filter((pitch) => !isBlackPitch(pitch));
  const blackPitches = allPitches.filter((pitch) => isBlackPitch(pitch));

  return {
    allPitches,
    whitePitches,
    blackPitches,
  };
}

function isBlackPitchForLayout(pitch) {
  return BLACK_PITCH_CLASSES.has(Number(pitch) % 12);
}

function buildWhitePitchesForLayout() {
  const whitePitches = [];

  for (let pitch = LOWEST_PITCH; pitch <= HIGHEST_PITCH; pitch += 1) {
    if (!isBlackPitchForLayout(pitch)) {
      whitePitches.push(pitch);
    }
  }

  return whitePitches;
}

export function pitchToX(pitch, width) {
  const numericPitch = Number(pitch);
  const whitePitches = buildWhitePitchesForLayout();
  const whiteKeyWidth = width / whitePitches.length;

  if (isBlackPitchForLayout(numericPitch)) {
    const previousWhite = numericPitch - 1;
    const whiteSlot = whitePitches.indexOf(previousWhite);

    if (whiteSlot >= 0) {
      return (whiteSlot + 1) * whiteKeyWidth;
    }
  }

  const whiteSlot = whitePitches.indexOf(numericPitch);

  if (whiteSlot >= 0) {
    return (whiteSlot + 0.5) * whiteKeyWidth;
  }

  return 0;
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
