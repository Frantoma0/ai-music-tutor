import React, { useEffect, useRef } from "react";
import {
  confidenceClass,
  handForPitch,
  pitchToX,
  LOWEST_PITCH,
  HIGHEST_PITCH,
} from "../lib/noteMapping";

const PIXELS_PER_SECOND = 140;
const NOTE_WIDTH = 18;
const HIT_LINE_Y_RATIO = 0.78;

function colorForNote(note) {
  const hand = handForPitch(note.pitch);
  const confidence = confidenceClass(note.confidence);

  if (confidence === "low") {
    return "#f97316";
  }

  if (confidence === "medium") {
    return hand === "left" ? "#60a5fa" : "#facc15";
  }

  return hand === "left" ? "#2563eb" : "#22c55e";
}

function drawKeyboardGuide(ctx, width, height) {
  ctx.save();

  ctx.strokeStyle = "rgba(148, 163, 184, 0.18)";
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

function drawHitLine(ctx, width, y) {
  ctx.save();

  ctx.strokeStyle = "rgba(248, 250, 252, 0.75)";
  ctx.lineWidth = 2;

  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(width, y);
  ctx.stroke();

  ctx.restore();
}

function drawNote(ctx, note, width, hitLineY, currentTime, tempo) {
  const x = pitchToX(note.pitch, width);
  const noteDuration = Math.max(note.end - note.start, 0.08);

  const scaledStart = note.start / tempo;
  const scaledEnd = note.end / tempo;
  const scaledCurrent = currentTime;

  const yTop = hitLineY - (scaledStart - scaledCurrent) * PIXELS_PER_SECOND;
  const yBottom = hitLineY - (scaledEnd - scaledCurrent) * PIXELS_PER_SECOND;

  const y = Math.min(yTop, yBottom);
  const h = Math.max(Math.abs(yBottom - yTop), noteDuration * PIXELS_PER_SECOND * 0.35);

  if (y > hitLineY + 120 || y + h < -80) {
    return;
  }

  ctx.save();

  ctx.fillStyle = colorForNote(note);
  ctx.strokeStyle = "rgba(15, 23, 42, 0.65)";
  ctx.lineWidth = 1.5;

  const radius = 7;
  const rectX = x - NOTE_WIDTH / 2;
  const rectY = y;
  const rectW = NOTE_WIDTH;
  const rectH = h;

  ctx.beginPath();

  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(rectX, rectY, rectW, rectH, radius);
  } else {
    ctx.rect(rectX, rectY, rectW, rectH);
  }

  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = "rgba(15, 23, 42, 0.75)";
  ctx.font = "10px Inter, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(note.pitchName, x, rectY - 5);

  ctx.restore();
}

export function WaterfallCanvas({ notes, currentTime, tempo }) {
  const canvasRef = useRef(null);

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

    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, "#020617");
    gradient.addColorStop(1, "#111827");

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    drawKeyboardGuide(ctx, width, height);

    for (const note of notes) {
      drawNote(ctx, note, width, hitLineY, currentTime, tempo);
    }

    drawHitLine(ctx, width, hitLineY);
  }, [notes, currentTime, tempo]);

  return <canvas ref={canvasRef} className="waterfall-canvas" />;
}
