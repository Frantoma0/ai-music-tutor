import React, { useEffect, useRef } from "react";
import {
  confidenceLevel,
  handForPitch,
  noteDisplayContent,
  pitchToX,
  LOWEST_PITCH,
  HIGHEST_PITCH,
} from "../lib/noteMapping";
import { confidenceStyle, lessonColors } from "../lib/designTokens";
import { buildBlackKeyAccent, hexToRgba } from "../lib/themes";


const STAGE_MIN_HEIGHT = 640;
const KEYBOARD_HEIGHT = 118;
const KEYBOARD_WHITE_KEY_HEIGHT = 96;
const KEYBOARD_BLACK_KEY_HEIGHT = 60;
const KEYBOARD_BLACK_KEY_WIDTH_RATIO = 0.58;

const PLAYFIELD_BG_LEFT = "#2F49AA";
const PLAYFIELD_BG_MID = "#5448A0";
const PLAYFIELD_BG_RIGHT = "#B05C9E";
const PLAYFIELD_OVERLAY_TOP = "rgba(20, 24, 58, 0.22)";
const PLAYFIELD_OVERLAY_BOTTOM = "rgba(9, 12, 30, 0.34)";
const PLAYFIELD_GRID = "rgba(255, 255, 255, 0.085)";
const PLAYFIELD_GRID_STRONG = "rgba(255, 255, 255, 0.13)";
const PLAYFIELD_BORDER = "rgba(255, 220, 255, 0.52)";
const HIT_LINE = "rgba(210, 155, 255, 0.30)";
const HIT_LINE_GLOW = "rgba(190, 120, 255, 0.12)";


const PIXELS_PER_SECOND = 140;
const NOTE_WIDTH = 22;
const NOTE_VISUAL_Y_OFFSET = 10;
const HIT_LINE_Y_RATIO = 0.985;
const RAW_MIN_NOTE_HEIGHT = 8;
const PRACTICE_MIN_NOTE_HEIGHT = 18;
const PRACTICE_CONNECTOR_MAX_GAP_SECONDS = 0.045;
const PRACTICE_CONNECTOR_MIN_GAP_SECONDS = 0.004;
const PRACTICE_CONNECTOR_WIDTH = 8;

const BLACK_KEY_PITCH_CLASSES = new Set([1, 3, 6, 8, 10]);

function isBlackKeyPitch(pitch) {
  const pitchNumber = Number(pitch);

  if (!Number.isFinite(pitchNumber)) {
    return false;
  }

  const pitchClass = ((pitchNumber % 12) + 12) % 12;

  return BLACK_KEY_PITCH_CLASSES.has(pitchClass);
}

function notePalette(note, colors = lessonColors) {
  const hand = note.hand === "left" || note.hand === "right"
    ? note.hand
    : handForPitch(note.pitch);

  return hand === "left" ? colors.leftHand : colors.rightHand;
}

const JUDGEMENT_PALETTES = {
  hit: {
    fill: "rgba(24, 168, 112, 0.94)",
    stroke: "rgba(178, 245, 214, 0.98)",
    glow: "rgba(52, 211, 153, 0.78)",
  },
  miss: {
    fill: "rgba(214, 72, 72, 0.90)",
    stroke: "rgba(254, 205, 205, 0.96)",
    glow: "rgba(248, 113, 113, 0.66)",
  },
};

function paletteForNote(note, judgement, colors) {
  return JUDGEMENT_PALETTES[judgement] || notePalette(note, colors);
}

function blackKeyAccentPalette(note, colors = lessonColors) {
  const hand = note.hand === "left" || note.hand === "right"
    ? note.hand
    : handForPitch(note.pitch);

  return buildBlackKeyAccent(
    hand === "left" ? colors.leftHand : colors.rightHand
  );
}

const UNKNOWN_CONFIDENCE_STYLE = {
  alpha: 0.72,
  borderWidth: 1.35,
  lineDash: [],
};

function isInCorrectionMask(note) {
  return Boolean(note.inCorrectionMask || note.in_correction_mask);
}

function visualConfidenceLevel(note) {
  if (isInCorrectionMask(note)) {
    return "low";
  }

  if (note.confidence === null || note.confidence === undefined) {
    return "unknown";
  }

  return confidenceLevel(note.confidence);
}

function noteAccidentalForPitch(note) {
  const pitchClass = Number(note.pitch) % 12;

  if ([1, 3, 6, 8, 10].includes(pitchClass)) {
    return "♯";
  }

  return "";
}

function staffStepForPitch(note) {
  /*
   * Returns a small visual offset so symbols are not identical.
   * This is not full notation rendering; it is a compact block icon.
   */
  const pitchClass = Number(note.pitch) % 12;

  const stepMap = {
    0: 2,  // C
    1: 2,  // C#
    2: 1,  // D
    3: 1,  // D#
    4: 0,  // E
    5: -1, // F
    6: -1, // F#
    7: -2, // G
    8: -2, // G#
    9: -3, // A
    10: -3, // A#
    11: -4, // B
  };

  return stepMap[pitchClass] ?? 0;
}

function drawMiniNotationSymbol(ctx, note, centerX, centerY) {
  const accidental = noteAccidentalForPitch(note);
  const pitch = Number(note.pitch);
  const stepOffset = staffStepForPitch(note) * 1.05;
  const noteY = centerY + stepOffset;

  const stemUp = pitch < 67;
  const noteW = 7.2;
  const noteH = 5.0;

  ctx.save();

  ctx.globalAlpha = 0.98;
  ctx.fillStyle = "#101124";
  ctx.strokeStyle = "#101124";
  ctx.lineWidth = 1.25;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.shadowBlur = 0;

  if (accidental) {
    ctx.font = "900 18px Georgia, 'Times New Roman', serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(accidental, centerX - 9.8, noteY - 1.2);
  }

  // Tiny staff hint line for stronger "sheet" feeling.
  ctx.globalAlpha = 0.22;
  ctx.beginPath();
  ctx.moveTo(centerX - 9.2, centerY + 6.8);
  ctx.lineTo(centerX + 9.2, centerY + 6.8);
  ctx.stroke();

  ctx.globalAlpha = 0.98;

  // Note head.
  ctx.save();
  ctx.translate(centerX - 1, noteY);
  ctx.rotate(-0.28);
  ctx.beginPath();
  ctx.ellipse(0, 0, noteW / 2, noteH / 2, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  // Stem.
  const stemX = centerX + 3.2;

  ctx.beginPath();

  if (stemUp) {
    ctx.moveTo(stemX, noteY - 1.2);
    ctx.lineTo(stemX, noteY - 15.5);
  } else {
    ctx.moveTo(centerX - 4.2, noteY + 1.2);
    ctx.lineTo(centerX - 4.2, noteY + 15.5);
  }

  ctx.stroke();

  // Small flag for eighth-note feeling.
  ctx.beginPath();

  if (stemUp) {
    ctx.moveTo(stemX, noteY - 15.5);
    ctx.quadraticCurveTo(stemX + 6.2, noteY - 13.2, stemX + 4.2, noteY - 8);
  } else {
    ctx.moveTo(centerX - 4.2, noteY + 15.5);
    ctx.quadraticCurveTo(centerX + 2.6, noteY + 13.2, centerX + 0.6, noteY + 8);
  }

  ctx.stroke();

  ctx.restore();
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();

  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(x, y, width, height, radius);
  } else {
    ctx.rect(x, y, width, height);
  }
}

function drawBlackKeyNoteAccents(ctx, note, rectX, rectY, rectW, rectH, colors) {
  const accent = blackKeyAccentPalette(note, colors);

  ctx.save();

  ctx.shadowColor = accent.glow;
  ctx.shadowBlur = 14;
  ctx.globalAlpha = 0.96;

  const accentFill = ctx.createLinearGradient(rectX, rectY, rectX, rectY + rectH);
  accentFill.addColorStop(0, accent.top);
  accentFill.addColorStop(0.48, accent.middle);
  accentFill.addColorStop(1, accent.bottom);

  ctx.fillStyle = accentFill;
  ctx.strokeStyle = accent.stroke;
  ctx.lineWidth = 2.05;
  ctx.setLineDash([]);

  drawRoundedRect(ctx, rectX, rectY, rectW, rectH, 8);
  ctx.fill();
  ctx.stroke();

  // Cheap inner contrast: one soft vertical highlight, not repeated texture.
  ctx.shadowBlur = 0;
  ctx.globalAlpha = 0.30;
  ctx.strokeStyle = "rgba(255, 255, 255, 0.78)";
  ctx.lineWidth = 1.1;
  ctx.beginPath();
  ctx.moveTo(rectX + rectW * 0.34, rectY + 5);
  ctx.lineTo(rectX + rectW * 0.34, rectY + rectH - 5);
  ctx.stroke();

  ctx.restore();
}

function drawKeyboardGuide(ctx, width, height) {
  ctx.save();

  ctx.strokeStyle = "rgba(255, 255, 255, 0.055)";
  ctx.lineWidth = 1;

  for (let pitch = LOWEST_PITCH; pitch <= HIGHEST_PITCH; pitch += 1) {
    const x = pitchToX(pitch, width);

    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  ctx.restore();
}

function drawHitLine(ctx, x, y, width) {
  ctx.save();

  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + width, y);
  ctx.strokeStyle = HIT_LINE;
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + width, y);
  ctx.strokeStyle = HIT_LINE_GLOW;
  ctx.lineWidth = 8;
  ctx.stroke();

  ctx.restore();
}

function drawHitSpark(ctx, x, y, color, intensity = 1) {
  ctx.save();

  const alpha = 0.72 * intensity;

  ctx.globalAlpha = alpha;
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.15;
  ctx.shadowColor = color;
  ctx.shadowBlur = 8;

  const rays = [
    [0, -11, 0, -3],
    [0, 3, 0, 11],
    [-11, 0, -3, 0],
    [3, 0, 11, 0],
    [-8, -8, -3, -3],
    [3, 3, 8, 8],
    [8, -8, 3, -3],
    [-3, 3, -8, 8],
  ];

  for (const [x1, y1, x2, y2] of rays) {
    ctx.beginPath();
    ctx.moveTo(x + x1, y + y1);
    ctx.lineTo(x + x2, y + y2);
    ctx.stroke();
  }

  ctx.globalAlpha = 0.9 * intensity;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x, y, 1.8, 0, Math.PI * 2);
  ctx.fill();

  ctx.restore();
}

function drawKeyStrikeGlow(ctx, x, y, color, intensity = 1) {
  ctx.save();

  const beam = ctx.createLinearGradient(x, y - 44, x, y + 8);
  beam.addColorStop(0, "rgba(255,255,255,0)");
  beam.addColorStop(0.58, color);
  beam.addColorStop(1, "rgba(255,255,255,0)");

  ctx.globalAlpha = 0.34 * intensity;
  ctx.fillStyle = beam;
  ctx.shadowColor = color;
  ctx.shadowBlur = 12;
  ctx.fillRect(x - 1, y - 44, 2, 52);

  ctx.restore();
}

function drawSubtleBaseGlow(ctx, x, y, color, intensity = 1) {
  ctx.save();

  const glow = ctx.createRadialGradient(x, y, 0, x, y, 22);
  glow.addColorStop(0, color);
  glow.addColorStop(0.35, "rgba(255,255,255,0.18)");
  glow.addColorStop(1, "rgba(255,255,255,0)");

  ctx.globalAlpha = 0.28 * intensity;
  ctx.fillStyle = glow;

  ctx.beginPath();
  ctx.ellipse(x, y + 2, 22, 7, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.restore();
}

function noteTimeToY(time, hitLineY, musicalTime) {
  return hitLineY - (time - musicalTime) * PIXELS_PER_SECOND + NOTE_VISUAL_Y_OFFSET;
}

function notesCanHavePracticeConnector(previousNote, currentNote) {
  if (!previousNote || !currentNote) {
    return false;
  }

  if (Number(previousNote.pitch) !== Number(currentNote.pitch)) {
    return false;
  }

  const previousHand = previousNote.hand ?? "unknown";
  const currentHand = currentNote.hand ?? "unknown";

  const handsCompatible =
    previousHand === currentHand ||
    previousHand === "unknown" ||
    currentHand === "unknown";

  if (!handsCompatible) {
    return false;
  }

  const previousEnd = Number(previousNote.end ?? previousNote.start ?? 0);
  const currentStart = Number(currentNote.start ?? 0);
  const gap = currentStart - previousEnd;

  return (
    gap >= PRACTICE_CONNECTOR_MIN_GAP_SECONDS &&
    gap <= PRACTICE_CONNECTOR_MAX_GAP_SECONDS
  );
}

function drawPracticeConnector(ctx, previousNote, currentNote, width, hitLineY, musicalTime, colors) {
  const x = pitchToX(currentNote.pitch, width);

  const previousEnd = Number(previousNote.end ?? previousNote.start ?? 0);
  const currentStart = Number(currentNote.start ?? 0);

  const yPreviousEnd = noteTimeToY(previousEnd, hitLineY, musicalTime);
  const yCurrentStart = noteTimeToY(currentStart, hitLineY, musicalTime);

  const connectorTop = Math.min(yPreviousEnd, yCurrentStart);
  const connectorBottom = Math.max(yPreviousEnd, yCurrentStart);
  const connectorHeight = Math.max(connectorBottom - connectorTop, 3);

  if (connectorTop > hitLineY + 120 || connectorBottom < -80) {
    return;
  }

  const palette = notePalette(currentNote, colors);
  const rectX = x - PRACTICE_CONNECTOR_WIDTH / 2;

  ctx.save();

  ctx.globalAlpha = 0.42;
  ctx.strokeStyle = palette.stroke;
  ctx.lineWidth = 1.4;
  ctx.setLineDash([3, 3]);
  ctx.shadowColor = palette.glow;
  ctx.shadowBlur = 5;

  drawRoundedRect(
    ctx,
    rectX,
    connectorTop,
    PRACTICE_CONNECTOR_WIDTH,
    connectorHeight,
    999
  );

  ctx.stroke();

  ctx.setLineDash([]);

  // Small seam marker: shows that this is a visual hint, not a merged note.
  ctx.globalAlpha = 0.72;
  ctx.beginPath();
  ctx.moveTo(x - 7, yCurrentStart);
  ctx.lineTo(x + 7, yCurrentStart);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.62)";
  ctx.lineWidth = 1;
  ctx.stroke();

  ctx.restore();
}

function drawPracticeConnectors(ctx, notes, width, hitLineY, musicalTime, colors) {
  const sortedNotes = [...notes].sort((first, second) => {
    const pitchDiff = Number(first.pitch) - Number(second.pitch);

    if (pitchDiff !== 0) {
      return pitchDiff;
    }

    return Number(first.start ?? 0) - Number(second.start ?? 0);
  });

  for (let index = 1; index < sortedNotes.length; index += 1) {
    const previousNote = sortedNotes[index - 1];
    const currentNote = sortedNotes[index];

    if (notesCanHavePracticeConnector(previousNote, currentNote)) {
      drawPracticeConnector(
        ctx,
        previousNote,
        currentNote,
        width,
        hitLineY,
        musicalTime,
        colors
      );
    }
  }
}

function drawNote(
  ctx,
  note,
  width,
  hitLineY,
  musicalTime,
  noteDisplayMode,
  noteViewMode,
  judgement,
  colors
) {
  const x = pitchToX(note.pitch, width);
  const yTop = hitLineY - (note.start - musicalTime) * PIXELS_PER_SECOND + NOTE_VISUAL_Y_OFFSET;
  const yBottom = hitLineY - (note.end - musicalTime) * PIXELS_PER_SECOND + NOTE_VISUAL_Y_OFFSET;

  const realTopY = Math.min(yTop, yBottom);
  const realBottomY = Math.max(yTop, yBottom);
  const rawHeight = Math.abs(yBottom - yTop);

  const minVisualHeight =
    noteViewMode === "practice"
      ? PRACTICE_MIN_NOTE_HEIGHT
      : RAW_MIN_NOTE_HEIGHT;

  const h = Math.max(rawHeight, minVisualHeight);

  /*
  * Important:
  * Keep the bottom edge locked to the real note onset.
  * If we increase the visual height, the block grows upward only.
  * This improves readability without changing when the learner should press.
  */
  const y = realBottomY - h;

  if (y > hitLineY + 120 || y + h < -80) {
    return;
  }

  const palette = paletteForNote(note, judgement, colors);
  const isBlackKeyNote = isBlackKeyPitch(note.pitch) && !judgement;
  const level = visualConfidenceLevel(note);
  const confidence =
    level === "unknown" ? UNKNOWN_CONFIDENCE_STYLE : confidenceStyle[level];

  const rectW = NOTE_WIDTH;
  const rectX = x - rectW / 2;
  const rectY = y;
  const rectH = h;

  ctx.save();

  ctx.globalAlpha = confidence.alpha;
  ctx.shadowColor = palette.glow;
  ctx.shadowBlur = level === "low" ? 3 : level === "unknown" ? 4 : 9;

  const fillGradient = ctx.createLinearGradient(rectX, rectY, rectX, rectY + rectH);
  fillGradient.addColorStop(0, palette.stroke);
  fillGradient.addColorStop(0.5, palette.fill);
  fillGradient.addColorStop(1, palette.fill);

  ctx.fillStyle = fillGradient;
  ctx.strokeStyle = palette.stroke;
  ctx.lineWidth = confidence.borderWidth;
  ctx.setLineDash(confidence.lineDash);

  drawRoundedRect(ctx, rectX, rectY, rectW, rectH, 8);
  ctx.fill();
  ctx.stroke();

  ctx.setLineDash([]);

  if (isBlackKeyNote) {
    drawBlackKeyNoteAccents(ctx, note, rectX, rectY, rectW, rectH, colors);
  }

  if (noteDisplayMode === "symbol") {
    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
    drawMiniNotationSymbol(ctx, note, x, rectY + Math.min(rectH / 2, 24));
  } else {
    const label = noteDisplayContent(note, noteDisplayMode);

    if (label) {
      ctx.globalAlpha = 1;
      ctx.shadowColor = isBlackKeyNote ? "rgba(3, 5, 18, 0.88)" : "transparent";
      ctx.shadowBlur = isBlackKeyNote ? 4 : 0;
      ctx.fillStyle = isBlackKeyNote ? "#f8fbff" : "#0f172a";
      ctx.font = "800 13px Inter, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(label, x, rectY + Math.min(rectH / 2, 22));
    }
  }

  if (judgement) {
    ctx.globalAlpha = 1;
    ctx.shadowColor = "rgba(4, 8, 20, 0.85)";
    ctx.shadowBlur = 4;
    ctx.fillStyle = "#ffffff";
    ctx.font = "900 12px Inter, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(
      judgement === "hit" ? "✓" : "✕",
      rectX + rectW - 7,
      rectY + 9
    );
  }

  ctx.restore();

  const noteIsTouchingHitLine = y <= hitLineY && y + h >= hitLineY;

  if (noteIsTouchingHitLine) {
    const centerDistance = Math.abs((y + h / 2) - hitLineY);
    const intensity = Math.max(0.28, Math.min(1, 1 - centerDistance / 120));

    drawSubtleBaseGlow(ctx, x, hitLineY, palette.glow, intensity);
    drawKeyStrikeGlow(ctx, x, hitLineY, palette.glow, intensity);
  }

  const onsetDistance = Math.abs(yBottom - hitLineY);

  if (onsetDistance < 7) {
    const intensity = Math.max(0.2, 1 - onsetDistance / 7);
    drawHitSpark(ctx, x, hitLineY, palette.stroke, intensity);
  }
}

export function WaterfallCanvas({
  notes,
  currentTime,
  musicalTime,
  tempo,
  noteDisplayMode,
  noteViewMode = "raw",
  judgements = {},
  colors = lessonColors,
  stage = null,
}) {
  const canvasRef = useRef(null);
  const effectiveMusicalTime = musicalTime ?? currentTime * tempo;

  useEffect(() => {
    const canvas = canvasRef.current;
    const parent = canvas.parentElement;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = parent.getBoundingClientRect();

      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;

      const ctx = canvas.getContext("2d");

      if (!ctx) {
        return;
      }

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();

    const observer = new ResizeObserver(resize);
    observer.observe(parent);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    if (!ctx) {
      return;
    }

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const hitLineY = height * HIT_LINE_Y_RATIO;

    ctx.clearRect(0, 0, width, height);

    const stageStops = stage || ["#071026", "#111A3F", "#17143D", "#241542", "#381A48"];

    const background = ctx.createLinearGradient(0, 0, width, 0);
    background.addColorStop(0.00, stageStops[0]);
    background.addColorStop(0.24, stageStops[1]);
    background.addColorStop(0.52, stageStops[2]);
    background.addColorStop(0.76, stageStops[3]);
    background.addColorStop(1.00, stageStops[4]);

    ctx.fillStyle = background;
    ctx.fillRect(0, 0, width, height);

    const leftGlow = ctx.createRadialGradient(
      width * 0.02,
      height * 0.48,
      0,
      width * 0.02,
      height * 0.48,
      width * 0.42
    );
    const leftGlowColor = colors.leftHand.fill;
    leftGlow.addColorStop(0, hexToRgba(leftGlowColor, 0.30));
    leftGlow.addColorStop(0.42, hexToRgba(leftGlowColor, 0.13));
    leftGlow.addColorStop(1, hexToRgba(leftGlowColor, 0));

    ctx.fillStyle = leftGlow;
    ctx.fillRect(0, 0, width, height);

    const centerGlow = ctx.createRadialGradient(
      width * 0.52,
      height * 0.45,
      0,
      width * 0.52,
      height * 0.45,
      width * 0.48
    );
    centerGlow.addColorStop(0, "rgba(116, 91, 198, 0.18)");
    centerGlow.addColorStop(0.48, "rgba(116, 91, 198, 0.08)");
    centerGlow.addColorStop(1, "rgba(116, 91, 198, 0)");

    ctx.fillStyle = centerGlow;
    ctx.fillRect(0, 0, width, height);

    const rightGlow = ctx.createRadialGradient(
      width * 1.02,
      height * 0.45,
      0,
      width * 1.02,
      height * 0.45,
      width * 0.44
    );
    const rightGlowColor = colors.rightHand.fill;
    rightGlow.addColorStop(0, hexToRgba(rightGlowColor, 0.24));
    rightGlow.addColorStop(0.45, hexToRgba(rightGlowColor, 0.11));
    rightGlow.addColorStop(1, hexToRgba(rightGlowColor, 0));

    ctx.fillStyle = rightGlow;
    ctx.fillRect(0, 0, width, height);

    const depthOverlay = ctx.createLinearGradient(0, 0, 0, height);
    depthOverlay.addColorStop(0.00, "rgba(4, 7, 20, 0.26)");
    depthOverlay.addColorStop(0.55, "rgba(5, 7, 18, 0.10)");
    depthOverlay.addColorStop(1.00, "rgba(8, 6, 18, 0.24)");

    ctx.fillStyle = depthOverlay;
    ctx.fillRect(0, 0, width, height);

    drawKeyboardGuide(ctx, width, height);

    if (noteViewMode === "practice") {
      drawPracticeConnectors(
        ctx,
        notes,
        width,
        hitLineY,
        effectiveMusicalTime,
        colors
      );
    }

    for (const note of notes) {
      drawNote(
        ctx,
        note,
        width,
        hitLineY,
        effectiveMusicalTime,
        noteDisplayMode,
        noteViewMode,
        judgements[note.id],
        colors
      );
    }

    drawHitLine(ctx, width, hitLineY);
  }, [notes, currentTime, effectiveMusicalTime, tempo, noteDisplayMode, noteViewMode, judgements, colors, stage]);

  return <canvas ref={canvasRef} className="waterfall-canvas" />;
}
