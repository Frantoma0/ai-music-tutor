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

export function buildPitchRange(
  lowestPitch = LOWEST_PITCH,
  highestPitch = HIGHEST_PITCH
) {
  const pitches = [];

  for (let pitch = lowestPitch; pitch <= highestPitch; pitch += 1) {
    pitches.push(pitch);
  }

  return pitches;
}

export function getKeyboardWhitePitches(
  lowestPitch = LOWEST_PITCH,
  highestPitch = HIGHEST_PITCH
) {
  return buildPitchRange(lowestPitch, highestPitch).filter(
    (pitch) => !isBlackPitch(pitch)
  );
}

export function getKeyboardBlackPitches(
  lowestPitch = LOWEST_PITCH,
  highestPitch = HIGHEST_PITCH
) {
  return buildPitchRange(lowestPitch, highestPitch).filter((pitch) =>
    isBlackPitch(pitch)
  );
}

export function getKeyboardPitchLayout(
  lowestPitch = LOWEST_PITCH,
  highestPitch = HIGHEST_PITCH
) {
  const allPitches = buildPitchRange(lowestPitch, highestPitch);
  const whitePitches = getKeyboardWhitePitches(lowestPitch, highestPitch);
  const blackPitches = getKeyboardBlackPitches(lowestPitch, highestPitch);

  return {
    allPitches,
    whitePitches,
    blackPitches,
  };
}

export function getPitchCenterRatio(
  pitch,
  lowestPitch = LOWEST_PITCH,
  highestPitch = HIGHEST_PITCH
) {
  const numericPitch = Number(pitch);
  const whitePitches = getKeyboardWhitePitches(lowestPitch, highestPitch);

  if (!whitePitches.length) {
    return 0;
  }

  if (isBlackPitch(numericPitch)) {
    const previousWhitePitch = numericPitch - 1;
    const previousWhiteIndex = whitePitches.indexOf(previousWhitePitch);

    if (previousWhiteIndex >= 0) {
      return (previousWhiteIndex + 1) / whitePitches.length;
    }
  }

  const whiteIndex = whitePitches.indexOf(numericPitch);

  if (whiteIndex >= 0) {
    return (whiteIndex + 0.5) / whitePitches.length;
  }

  const fallbackRatio =
    (numericPitch - lowestPitch) / Math.max(1, highestPitch - lowestPitch);

  return Math.min(1, Math.max(0, fallbackRatio));
}

export function pitchToX(pitch, width) {
  return getPitchCenterRatio(pitch) * width;
}

export function pitchName(pitch) {
    return NOTE_NAMES[pitchClass(pitch)].replace("#", "♯");
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