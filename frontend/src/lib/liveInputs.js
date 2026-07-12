/*
 * Live note inputs beyond the microphone:
 *
 *   1. Web MIDI  – a real digital piano / MIDI keyboard. The most precise
 *                  input for note checking (what Synthesia uses).
 *   2. Computer keyboard – play without any instrument:
 *                  A S D F G H J K L ;  = white keys from C4
 *                  W E   T Y U   O P   = the black keys between them
 *                  Z / X shift the octave down / up.
 *
 * Both feed the same onNoteOn / onNoteOff callbacks that the practice
 * scorer and the sampler already understand.
 */

const KEYBOARD_BASE_MIDI = 60; // C4

const KEY_TO_OFFSET = {
  KeyA: 0, // C
  KeyW: 1, // C#
  KeyS: 2, // D
  KeyE: 3, // D#
  KeyD: 4, // E
  KeyF: 5, // F
  KeyT: 6, // F#
  KeyG: 7, // G
  KeyY: 8, // G#
  KeyH: 9, // A
  KeyU: 10, // A#
  KeyJ: 11, // B
  KeyK: 12, // C5
  KeyO: 13, // C#5
  KeyL: 14, // D5
  KeyP: 15, // D#5
  Semicolon: 16, // E5
};

function isTypingTarget(target) {
  if (!target) return false;

  const tag = target.tagName;

  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    target.isContentEditable
  );
}

export function attachComputerKeyboardPiano({
  onNoteOn = () => {},
  onNoteOff = () => {},
  onOctaveChange = () => {},
} = {}) {
  let octaveShift = 0;
  const heldCodes = new Map(); // code -> midi

  function handleKeyDown(event) {
    if (event.repeat || event.metaKey || event.ctrlKey || event.altKey) return;
    if (isTypingTarget(event.target)) return;

    if (event.code === "KeyZ") {
      octaveShift = Math.max(octaveShift - 1, -3);
      onOctaveChange(octaveShift);
      return;
    }

    if (event.code === "KeyX") {
      octaveShift = Math.min(octaveShift + 1, 3);
      onOctaveChange(octaveShift);
      return;
    }

    const offset = KEY_TO_OFFSET[event.code];
    if (offset === undefined) return;

    event.preventDefault();

    const midi = KEYBOARD_BASE_MIDI + octaveShift * 12 + offset;
    heldCodes.set(event.code, midi);
    onNoteOn(midi, 92);
  }

  function handleKeyUp(event) {
    const midi = heldCodes.get(event.code);
    if (midi === undefined) return;

    heldCodes.delete(event.code);
    onNoteOff(midi);
  }

  window.addEventListener("keydown", handleKeyDown);
  window.addEventListener("keyup", handleKeyUp);

  return () => {
    window.removeEventListener("keydown", handleKeyDown);
    window.removeEventListener("keyup", handleKeyUp);

    for (const midi of heldCodes.values()) {
      onNoteOff(midi);
    }

    heldCodes.clear();
  };
}

export function createMidiInput({
  onNoteOn = () => {},
  onNoteOff = () => {},
  onStatus = () => {},
} = {}) {
  let access = null;
  let disposed = false;
  const boundInputs = new Set();

  function handleMessage(event) {
    const [status, note, velocity] = event.data;
    const command = status & 0xf0;

    if (command === 0x90 && velocity > 0) {
      onNoteOn(note, velocity);
    } else if (command === 0x80 || (command === 0x90 && velocity === 0)) {
      onNoteOff(note);
    }
  }

  function bindInputs() {
    if (!access) return;

    let count = 0;

    for (const input of access.inputs.values()) {
      if (!boundInputs.has(input)) {
        input.addEventListener("midimessage", handleMessage);
        boundInputs.add(input);
      }
      count += 1;
    }

    onStatus(count > 0 ? "connected" : "waiting");
  }

  async function start() {
    if (!navigator.requestMIDIAccess) {
      onStatus("unsupported");
      return;
    }

    try {
      access = await navigator.requestMIDIAccess({ sysex: false });
    } catch {
      onStatus("denied");
      return;
    }

    if (disposed) return;

    bindInputs();
    access.addEventListener("statechange", bindInputs);
  }

  function stop() {
    disposed = true;

    for (const input of boundInputs) {
      input.removeEventListener("midimessage", handleMessage);
    }

    boundInputs.clear();

    if (access) {
      access.removeEventListener("statechange", bindInputs);
      access = null;
    }

    onStatus("off");
  }

  return { start, stop };
}
