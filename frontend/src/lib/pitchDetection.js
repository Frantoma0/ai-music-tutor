/*
 * Live microphone pitch detection
 * -------------------------------
 * Web Audio API + time-domain autocorrelation (McLeod-style normalized
 * difference) with parabolic interpolation. Runs fully in the browser,
 * no dependencies, local-first.
 *
 * Emits:
 *   onStatus(status)          "starting" | "listening" | "denied" | "error" | "stopped"
 *   onPitch({ midi, frequency, clarity, rms })   every analysed frame with a stable pitch
 *   onSilence()               frame below the noise gate
 *   onNoteOn(midi)            a NEW note attack (debounced + smoothed)
 */

const MIN_FREQUENCY = 50; // below A1 – ignore rumble
const MAX_FREQUENCY = 2100; // above C7 – ignore hiss
const RMS_GATE = 0.012; // noise gate
const CLARITY_GATE = 0.86; // autocorrelation confidence gate
const ANALYSIS_INTERVAL_MS = 45;
const STABLE_FRAMES_FOR_NOTE_ON = 2; // frames of the same midi before note-on
const SILENCE_FRAMES_FOR_RELEASE = 3; // frames of silence before re-attack allowed
const REATTACK_RMS_JUMP = 1.9; // energy jump that counts as repeated note

export function frequencyToMidi(frequency) {
  return Math.round(69 + 12 * Math.log2(frequency / 440));
}

/*
 * Autocorrelation with normalization and parabolic peak interpolation.
 * Returns { frequency, clarity } or null when no periodic signal found.
 */
export function detectPitch(buffer, sampleRate) {
  const size = buffer.length;

  let rms = 0;
  for (let i = 0; i < size; i += 1) {
    rms += buffer[i] * buffer[i];
  }
  rms = Math.sqrt(rms / size);

  if (rms < RMS_GATE) {
    return { frequency: null, clarity: 0, rms };
  }

  const maxLag = Math.floor(sampleRate / MIN_FREQUENCY);
  const minLag = Math.floor(sampleRate / MAX_FREQUENCY);
  const lagLimit = Math.min(maxLag, Math.floor(size / 2));

  let bestLag = -1;
  let bestCorrelation = 0;

  // Normalized autocorrelation over the allowed lag range.
  for (let lag = minLag; lag <= lagLimit; lag += 1) {
    let correlation = 0;
    let energyA = 0;
    let energyB = 0;

    for (let i = 0; i < size - lag; i += 1) {
      const a = buffer[i];
      const b = buffer[i + lag];
      correlation += a * b;
      energyA += a * a;
      energyB += b * b;
    }

    const normalizer = Math.sqrt(energyA * energyB) || 1;
    const normalized = correlation / normalizer;

    if (normalized > bestCorrelation) {
      bestCorrelation = normalized;
      bestLag = lag;
    }
  }

  if (bestLag <= 0 || bestCorrelation < CLARITY_GATE) {
    return { frequency: null, clarity: bestCorrelation, rms };
  }

  // Parabolic interpolation around the best lag for sub-sample accuracy.
  const correlationAt = (lag) => {
    if (lag < minLag || lag > lagLimit) return 0;

    let correlation = 0;
    let energyA = 0;
    let energyB = 0;

    for (let i = 0; i < size - lag; i += 1) {
      const a = buffer[i];
      const b = buffer[i + lag];
      correlation += a * b;
      energyA += a * a;
      energyB += b * b;
    }

    return correlation / (Math.sqrt(energyA * energyB) || 1);
  };

  const left = correlationAt(bestLag - 1);
  const right = correlationAt(bestLag + 1);
  const denominator = 2 * (2 * bestCorrelation - left - right);
  const shift = denominator !== 0 ? (right - left) / denominator : 0;
  const refinedLag = bestLag + Math.max(-0.5, Math.min(0.5, shift));

  return {
    frequency: sampleRate / refinedLag,
    clarity: bestCorrelation,
    rms,
  };
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

export function createMicPitchDetector({
  onStatus = () => {},
  onPitch = () => {},
  onSilence = () => {},
  onNoteOn = () => {},
} = {}) {
  let audioContext = null;
  let mediaStream = null;
  let analyser = null;
  let timerId = null;
  let disposed = false;

  const recentMidis = [];
  let stableMidi = null;
  let stableFrames = 0;
  let lastEmittedMidi = null;
  let silenceFrames = SILENCE_FRAMES_FOR_RELEASE;
  let previousRms = 0;

  function analyseFrame(buffer) {
    analyser.getFloatTimeDomainData(buffer);

    const { frequency, clarity, rms } = detectPitch(
      buffer,
      audioContext.sampleRate
    );

    if (!frequency) {
      silenceFrames += 1;
      recentMidis.length = 0;
      stableMidi = null;
      stableFrames = 0;

      if (silenceFrames >= SILENCE_FRAMES_FOR_RELEASE) {
        lastEmittedMidi = null;
        onSilence();
      }

      previousRms = rms;
      return;
    }

    const rawMidi = frequencyToMidi(frequency);

    // Median smoothing over the last 3 frames kills octave flickers.
    recentMidis.push(rawMidi);
    if (recentMidis.length > 3) recentMidis.shift();
    const smoothMidi = median(recentMidis);

    onPitch({ midi: smoothMidi, frequency, clarity, rms });

    if (smoothMidi === stableMidi) {
      stableFrames += 1;
    } else {
      stableMidi = smoothMidi;
      stableFrames = 1;
    }

    const isReattack =
      smoothMidi === lastEmittedMidi &&
      rms > previousRms * REATTACK_RMS_JUMP &&
      silenceFrames === 0;

    const isNewStableNote =
      stableFrames >= STABLE_FRAMES_FOR_NOTE_ON &&
      smoothMidi !== lastEmittedMidi;

    const isAfterSilence =
      stableFrames >= STABLE_FRAMES_FOR_NOTE_ON &&
      silenceFrames >= SILENCE_FRAMES_FOR_RELEASE;

    if (isNewStableNote || isAfterSilence || isReattack) {
      lastEmittedMidi = smoothMidi;
      onNoteOn(smoothMidi);
    }

    silenceFrames = 0;
    previousRms = rms;
  }

  async function start() {
    onStatus("starting");

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      });
    } catch (error) {
      onStatus("denied");
      throw error;
    }

    if (disposed) {
      mediaStream.getTracks().forEach((track) => track.stop());
      return;
    }

    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    audioContext = new AudioContextClass();

    const source = audioContext.createMediaStreamSource(mediaStream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);

    const buffer = new Float32Array(analyser.fftSize);

    timerId = setInterval(() => {
      if (disposed) return;

      try {
        analyseFrame(buffer);
      } catch (error) {
        console.warn("Pitch analysis frame failed:", error);
      }
    }, ANALYSIS_INTERVAL_MS);

    onStatus("listening");
  }

  function stop() {
    disposed = true;

    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }

    if (audioContext) {
      audioContext.close().catch(() => {});
      audioContext = null;
    }

    onStatus("stopped");
  }

  return { start, stop };
}
