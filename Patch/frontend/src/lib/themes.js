/*
 * Theme system for DaiTune
 * ------------------------
 * Two independent axes, both persisted in localStorage:
 *
 *   1. UI theme        – overall interface colors (light / dark / colored).
 *                        Applied as body[data-theme="…"]; CSS does the rest.
 *                        Each theme also carries the waterfall stage gradient.
 *
 *   2. Block palette   – the colors of the falling note blocks (and the
 *                        active piano keys / sheet noteheads), changeable
 *                        separately from the UI theme.
 */

export const UI_THEME_STORAGE_KEY = "daitune-ui-theme";
export const BLOCK_PALETTE_STORAGE_KEY = "daitune-block-palette";

/* ------------------------------ helpers ------------------------------ */

export function hexToRgba(hex, alpha = 1) {
  const value = hex.replace("#", "");
  const full =
    value.length === 3
      ? value
          .split("")
          .map((char) => char + char)
          .join("")
      : value;

  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function shadeHex(hex, amount) {
  // amount in [-1, 1]; negative darkens, positive lightens.
  const value = hex.replace("#", "");
  const full =
    value.length === 3
      ? value
          .split("")
          .map((char) => char + char)
          .join("")
      : value;

  const channel = (offset) => {
    const base = parseInt(full.slice(offset, offset + 2), 16);
    const target = amount >= 0 ? 255 : 0;
    const mixed = Math.round(base + (target - base) * Math.abs(amount));
    return Math.max(0, Math.min(255, mixed)).toString(16).padStart(2, "0");
  };

  return `#${channel(0)}${channel(2)}${channel(4)}`;
}

/* ------------------------------ UI themes ---------------------------- */

export const UI_THEMES = [
  {
    id: "daitune",
    label: "DaiTune",
    stage: ["#071026", "#111A3F", "#17143D", "#241542", "#381A48"],
  },
  {
    id: "dark",
    label: "Dark",
    stage: ["#05060C", "#0A0C16", "#0D0F1C", "#111325", "#15172C"],
  },
  {
    id: "midnight",
    label: "Midnight",
    stage: ["#020B1E", "#04132E", "#071B3E", "#0A234E", "#0E2B5E"],
  },
  {
    id: "ocean",
    label: "Ocean",
    stage: ["#02222B", "#053641", "#074753", "#0A5A66", "#0D6C78"],
  },
  {
    id: "sunset",
    label: "Sunset",
    stage: ["#1C0A2E", "#33103C", "#4C1543", "#651A45", "#7E2143"],
  },
  {
    id: "light",
    label: "Light",
    stage: ["#20264A", "#272E58", "#2E3566", "#353C74", "#3C4382"],
  },
];

export function getUiTheme(themeId) {
  return UI_THEMES.find((theme) => theme.id === themeId) || UI_THEMES[0];
}

export function applyUiTheme(themeId) {
  const theme = getUiTheme(themeId);

  document.body.dataset.theme = theme.id;

  try {
    localStorage.setItem(UI_THEME_STORAGE_KEY, theme.id);
  } catch {
    /* private mode – ignore */
  }

  return theme;
}

export function loadStoredUiThemeId() {
  try {
    const stored = localStorage.getItem(UI_THEME_STORAGE_KEY);
    return getUiTheme(stored).id;
  } catch {
    return UI_THEMES[0].id;
  }
}

/* --------------------------- block palettes -------------------------- */

function buildHand(fillHex) {
  return {
    fill: fillHex,
    stroke: shadeHex(fillHex, 0.55),
    glow: hexToRgba(fillHex, 0.9),
  };
}

export const BLOCK_PALETTES = [
  {
    id: "classic",
    label: "Classic",
    left: { fill: "#60a5fa", stroke: "#bfdbfe", glow: "rgba(96, 165, 250, 0.9)" },
    right: { fill: "#f472b6", stroke: "#fbcfe8", glow: "rgba(244, 114, 182, 0.9)" },
  },
  {
    id: "neon",
    label: "Neon",
    left: buildHand("#22e58f"),
    right: buildHand("#e743ff"),
  },
  {
    id: "ocean",
    label: "Ocean",
    left: buildHand("#2dd4bf"),
    right: buildHand("#fb923c"),
  },
  {
    id: "candy",
    label: "Candy",
    left: buildHand("#a78bfa"),
    right: buildHand("#fb7185"),
  },
  {
    id: "sunbeam",
    label: "Sunbeam",
    left: buildHand("#facc15"),
    right: buildHand("#38bdf8"),
  },
  {
    id: "mono",
    label: "Mono",
    left: buildHand("#94a3b8"),
    right: buildHand("#f8fafc"),
  },
];

export function getBlockPalette(paletteId) {
  return (
    BLOCK_PALETTES.find((palette) => palette.id === paletteId) ||
    BLOCK_PALETTES[0]
  );
}

export function applyBlockPalette(paletteId) {
  const palette = getBlockPalette(paletteId);
  const root = document.documentElement;

  // Legend chips + active piano keys read these variables.
  root.style.setProperty("--left-hand", palette.left.fill);
  root.style.setProperty("--right-hand", palette.right.fill);

  root.style.setProperty("--key-left-top", shadeHex(palette.left.fill, 0.6));
  root.style.setProperty("--key-left-bottom", palette.left.fill);
  root.style.setProperty("--key-left-deep", shadeHex(palette.left.fill, -0.35));
  root.style.setProperty("--key-left-glow", palette.left.glow);

  root.style.setProperty("--key-right-top", shadeHex(palette.right.fill, 0.6));
  root.style.setProperty("--key-right-bottom", palette.right.fill);
  root.style.setProperty("--key-right-deep", shadeHex(palette.right.fill, -0.35));
  root.style.setProperty("--key-right-glow", palette.right.glow);

  try {
    localStorage.setItem(BLOCK_PALETTE_STORAGE_KEY, palette.id);
  } catch {
    /* ignore */
  }

  return palette;
}

export function loadStoredBlockPaletteId() {
  try {
    const stored = localStorage.getItem(BLOCK_PALETTE_STORAGE_KEY);
    return getBlockPalette(stored).id;
  } catch {
    return BLOCK_PALETTES[0].id;
  }
}

/* Sheet helpers – ink-friendly variants of a hand color for paper. */

export function buildSheetHand(hand) {
  return {
    head: shadeHex(hand.fill, -0.22),
    bar: hexToRgba(hand.fill, 0.28),
    stem: shadeHex(hand.fill, -0.5),
  };
}

/* Canvas helpers – derived visuals for black-key note accents. */

export function buildBlackKeyAccent(hand) {
  return {
    top: hexToRgba(shadeHex(hand.fill, 0.45).replace("#", "#"), 0.96),
    middle: hexToRgba(hand.fill, 0.92),
    bottom: hexToRgba(shadeHex(hand.fill, -0.3), 0.88),
    stroke: hexToRgba(shadeHex(hand.fill, 0.7), 0.98),
    glow: hexToRgba(hand.fill, 0.78),
    label: "#fbfdff",
    labelShadow: "rgba(6, 10, 26, 0.86)",
  };
}
