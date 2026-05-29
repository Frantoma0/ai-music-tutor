export const LOWEST_PITCH = 36; // C2
export const HIGHEST_PITCH = 84; // C6
export const MIDDLE_C = 60; // C4

export function pitchToX(pitch, width) {
  const pitchRange = HIGHEST_PITCH - LOWEST_PITCH;
  const normalized = (pitch - LOWEST_PITCH) / pitchRange;
  return normalized * width;
}

export function confidenceClass(confidence) {
  if (confidence >= 0.8) return "high";
  if (confidence >= 0.6) return "medium";
  return "low";
}

export function handForPitch(pitch) {
  return pitch < MIDDLE_C ? "left" : "right";
}
