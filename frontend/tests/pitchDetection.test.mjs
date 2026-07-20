import assert from "node:assert/strict";
import test from "node:test";

import { detectPitch, frequencyToMidi } from "../src/lib/pitchDetection.js";

const SAMPLE_RATE = 44100;
const BUFFER_SIZE = 2048;

function sineBuffer(frequency, amplitude = 0.4) {
  const buffer = new Float32Array(BUFFER_SIZE);

  for (let i = 0; i < BUFFER_SIZE; i += 1) {
    buffer[i] = amplitude * Math.sin((2 * Math.PI * frequency * i) / SAMPLE_RATE);
  }

  return buffer;
}

test("frequencyToMidi maps reference pitches correctly", () => {
  assert.equal(frequencyToMidi(440), 69); // A4
  assert.equal(frequencyToMidi(261.63), 60); // C4
  assert.equal(frequencyToMidi(130.81), 48); // C3
});

test("detectPitch finds a clean A4 sine within a few cents", () => {
  const { frequency, clarity } = detectPitch(sineBuffer(440), SAMPLE_RATE);

  assert.ok(frequency !== null);
  assert.ok(Math.abs(frequency - 440) < 2, `expected ~440 Hz, got ${frequency}`);
  assert.ok(clarity > 0.9);
  assert.equal(frequencyToMidi(frequency), 69);
});

test("detectPitch resolves a low C3 sine to the right key", () => {
  const { frequency } = detectPitch(sineBuffer(130.81), SAMPLE_RATE);

  assert.ok(frequency !== null);
  assert.equal(frequencyToMidi(frequency), 48);
});

test("detectPitch gates out silence", () => {
  const silence = new Float32Array(BUFFER_SIZE);

  const { frequency, rms } = detectPitch(silence, SAMPLE_RATE);

  assert.equal(frequency, null);
  assert.ok(rms < 0.012);
});

test("detectPitch rejects noise without a periodic signal", () => {
  const noise = new Float32Array(BUFFER_SIZE);

  let seed = 42;
  for (let i = 0; i < BUFFER_SIZE; i += 1) {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    noise[i] = (seed / 2147483648 - 0.5) * 0.5;
  }

  const { frequency, clarity } = detectPitch(noise, SAMPLE_RATE);

  assert.ok(frequency === null || clarity < 0.9);
});
