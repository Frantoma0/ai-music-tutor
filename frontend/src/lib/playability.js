import { handForPitch } from "./noteMapping";
import { buildPracticeNotes } from "./practiceNotes";

/*
 * Playability filter
 * ------------------
 * Basic Pitch transcriptions contain artifacts that make lessons
 * unrealistic to play and unpleasant to hear:
 *
 *   1. "Dust"    – ultra short, low confidence blips.
 *   2. "Ghosts"  – harmonic duplicates (+1 / +2 octaves, +octave+fifth)
 *                  created by overtones of a real note.
 *   3. Smeared chords – notes of one chord starting 10–40 ms apart.
 *   4. Impossible polyphony – more simultaneous notes than two hands
 *                  can physically press.
 *
 * This module cleans all four in deterministic, explainable passes.
 * Every removed note is counted so the UI can report what was hidden.
 */

export const PLAYABILITY_DEFAULTS = {
  // Pass 1 – dust
  dustMaxDurationSeconds: 0.085,
  dustMaxConfidence: 0.55,
  dustMaxVelocity: 18,

  // Pass 2 – adaptive confidence floor (quantile-based)
  confidenceQuantile: 0.15,
  confidenceFloorMin: 0.32,
  confidenceFloorMax: 0.5,

  // Pass 3 – onset clustering (chord grouping)
  onsetClusterWindowSeconds: 0.035,

  // Pass 4 – harmonic ghosts (same onset + sustained across time)
  ghostIntervals: [12, 19, 24, 28],
  ghostConfidenceSlack: 0.05,
  ghostVelocitySlack: 10,
  ghostMaxDurationRatio: 1.2,
  sustainedGhostTailSeconds: 0.14,
  sustainedGhostConfidenceSlack: 0.12,
  sustainedGhostVelocitySlack: 16,
  sustainedGhostWeakConfidence: 0.45,
  melodyProtectConfidence: 0.78,

  // Key conformity (only active when keyPitchClasses is provided)
  keyPitchClasses: null,
  keyMinConfidence: 0.7,
  keyMinDurationSeconds: 0.35,
  keyUnreliableOutRatio: 0.25,

  // Pass 5 – polyphony cap
  maxVoicesPerHand: 3,
  maxVoicesTotal: 6,

  // Pass 6 – density cap (per hand, per second)
  maxNotesPerSecondRight: 9,
  maxNotesPerSecondLeft: 7,

  // Pass 7 – smoothing
  minPlaybackDurationSeconds: 0.09,
  mergeGapSeconds: 0.06,
};

/*
 * Beginner preset: an arrangement a first-year learner can actually
 * follow – melody plus simple bass, no dense ornaments, no weak notes.
 */
export const BEGINNER_OVERRIDES = {
  dustMaxDurationSeconds: 0.11,
  dustMaxConfidence: 0.62,
  confidenceQuantile: 0.3,
  confidenceFloorMin: 0.42,
  confidenceFloorMax: 0.62,
  ghostConfidenceSlack: 0.12,
  ghostVelocitySlack: 18,
  sustainedGhostTailSeconds: 0.22,
  sustainedGhostConfidenceSlack: 0.18,
  sustainedGhostVelocitySlack: 24,
  sustainedGhostWeakConfidence: 0.5,
  keyMinConfidence: 0.8,
  maxVoicesPerHand: 2,
  maxVoicesTotal: 3,
  maxNotesPerSecondRight: 5,
  maxNotesPerSecondLeft: 3,
  minPlaybackDurationSeconds: 0.13,
  mergeGapSeconds: 0.1,
};

export const SIMPLIFY_LEVELS = {
  practice: PLAYABILITY_DEFAULTS,
  beginner: { ...PLAYABILITY_DEFAULTS, ...BEGINNER_OVERRIDES },
};

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function noteConfidence(note) {
  if (note.confidence === null || note.confidence === undefined) {
    // Unknown confidence should not be punished as if it were zero.
    return 0.7;
  }

  return toNumber(note.confidence, 0.7);
}

function noteVelocity(note) {
  return toNumber(note.velocity, 72);
}

function noteHand(note) {
  if (note.hand === "left" || note.hand === "right") {
    return note.hand;
  }

  return handForPitch(toNumber(note.pitch));
}

function noteStrength(note) {
  return noteConfidence(note) * 0.6 + (noteVelocity(note) / 127) * 0.4;
}

/*
 * Skyline protection: the top right-hand voice (melody) and the bottom
 * left-hand voice (bass) in every short window are structurally important.
 * They are exempt from dust / confidence / density removal so aggressive
 * cleaning can never eat the tune itself.
 */
const SKYLINE_BUCKET_SECONDS = 0.5;
const GHOST_INTERVALS_FOR_SKYLINE = [12, 19, 24];

/*
 * A note is "ghost-like" when a same-hand fundamental one or two octaves
 * (or an octave plus a fifth) below is still sounding at its onset with
 * comparable strength. Such a note can never represent the melody, so it
 * must not win skyline protection: otherwise every overtone artifact
 * above the tune would shield itself from the ghost filters.
 */
function isGhostLikeNote(note, sortedNotes) {
  for (const lower of sortedNotes) {
    if (lower.start >= note.start) break;
    if (lower.end <= note.start + 0.02) continue;
    if (noteHand(lower) !== noteHand(note)) continue;

    const interval = note.pitch - lower.pitch;

    if (!GHOST_INTERVALS_FOR_SKYLINE.includes(interval)) continue;

    if (noteConfidence(lower) >= noteConfidence(note) - 0.05) {
      return true;
    }
  }

  return false;
}

function computeProtectedSkyline(notes, bucketSeconds = SKYLINE_BUCKET_SECONDS) {
  const sorted = [...notes].sort((a, b) => a.start - b.start);
  const buckets = new Map();

  const isBetterVoice = (candidate, current) =>
    noteHand(candidate) === "right"
      ? candidate.pitch > current.pitch
      : candidate.pitch < current.pitch;

  for (const note of sorted) {
    if (isGhostLikeNote(note, sorted)) continue;

    // A note this weak and this short cannot plausibly carry the melody
    // or the bass, so it does not earn protection from the cleanup passes.
    const implausiblyWeak =
      noteConfidence(note) < 0.45 && note.duration < 0.14;

    if (implausiblyWeak) continue;

    const key = `${noteHand(note)}:${Math.floor(note.start / bucketSeconds)}`;
    const current = buckets.get(key);

    if (!current || isBetterVoice(note, current)) {
      buckets.set(key, note);
    }
  }

  const protectedIds = new Set();

  for (const note of buckets.values()) {
    if (note.id !== undefined && note.id !== null) {
      protectedIds.add(note.id);
    }
  }

  return protectedIds;
}

function normalizeNotes(notes) {
  return notes
    .map((note) => {
      const start = toNumber(note.start, 0);
      const rawEnd = toNumber(note.end, start);
      const end = Math.max(rawEnd, start);

      return {
        ...note,
        pitch: toNumber(note.pitch),
        start,
        end,
        duration: Math.max(end - start, 0),
      };
    })
    .sort((first, second) => {
      const startDiff = first.start - second.start;
      if (startDiff !== 0) return startDiff;
      return first.pitch - second.pitch;
    });
}

/* ---------------------------------------------------------------- */
/* Pass 1 – dust                                                     */
/* ---------------------------------------------------------------- */

function isDustNote(note, options) {
  const shortAndUnsure =
    note.duration < options.dustMaxDurationSeconds &&
    noteConfidence(note) < options.dustMaxConfidence;

  const shortAndSilent =
    note.duration < options.minPlaybackDurationSeconds &&
    noteVelocity(note) <= options.dustMaxVelocity;

  return shortAndUnsure || shortAndSilent;
}

/* ---------------------------------------------------------------- */
/* Pass 2 – onset clustering                                         */
/* ---------------------------------------------------------------- */

function clusterByOnset(notes, windowSeconds) {
  const clusters = [];
  let current = null;

  for (const note of notes) {
    if (!current || note.start - current.anchorStart > windowSeconds) {
      current = { anchorStart: note.start, notes: [note] };
      clusters.push(current);
    } else {
      current.notes.push(note);
    }
  }

  return clusters;
}

function medianStart(notes) {
  const starts = notes.map((note) => note.start).sort((a, b) => a - b);
  const middle = Math.floor(starts.length / 2);

  if (starts.length % 2 === 1) {
    return starts[middle];
  }

  return (starts[middle - 1] + starts[middle]) / 2;
}

/* ---------------------------------------------------------------- */
/* Pass 3 – unison duplicates and harmonic ghosts inside a cluster   */
/* ---------------------------------------------------------------- */

function dedupeUnisons(clusterNotes) {
  const byPitch = new Map();

  for (const note of clusterNotes) {
    const existing = byPitch.get(note.pitch);

    if (!existing) {
      byPitch.set(note.pitch, note);
      continue;
    }

    const keep = noteStrength(note) > noteStrength(existing) ? note : existing;
    const drop = keep === note ? existing : note;

    byPitch.set(note.pitch, {
      ...keep,
      end: Math.max(keep.end, drop.end),
      duration: Math.max(keep.end, drop.end) - keep.start,
    });
  }

  return Array.from(byPitch.values()).sort((a, b) => a.pitch - b.pitch);
}

function markHarmonicGhosts(clusterNotes, options) {
  const ghosts = new Set();
  const topPitch = clusterNotes[clusterNotes.length - 1]?.pitch;

  for (let lowIndex = 0; lowIndex < clusterNotes.length; lowIndex += 1) {
    const low = clusterNotes[lowIndex];

    if (ghosts.has(low)) continue;

    for (let highIndex = lowIndex + 1; highIndex < clusterNotes.length; highIndex += 1) {
      const high = clusterNotes[highIndex];

      if (ghosts.has(high)) continue;

      const interval = high.pitch - low.pitch;

      if (!options.ghostIntervals.includes(interval)) continue;

      // Melody protection: a confident top voice is never treated
      // as an overtone, even one octave above the note below it.
      const isProtectedMelody =
        high.pitch === topPitch &&
        noteConfidence(high) >= options.melodyProtectConfidence;

      if (isProtectedMelody) continue;

      const weakerConfidence =
        noteConfidence(high) <= noteConfidence(low) + options.ghostConfidenceSlack;
      const weakerVelocity =
        noteVelocity(high) <= noteVelocity(low) + options.ghostVelocitySlack;
      const notLonger =
        high.duration <= low.duration * options.ghostMaxDurationRatio;

      if (weakerConfidence && weakerVelocity && notLonger) {
        ghosts.add(high);
      }
    }
  }

  return clusterNotes.filter((note) => !ghosts.has(note));
}

/* ---------------------------------------------------------------- */
/* Pass 4 – polyphony cap                                            */
/* ---------------------------------------------------------------- */

function capHandVoices(handNotes, hand, maxVoices) {
  if (handNotes.length <= maxVoices) {
    return handNotes;
  }

  const sortedByPitch = [...handNotes].sort((a, b) => a.pitch - b.pitch);

  // The musically essential voice: melody on the right hand,
  // bass on the left hand. It is always kept.
  const essential =
    hand === "right"
      ? sortedByPitch[sortedByPitch.length - 1]
      : sortedByPitch[0];

  const rest = sortedByPitch
    .filter((note) => note !== essential)
    .sort((a, b) => noteStrength(b) - noteStrength(a));

  return [essential, ...rest.slice(0, Math.max(maxVoices - 1, 0))];
}

function capClusterPolyphony(clusterNotes, options) {
  const left = [];
  const right = [];

  for (const note of clusterNotes) {
    (noteHand(note) === "left" ? left : right).push(note);
  }

  let kept = [
    ...capHandVoices(left, "left", options.maxVoicesPerHand),
    ...capHandVoices(right, "right", options.maxVoicesPerHand),
  ];

  if (kept.length > options.maxVoicesTotal) {
    const sortedByPitch = [...kept].sort((a, b) => a.pitch - b.pitch);
    const bass = sortedByPitch[0];
    const melody = sortedByPitch[sortedByPitch.length - 1];
    const middle = sortedByPitch
      .slice(1, -1)
      .sort((a, b) => noteStrength(b) - noteStrength(a));

    kept = [bass, melody, ...middle].slice(0, options.maxVoicesTotal);
  }

  return kept.sort((a, b) => a.pitch - b.pitch);
}

/* ---------------------------------------------------------------- */
/* Pass 5 – minimum audible duration                                 */
/* ---------------------------------------------------------------- */

function enforceMinimumDurations(notes, minDuration) {
  const byPitch = new Map();

  for (const note of notes) {
    if (!byPitch.has(note.pitch)) {
      byPitch.set(note.pitch, []);
    }

    byPitch.get(note.pitch).push(note);
  }

  const adjusted = [];

  for (const pitchNotes of byPitch.values()) {
    pitchNotes.sort((a, b) => a.start - b.start);

    for (let index = 0; index < pitchNotes.length; index += 1) {
      const note = pitchNotes[index];
      const next = pitchNotes[index + 1];

      let end = note.end;

      if (end - note.start < minDuration) {
        end = note.start + minDuration;
      }

      if (next) {
        end = Math.min(end, next.start - 0.02);
      }

      end = Math.max(end, note.end, note.start);

      adjusted.push({
        ...note,
        end,
        duration: end - note.start,
      });
    }
  }

  return adjusted.sort((a, b) => a.start - b.start || a.pitch - b.pitch);
}

/* ---------------------------------------------------------------- */
/* Pass 2 – adaptive confidence floor                                 */
/* ---------------------------------------------------------------- */

function applyConfidenceFloor(notes, options, protectedIds = new Set()) {
  const confidences = notes
    .map((note) =>
      note.confidence === null || note.confidence === undefined
        ? null
        : toNumber(note.confidence)
    )
    .filter((value) => value !== null)
    .sort((a, b) => a - b);

  // Only meaningful when most notes carry a confidence value.
  if (confidences.length < notes.length * 0.6 || confidences.length < 8) {
    return notes;
  }

  const index = Math.floor(confidences.length * options.confidenceQuantile);
  const quantileValue = confidences[Math.min(index, confidences.length - 1)];
  const floor = Math.min(
    options.confidenceFloorMax,
    Math.max(options.confidenceFloorMin, quantileValue)
  );

  return notes.filter((note) => {
    if (protectedIds.has(note.id)) {
      return true;
    }

    if (note.confidence === null || note.confidence === undefined) {
      return true;
    }

    if (toNumber(note.confidence) >= floor) {
      return true;
    }

    // A long, loud note is real even when the model was unsure.
    return note.duration > 0.4 && noteVelocity(note) >= 64;
  });
}

/* ---------------------------------------------------------------- */
/* Key signature parsing and conformity                              */
/* ---------------------------------------------------------------- */

const NOTE_NAME_TO_PITCH_CLASS = {
  C: 0, "C#": 1, DB: 1, D: 2, "D#": 3, EB: 3, E: 4, F: 5, "F#": 6,
  GB: 6, G: 7, "G#": 8, AB: 8, A: 9, "A#": 10, BB: 10, B: 11,
};

const MAJOR_SCALE_INTERVALS = [0, 2, 4, 5, 7, 9, 11];
// Natural minor plus the raised seventh, which is ubiquitous in practice.
const MINOR_SCALE_INTERVALS = [0, 2, 3, 5, 7, 8, 10, 11];

export function parseKeySignature(keyName) {
  if (typeof keyName !== "string" || !keyName.trim()) {
    return null;
  }

  const normalized = keyName
    .trim()
    .replace(/\u266f/g, "#")
    .replace(/\u266d/g, "b")
    .toUpperCase();

  const match = normalized.match(/^([A-G][#B]?)\s*(MAJOR|MINOR|MAJ|MIN|M)?/);

  if (!match) {
    return null;
  }

  const root = NOTE_NAME_TO_PITCH_CLASS[match[1]];

  if (root === undefined) {
    return null;
  }

  const isMinor = /MIN|MINOR/.test(match[2] || "") || match[2] === "M";
  const intervals = isMinor ? MINOR_SCALE_INTERVALS : MAJOR_SCALE_INTERVALS;

  return new Set(intervals.map((interval) => (root + interval) % 12));
}

function applyKeyConformity(notes, options, protectedIds) {
  const keyPitchClasses = options.keyPitchClasses;

  if (!(keyPitchClasses instanceof Set) || keyPitchClasses.size === 0) {
    return notes;
  }

  const outOfKey = notes.filter(
    (note) => !keyPitchClasses.has(((note.pitch % 12) + 12) % 12)
  );

  // A high out-of-key ratio means the detected key is unreliable or the
  // piece modulates heavily; in that case only clearly weak notes go.
  const unreliableKey =
    outOfKey.length / Math.max(notes.length, 1) > options.keyUnreliableOutRatio;

  return notes.filter((note) => {
    if (protectedIds.has(note.id)) {
      return true;
    }

    if (keyPitchClasses.has(((note.pitch % 12) + 12) % 12)) {
      return true;
    }

    const confidence = noteConfidence(note);
    const hvsLabel = note.hvsLabel ?? note.hvs_label;
    const backendFlagsChromatic =
      typeof hvsLabel === "string" && hvsLabel.startsWith("chromatic");

    if (unreliableKey) {
      return !(confidence < 0.5 && note.duration < 0.12);
    }

    if (backendFlagsChromatic && confidence < 0.75) {
      return false;
    }

    return (
      confidence >= options.keyMinConfidence ||
      note.duration >= options.keyMinDurationSeconds
    );
  });
}

/* ---------------------------------------------------------------- */
/* Pass 4b – sustained harmonic ghosts across time                   */
/*                                                                    */
/* The classic Basic Pitch artifact on real recordings: while a real  */
/* note is still sounding, its overtone (+1 or +2 octaves, or an      */
/* octave + fifth) pops in as a separate weak note some 50–200 ms     */
/* later. Same-onset clustering cannot catch these; a sweep over the  */
/* currently sounding notes can.                                      */
/* ---------------------------------------------------------------- */

function removeSustainedHarmonicGhosts(notes, options, protectedIds = new Set()) {
  const sorted = [...notes].sort((a, b) => a.start - b.start || a.pitch - b.pitch);
  const kept = [];
  const removed = new Set();

  for (const note of sorted) {
    if (protectedIds.has(note.id)) {
      kept.push(note);
      continue;
    }

    // Fundamentals currently sounding under this note's onset.
    let isGhost = false;

    for (const lower of kept) {
      if (removed.has(lower)) continue;
      if (lower.end <= note.start + 0.02) continue;
      if (lower.start >= note.start - 0.015) continue; // same-onset pass handles that

      const interval = note.pitch - lower.pitch;
      if (!options.ghostIntervals.includes(interval)) continue;

      const insideTail =
        note.end <= lower.end + options.sustainedGhostTailSeconds;

      if (!insideTail) continue;

      const clearlyWeak =
        noteConfidence(note) < options.sustainedGhostWeakConfidence;
      const notStronger =
        noteConfidence(note) <=
          noteConfidence(lower) + options.sustainedGhostConfidenceSlack &&
        noteVelocity(note) <=
          noteVelocity(lower) + options.sustainedGhostVelocitySlack;

      const isProtectedMelody =
        noteConfidence(note) >= options.melodyProtectConfidence &&
        noteVelocity(note) >= noteVelocity(lower);

      if ((clearlyWeak || notStronger) && !isProtectedMelody) {
        isGhost = true;
        break;
      }
    }

    if (!isGhost) {
      kept.push(note);
    }
  }

  return kept;
}

/* ---------------------------------------------------------------- */
/* Pass 6 – density cap: keep the strongest notes per hand & second   */
/* ---------------------------------------------------------------- */

function applyDensityCap(notes, options) {
  const buckets = new Map(); // `${hand}:${secondBucket}` -> notes[]

  for (const note of notes) {
    const key = `${noteHand(note)}:${Math.floor(note.start / 0.5)}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(note);
  }

  const dropped = new Set();
  const skyline = computeProtectedSkyline(notes);

  for (const [key, bucketNotes] of buckets) {
    const hand = key.startsWith("left") ? "left" : "right";
    const perSecond =
      hand === "left"
        ? options.maxNotesPerSecondLeft
        : options.maxNotesPerSecondRight;
    const limit = Math.max(1, Math.ceil(perSecond / 2)); // bucket = 0.5 s

    if (bucketNotes.length <= limit) continue;

    const sortedByPitch = [...bucketNotes].sort((a, b) => a.pitch - b.pitch);
    const essential =
      hand === "right"
        ? sortedByPitch[sortedByPitch.length - 1]
        : sortedByPitch[0];

    const rest = bucketNotes
      .filter((note) => note !== essential)
      .sort((a, b) => noteStrength(b) - noteStrength(a));

    for (const note of rest.slice(Math.max(limit - 1, 0))) {
      if (!skyline.has(note.id)) {
        dropped.add(note);
      }
    }
  }

  return notes.filter((note) => !dropped.has(note));
}

/* ---------------------------------------------------------------- */
/* Fit to the learner's own piano                                     */
/*                                                                    */
/* 1. Shift the whole piece by the octave that puts the most notes    */
/*    inside [lowestPitch, highestPitch].                             */
/* 2. Fold the remaining outliers octave-by-octave into the range     */
/*    (possible whenever the keyboard spans at least one octave).     */
/* ---------------------------------------------------------------- */

export function fitNotesToRange(notes = [], lowestPitch = 36, highestPitch = 84) {
  const low = Math.min(lowestPitch, highestPitch);
  const high = Math.max(lowestPitch, highestPitch);

  if (!notes.length || high - low < 12) {
    return notes;
  }

  let bestShift = 0;
  let bestScore = -1;

  for (let octaves = -3; octaves <= 3; octaves += 1) {
    const shift = octaves * 12;
    let inside = 0;

    for (const note of notes) {
      const pitch = toNumber(note.pitch) + shift;
      if (pitch >= low && pitch <= high) inside += 1;
    }

    const score = inside - Math.abs(octaves) * 0.25; // prefer smaller shifts on ties

    if (score > bestScore) {
      bestScore = score;
      bestShift = shift;
    }
  }

  return notes.map((note) => {
    const sourcePitch = toNumber(note.pitch);
    let pitch = sourcePitch + bestShift;

    while (pitch < low) pitch += 12;
    while (pitch > high) pitch -= 12;

    if (pitch === sourcePitch) {
      return note;
    }

    const mapped = {
      ...note,
      pitch,
      sourcePitch,
      rangeFitted: true,
    };

    // Old names would show the pre-shift pitch; recompute lazily in the UI.
    delete mapped.pitchName;
    delete mapped.pitch_name;

    return mapped;
  });
}

/* ---------------------------------------------------------------- */
/* Public API                                                        */
/* ---------------------------------------------------------------- */

export function buildPlayableNotes(
  notes = [],
  levelOrOptions = "practice",
  extraOptions = {}
) {
  const base =
    typeof levelOrOptions === "string"
      ? SIMPLIFY_LEVELS[levelOrOptions] || PLAYABILITY_DEFAULTS
      : { ...PLAYABILITY_DEFAULTS, ...levelOrOptions };
  const options = { ...base, ...extraOptions };

  const normalized = normalizeNotes(notes);
  const protectedIds = computeProtectedSkyline(normalized);

  let working = normalized.filter(
    (note) => protectedIds.has(note.id) || !isDustNote(note, options)
  );
  working = applyConfidenceFloor(working, options, protectedIds);
  working = applyKeyConformity(working, options, protectedIds);
  working = removeSustainedHarmonicGhosts(working, options, protectedIds);

  const clusters = clusterByOnset(working, options.onsetClusterWindowSeconds);
  const clusteredResult = [];

  for (const cluster of clusters) {
    let clusterNotes = dedupeUnisons(cluster.notes);
    clusterNotes = markHarmonicGhosts(clusterNotes, options);
    clusterNotes = capClusterPolyphony(clusterNotes, options);

    // Align surviving chord members to one onset so the chord
    // sounds together instead of smeared.
    const snappedStart = medianStart(clusterNotes);

    for (const note of clusterNotes) {
      const end = Math.max(note.end, snappedStart);

      clusteredResult.push({
        ...note,
        start: snappedStart,
        end,
        duration: end - snappedStart,
      });
    }
  }

  const densityCapped = applyDensityCap(clusteredResult, options);

  const merged = buildPracticeNotes(densityCapped, {
    maxGapSeconds: options.mergeGapSeconds,
  });

  return enforceMinimumDurations(merged, options.minPlaybackDurationSeconds);
}

export function getPlayabilityStats(rawNotes = [], playableNotes = []) {
  const rawCount = rawNotes.length;
  const playableCount = playableNotes.length;

  return {
    rawCount,
    playableCount,
    removedCount: Math.max(rawCount - playableCount, 0),
  };
}
