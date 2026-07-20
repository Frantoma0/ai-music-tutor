import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPlayableNotes,
  fitNotesToRange,
  getPlayabilityStats,
  parseKeySignature,
} from "../src/lib/playability.js";

function note(overrides = {}) {
  return {
    id: overrides.id ?? `n-${Math.random().toString(36).slice(2, 8)}`,
    pitch: 60,
    start: 0,
    end: 0.5,
    velocity: 80,
    confidence: 0.9,
    hand: "right",
    ...overrides,
  };
}

test("dust notes are removed while normal notes survive", () => {
  const notes = [
    note({ id: "keep", start: 1.0, end: 1.5 }),
    note({ id: "dust", start: 1.0, end: 1.05, confidence: 0.3, velocity: 20 }),
  ];

  const out = buildPlayableNotes(notes, "practice");
  const ids = out.map((n) => n.id);

  assert.ok(ids.includes("keep"));
  assert.ok(!ids.includes("dust"));
});

test("same-onset harmonic ghosts are removed and chords are aligned", () => {
  const notes = [
    note({ id: "root", pitch: 60, start: 1.0, end: 1.6, confidence: 0.9 }),
    note({ id: "third", pitch: 64, start: 1.02, end: 1.58, confidence: 0.85 }),
    note({ id: "ghost", pitch: 72, start: 1.01, end: 1.3, confidence: 0.5, velocity: 40 }),
  ];

  const out = buildPlayableNotes(notes, "practice");
  const ids = out.map((n) => n.id);

  assert.ok(!ids.includes("ghost"));

  const starts = new Set(out.map((n) => n.start.toFixed(3)));
  assert.equal(starts.size, 1, "chord members share one onset after snapping");
});

test("sustained octave ghosts inside a sounding note are removed", () => {
  const notes = [
    note({ id: "fundamental", pitch: 48, hand: "left", start: 1.0, end: 2.2, confidence: 0.9 }),
    note({
      id: "ghost",
      pitch: 60,
      hand: "left",
      start: 1.12,
      end: 1.5,
      confidence: 0.4,
      velocity: 34,
    }),
    note({ id: "melody", pitch: 72, hand: "right", start: 1.3, end: 2.0, confidence: 0.92 }),
  ];

  const out = buildPlayableNotes(notes, "practice");
  const ids = out.map((n) => n.id);

  assert.ok(ids.includes("fundamental"));
  assert.ok(ids.includes("melody"), "strong melody above is protected");
  assert.ok(!ids.includes("ghost"));
});

test("weak but structurally essential melody survives beginner cleaning", () => {
  const notes = [
    note({ id: "bass", pitch: 40, hand: "left", start: 0, end: 1.2 }),
    note({ id: "melody", pitch: 76, start: 0.05, end: 0.35, velocity: 38, confidence: 0.35 }),
    note({ id: "fill-a", pitch: 64, start: 0.06, end: 0.2, velocity: 36, confidence: 0.3 }),
    note({ id: "fill-b", pitch: 67, start: 0.07, end: 0.2, velocity: 35, confidence: 0.31 }),
  ];

  const out = buildPlayableNotes(notes, "beginner");
  const ids = out.map((n) => n.id);

  assert.ok(ids.includes("melody"));
  assert.ok(ids.includes("bass"));
});

test("polyphony cap keeps the bass of a dense left-hand cluster", () => {
  const cluster = [36, 40, 43, 45, 47].map((pitch, index) =>
    note({
      id: `l-${pitch}`,
      pitch,
      hand: "left",
      start: 1.0 + index * 0.005,
      end: 1.5,
      confidence: pitch === 36 ? 0.9 : 0.5,
      velocity: pitch === 36 ? 80 : 40,
    })
  );

  const out = buildPlayableNotes(cluster, "practice");

  assert.ok(out.some((n) => n.pitch === 36), "bass voice is always kept");
  assert.ok(out.length <= 3, "left hand is capped to three voices");
});

test("repeated notes with micro gaps merge into one", () => {
  const notes = [
    note({ id: "r1", pitch: 62, start: 3.0, end: 3.2 }),
    note({ id: "r2", pitch: 62, start: 3.24, end: 3.5 }),
  ];

  const out = buildPlayableNotes(notes, "practice");

  assert.equal(out.filter((n) => n.pitch === 62).length, 1);
});

test("key conformity drops weak out-of-key notes and keeps strong ones", () => {
  const dMajor = parseKeySignature("D major");

  const notes = [
    note({ id: "in-key", pitch: 62, start: 1.0, end: 1.5 }),
    note({ id: "weak-out", pitch: 63, start: 2.0, end: 2.1, confidence: 0.4 }),
    note({ id: "strong-out", pitch: 63, start: 3.0, end: 3.6, confidence: 0.9 }),
    ...Array.from({ length: 12 }, (_, i) =>
      note({ id: `pad-${i}`, pitch: 62 + (i % 2) * 5, start: 4 + i, end: 4.6 + i })
    ),
  ];

  const out = buildPlayableNotes(notes, "practice", { keyPitchClasses: dMajor });
  const ids = out.map((n) => n.id);

  assert.ok(ids.includes("in-key"));
  assert.ok(!ids.includes("weak-out"));
  assert.ok(ids.includes("strong-out"), "confident chromatic notes are kept");
});

test("parseKeySignature understands common spellings", () => {
  assert.deepEqual([...parseKeySignature("D major")].sort((a, b) => a - b), [1, 2, 4, 6, 7, 9, 11]);
  assert.ok(parseKeySignature("A minor").has(11), "minor includes the raised seventh");
  assert.ok(parseKeySignature("F# major").has(6));
  assert.ok(parseKeySignature("Bb major").has(10));
  assert.equal(parseKeySignature(""), null);
  assert.equal(parseKeySignature(null), null);
});

test("fitNotesToRange shifts globally and folds outliers into the range", () => {
  const notes = [
    note({ id: "a", pitch: 84, start: 0, end: 0.5 }),
    note({ id: "b", pitch: 96, start: 0.6, end: 1.0 }),
    note({ id: "c", pitch: 89, start: 1.1, end: 1.5 }),
    note({ id: "d", pitch: 48, hand: "left", start: 0, end: 1.0 }),
  ];

  const out = fitNotesToRange(notes, 41, 84);

  assert.ok(out.every((n) => n.pitch >= 41 && n.pitch <= 84));
  assert.ok(out.some((n) => n.rangeFitted), "folded notes are flagged");
});

test("fitNotesToRange leaves notes alone when the range is under an octave", () => {
  const notes = [note({ id: "a", pitch: 90 })];

  const out = fitNotesToRange(notes, 60, 66);

  assert.equal(out[0].pitch, 90);
});

test("getPlayabilityStats reports removed counts", () => {
  const raw = [note({ id: "a" }), note({ id: "b" })];
  const playable = [raw[0]];

  assert.deepEqual(getPlayabilityStats(raw, playable), {
    rawCount: 2,
    playableCount: 1,
    removedCount: 1,
  });
});
