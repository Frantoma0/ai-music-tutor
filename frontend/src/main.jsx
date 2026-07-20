import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as Tone from "tone";
import "./styles.css";
import viewBlocksIcon from "./assets/view-blocks.png";
import viewSheetIcon from "./assets/view-sheet.png";
import viewMixIcon from "./assets/view-mix.png";
import daiTuneLogo from "./assets/dai_tune_logo.png";
import HandsControl from "./components/HandsControl.jsx";
import { PianoKeyboard } from "./components/PianoKeyboard";
import { WaterfallCanvas } from "./components/WaterfallCanvas";
import SheetView from "./components/SheetView.jsx";
import { buildPlayableNotes, fitNotesToRange, parseKeySignature } from "./lib/playability";
import { createMicPitchDetector } from "./lib/pitchDetection";
import {
  UI_THEMES,
  BLOCK_PALETTES,
  applyUiTheme,
  applyBlockPalette,
  getUiTheme,
  getBlockPalette,
  loadStoredUiThemeId,
  loadStoredBlockPaletteId, buildSheetHand } from "./lib/themes";
import { attachComputerKeyboardPiano, createMidiInput } from "./lib/liveInputs";
import { confidenceLevel } from "./lib/noteMapping";
import { demoNotes } from "./lib/demoNotes";
import {
  DEFAULT_LESSON_JOB_ID,
  dedupeRunsByJobId,
  deletePipelineRun,
  fetchLesson,
  fetchPipelineRuns,
  updatePipelineRunThumbnail,
  makeJobIdFromTitle,
  mapLessonNotesToUiNotes,
  runAudioToAnalysis,
  titleForRun,
  titleFromFilename,
  titleFromYouTubeUrl,
  uploadAudioFile,
  uploadYoutubeAudio, saveLessonProgress, fetchProgressSummary, saveLessonPosition, requestCoachPlan } from "./api/lessonApi";

const FALLBACK_DURATION_SECONDS = 4.2;

const LANGUAGE_STORAGE_KEY = "daiTuneLanguage";

const UI_COPY = {
  en: {
    "brand.name": "DaiTune",
    "brand.eyebrow": "Local-first piano tutor",
    "brand.subtitle": "Create, continue, and manage your piano lessons.",

    "common.close": "Close",
    "common.cancel": "Cancel",
    "common.create": "Create",
    "common.working": "Working...",
    "common.play": "Play",
    "common.pause": "Pause",
    "common.reset": "Reset",
    "common.saved": "saved",
    "common.unknown": "Unknown",
    "common.delete": "Delete",
    "common.rename": "Rename",

    "home.continueLatest": "Continue latest",
    "home.newLesson": "+ New lesson",
    "home.quickStart": "Quick start",
    "home.title": "Your piano lesson library",
    "home.description": "Paste a YouTube link or upload an audio file to create a local interactive piano lesson.",
    "home.pasteYoutube": "Paste YouTube link...",
    "home.add": "Add →",
    "home.upload": "Upload MP3 / WAV",
    "home.library": "Library",
    "home.yourLessons": "Your lessons",

    "drawer.menu": "Menu",
    "drawer.home": "Home page",
    "drawer.homeHint": "Lesson library and quick start",
    "drawer.newLessonHint": "Create from YouTube, MP3 or WAV",
    "drawer.currentLesson": "Current lesson",
    "drawer.savedLessons": "Saved lessons",

    "view.blocks": "Blocks",
    "view.sheet": "Sheet",
    "view.mix": "Mix",

    "player.label": "Player",
    "player.playLesson": "Play lesson",
    "player.pausePlayback": "Pause playback",

    "summary.reviewNotes": "Review notes",
    "summary.unknownConfidence": "Unknown confidence",
    "summary.fallback": "Using local fallback notes",

    "modal.createEyebrow": "Create",
    "modal.newLesson": "New lesson",
    "modal.lessonTitle": "Lesson title",
    "modal.titlePlaceholder": "Title",
    "modal.titleAutoHint": "Title can be filled automatically from YouTube metadata.",
    "modal.titleCustomHint": "Custom title will be kept.",
    "modal.youtubeUrl": "YouTube URL",
    "modal.uploadFile": "Upload file",
    "modal.audioFile": "Audio file",
    "modal.audioSource": "Audio source",
    "modal.youtubePlaceholder": "https://www.youtube.com/watch?v=...",
    "modal.sourcePlaceholder": "data/processed/yt-MZter9IuEO4/input.wav",
    "modal.preprocessing": "Audio preprocessing",
    "modal.preprocessingHint": "Safe cleanup before transcription",
    "modal.trimSilence": "Trim leading silence",
    "modal.trimSilenceHint": "Remove quiet silence at the start of the audio.",
    "modal.normalize": "Normalize volume",
    "modal.normalizeHint": "Make quiet or loud recordings more consistent.",
    "modal.highpass": "High-pass rumble filter",
    "modal.highpassHint": "Reduce low-frequency noise before transcription.",
    "modal.sourceSeparation": "Use source separation",
    "modal.sourceSeparationHint": "Slower, but useful for songs with vocals or full instrumental mixes.",
    "modal.processingFallbackTitle": "Processing lesson",
    "modal.processingFallbackHint": "Working...",
    "modal.createLesson": "Create lesson",
    "modal.lessonNamePrompt": "Lesson name",

    "controls.tempo": "Tempo",
    "controls.display": "Display",
    "controls.blank": "Blank",
    "controls.symbol": "♪",
    "controls.notes": "Notes",
    "controls.mic": "Mic",
    "notes.beginner": "Beginner",
    "controls.weak": "Weak notes",
    "coach.button": "Coach",
    "coach.title": "Your practice plan",
    "coach.loading": "Analyzing your practice...",
    "coach.empty": "Play at least one full attempt with mic or MIDI on, and I'll build your plan.",
    "coach.error": "Coach is unavailable right now.",
    "coach.practice": "Practice this",
    "coach.apply": "Apply",
    "coach.recommended": "Recommended",
    "coach.errorsWord": "slips",
    "coach.handLeft": "left hand",
    "coach.handRight": "right hand",
    "coach.handBoth": "both hands",
    "coach.close": "Close",
    "weak.show": "Show",
    "weak.hide": "Hide",
    "weak.hiddenCount": "hidden",
    "notes.hintRaw": "Raw view shows the original transcription.",
    "notes.hintPractice": "Practice: cleaned, playable arrangement",
    "notes.hintBeginner": "Beginner: melody + simple bass only",
    "notes.hidden": "artifacts hidden",
    "settings.piano": "My piano",
    "settings.pianoModel": "Choose a model (optional)",
    "settings.pianoSize": "Keyboard size",
    "settings.pianoFrom": "From",
    "settings.pianoTo": "To",
    "settings.pianoKeys": "keys",
    "settings.fitRange": "Fit songs to my piano range",
    "settings.custom": "Custom",
    "mic.on": "On",
    "mic.off": "Off",
    "mic.listening": "Listening",
    "mic.starting": "Starting...",
    "mic.denied": "Mic access denied",
    "practice.hits": "Hit",
    "practice.missed": "Missed",
    "practice.wrong": "Wrong",
    "practice.accuracy": "Accuracy",
    "settings.title": "Appearance & practice",
    "settings.theme": "Interface theme",
    "settings.blocks": "Note block colors",
    "settings.countdown": "3-2-1 countdown before play",
    "settings.midi": "MIDI keyboard",
    "settings.keysHint": "Computer keys: A–; play from C4 · W E T Y U O P are black keys · Z / X octave",
    "controls.mode": "Mode",
    "mode.flow": "Flow",
    "mode.wait": "Wait",
    "mode.waitHint": "Wait mode pauses on each note until you play it (mic, MIDI or keys).",
    "controls.metronome": "Metronome",
    "controls.loop": "Loop",
    "loop.setA": "A",
    "loop.setB": "B",
    "loop.clear": "Clear loop",
    "results.title": "Lesson results",
    "results.tryAgain": "Try again",
    "results.close": "Close",
    "controls.raw": "Raw",
    "controls.practice": "Practice",
    "controls.keys": "Keys",
    "controls.off": "Off",
    "controls.all": "All",
    "controls.lowConfidence": "Low conf.",

    "delete.confirmTitle": "Delete",
    "delete.confirmBody": "This will remove it from your saved lessons.",
    "errors.deleteFailed": "Failed to delete lesson.",
    "errors.enterTitle": "Please enter a lesson title.",
    "errors.chooseFile": "Please choose a .wav or .mp3 file.",
    "errors.enterSource": "Please enter a source.",
  },

  bg: {
    "brand.name": "DaiTune",
    "brand.eyebrow": "Локален пиано помощник",
    "brand.subtitle": "Създавай и управлявай своите пиано уроци.",

    "common.close": "Затвори",
    "common.cancel": "Отказ",
    "common.create": "Създай",
    "common.working": "Работи...",
    "common.play": "Старт",
    "common.pause": "Пауза",
    "common.reset": "Нулирай",
    "common.saved": "запазени",
    "common.unknown": "Неизвестно",
    "common.delete": "Изтрий",
    "common.rename": "Преименувай",

    "home.continueLatest": "Продължи последния",
    "home.newLesson": "+ Нов урок",
    "home.quickStart": "Бърз старт",
    "home.title": "Твоята библиотека с пиано уроци",
    "home.description": "Постави YouTube линк или качи аудио файл, за да създадеш локален интерактивен урок.",
    "home.pasteYoutube": "Постави YouTube линк...",
    "home.add": "Добави →",
    "home.upload": "Качи MP3 / WAV",
    "home.library": "Библиотека",
    "home.yourLessons": "Твоите уроци",

    "drawer.menu": "Меню",
    "drawer.home": "Начало",
    "drawer.homeHint": "Библиотека с уроци и бърз старт",
    "drawer.newLessonHint": "Създай от YouTube, MP3 или WAV",
    "drawer.currentLesson": "Текущ урок",
    "drawer.savedLessons": "Запазени уроци",

    "view.blocks": "Блокове",
    "view.sheet": "Партитура",
    "view.mix": "Смесено",

    "player.label": "Плеър",
    "player.playLesson": "Пусни урока",
    "player.pausePlayback": "Пауза",

    "summary.reviewNotes": "Ноти за преглед",
    "summary.unknownConfidence": "Неизвестна увереност",
    "summary.fallback": "Използват се локални примерни ноти",

    "modal.createEyebrow": "Създаване",
    "modal.newLesson": "Нов урок",
    "modal.lessonTitle": "Заглавие на урока",
    "modal.titlePlaceholder": "Заглавие",
    "modal.titleAutoHint": "Заглавието може да се попълни автоматично от YouTube metadata.",
    "modal.titleCustomHint": "Персонализираното заглавие ще бъде запазено.",
    "modal.youtubeUrl": "YouTube линк",
    "modal.uploadFile": "Качи файл",
    "modal.audioFile": "Аудио файл",
    "modal.audioSource": "Аудио източник",
    "modal.youtubePlaceholder": "https://www.youtube.com/watch?v=...",
    "modal.sourcePlaceholder": "data/processed/yt-MZter9IuEO4/input.wav",
    "modal.preprocessing": "Аудио обработка",
    "modal.preprocessingHint": "Безопасно почистване преди транскрипция",
    "modal.trimSilence": "Изрязване на начална тишина",
    "modal.trimSilenceHint": "Премахва тиха пауза в началото на аудиото.",
    "modal.normalize": "Нормализиране на звука",
    "modal.normalizeHint": "Прави тихите и силните записи по-равномерни.",
    "modal.highpass": "High-pass филтър",
    "modal.highpassHint": "Намалява нискочестотния шум преди транскрипция.",
    "modal.sourceSeparation": "Използвай разделяне на инструменти",
    "modal.sourceSeparationHint": "По-бавно, но полезно за песни с вокали или пълен инструментал.",
    "modal.processingFallbackTitle": "Обработка на урока",
    "modal.processingFallbackHint": "Работи...",
    "modal.createLesson": "Създай урок",
    "modal.lessonNamePrompt": "Име на урока",

    "controls.tempo": "Темпо",
    "controls.display": "Показване",
    "controls.blank": "Празно",
    "controls.symbol": "♪",
    "controls.notes": "Ноти",
    "controls.mic": "Микрофон",
    "notes.beginner": "Начинаещ",
    "controls.weak": "Слаби ноти",
    "coach.button": "Коуч",
    "coach.title": "Твоят план за упражнение",
    "coach.loading": "Анализирам свиренето ти...",
    "coach.empty": "Изсвири поне един пълен опит с включен микрофон или MIDI и ще ти направя план.",
    "coach.error": "Коучът не е достъпен в момента.",
    "coach.practice": "Упражнявай това",
    "coach.apply": "Приложи",
    "coach.recommended": "Препоръчано",
    "coach.errorsWord": "грешки",
    "coach.handLeft": "лява ръка",
    "coach.handRight": "дясна ръка",
    "coach.handBoth": "двете ръце",
    "coach.close": "Затвори",
    "weak.show": "Покажи",
    "weak.hide": "Скрий",
    "weak.hiddenCount": "скрити",
    "notes.hintRaw": "Raw показва оригиналната транскрипция.",
    "notes.hintPractice": "Practice: изчистен, реален за свирене аранжимент",
    "notes.hintBeginner": "Начинаещ: само мелодия + прост бас",
    "notes.hidden": "скрити артефакта",
    "settings.piano": "Моето пиано",
    "settings.pianoModel": "Избери модел (по избор)",
    "settings.pianoSize": "Размер на клавиатурата",
    "settings.pianoFrom": "От",
    "settings.pianoTo": "До",
    "settings.pianoKeys": "клавиша",
    "settings.fitRange": "Напасвай песните към моето пиано",
    "settings.custom": "По избор",
    "mic.on": "Вкл",
    "mic.off": "Изкл",
    "mic.listening": "Слуша",
    "mic.starting": "Стартиране...",
    "mic.denied": "Отказан достъп до микрофона",
    "practice.hits": "Верни",
    "practice.missed": "Пропуснати",
    "practice.wrong": "Грешни",
    "practice.accuracy": "Точност",
    "settings.title": "Изглед и упражнение",
    "settings.theme": "Тема на интерфейса",
    "settings.blocks": "Цветове на блокчетата",
    "settings.countdown": "Отброяване 3-2-1 преди старт",
    "settings.midi": "MIDI клавиатура",
    "settings.keysHint": "Клавиши: A–; свирят от C4 · W E T Y U O P са черните · Z / X сменят октавата",
    "controls.mode": "Режим",
    "mode.flow": "Поток",
    "mode.wait": "Изчакване",
    "mode.waitHint": "Режим Изчакване спира на всяка нота, докато не я изсвириш (микрофон, MIDI или клавиши).",
    "controls.metronome": "Метроном",
    "controls.loop": "Повторение",
    "loop.setA": "A",
    "loop.setB": "B",
    "loop.clear": "Изчисти повторението",
    "results.title": "Резултати от урока",
    "results.tryAgain": "Опитай пак",
    "results.close": "Затвори",
    "controls.raw": "Сурови",
    "controls.practice": "Упражнение",
    "controls.keys": "Клавиши",
    "controls.off": "Изкл.",
    "controls.all": "Всички",
    "controls.lowConfidence": "Ниска увереност",

    "delete.confirmTitle": "Изтриване",
    "delete.confirmBody": "Това ще премахне урока от запазените уроци.",
    "errors.deleteFailed": "Неуспешно изтриване на урока.",
    "errors.enterTitle": "Моля, въведи заглавие на урока.",
    "errors.chooseFile": "Моля, избери .wav или .mp3 файл.",
    "errors.enterSource": "Моля, въведи източник.",
  },
};

const PROGRESS_COPY = {
  en: {
    preparing: ["Warming up the piano engine...", "Tuning the tiny digital piano inside your browser."],
    uploading: ["Uploading your audio...", "Moving your recording into the lesson pipeline."],
    downloading: ["Downloading the performance...", "Pulling the audio track and leaving the video drama behind."],
    separating: ["Separating instruments...", "Demucs is giving the piano its own spotlight."],
    transcribing: ["Listening for notes...", "Basic Pitch is turning sound into MIDI notes."],
    analyzing: ["Analyzing harmony...", "The harmony detective is working."],
    saving: ["Saving your lesson...", "Adding this lesson to your practice shelf."],
    loading: ["Opening your lesson...", "The piano blocks are lining up."],
    done: ["Ready to play!", "The practice stage is yours."],
  },
  bg: {
    preparing: ["Подгряваме пиано двигателя...", "Настройваме малкото дигитално пиано в браузъра."],
    uploading: ["Качваме аудиото...", "Преместваме записа към lesson pipeline-а."],
    downloading: ["Сваляме изпълнението...", "Взимаме звука и оставяме видео драмата настрани."],
    separating: ["Разделяме инструментите...", "Demucs се опитва да даде собствен прожектор на пианото."],
    transcribing: ["Слушаме за ноти...", "Basic Pitch превръща звука в MIDI ноти."],
    analyzing: ["Анализираме хармонията...", "Музикалният детектив работи."],
    saving: ["Запазваме урока...", "Добавяме урока към твоята библиотека."],
    loading: ["Отваряме урока...", "Пиано блокчетата се подреждат."],
    done: ["Готово за свирене!", "Сцената за упражнение е твоя."],
  },
};

function resolveInitialLanguage() {
  try {
    const savedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY);

    if (savedLanguage === "bg" || savedLanguage === "en") {
      return savedLanguage;
    }
  } catch {
    // Ignore localStorage issues.
  }

  return "en";
}

function getCopy(language, key) {
  return UI_COPY[language]?.[key] || UI_COPY.en[key] || key;
}

function pickRandomProgressHint(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return "";
  }

  return items[Math.floor(Math.random() * items.length)];
}

function progressCopyFor(stepKey, language = "en") {
  const pair =
    PROGRESS_COPY[language]?.[stepKey] ||
    PROGRESS_COPY.en[stepKey] ||
    PROGRESS_COPY.en.preparing;

  return {
    title: pair[0],
    hint: pickRandomProgressHint(pair.slice(1)),
  };
}

function LanguageToggle({ language, onToggle }) {
  const nextLanguageLabel = language === "en" ? "BG" : "EN";

  return (
    <button
      type="button"
      className="language-toggle-button"
      onClick={onToggle}
      aria-label={language === "en" ? "Switch to Bulgarian" : "Switch to English"}
      title={language === "en" ? "Switch to Bulgarian" : "Switch to English"}
    >
      {nextLanguageLabel}
    </button>
  );
}


function midiToToneNote(midiPitch) {
  return Tone.Frequency(midiPitch, "midi").toNote();
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M4 7h16M4 12h16M4 17h16"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M4.5 19.5 8.2 18.7 18.7 8.2a2.1 2.1 0 0 0 0-3l-.9-.9a2.1 2.1 0 0 0-3 0L4.3 14.8 3.5 18.5c-.1.6.4 1.1 1 1Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="m13.7 5.4 4.9 4.9"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M5 7h14"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="M10 7V5.8C10 4.8 10.8 4 11.8 4h.4C13.2 4 14 4.8 14 5.8V7"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M7.2 9.5l.7 8.1A2.6 2.6 0 0 0 10.5 20h3a2.6 2.6 0 0 0 2.6-2.4l.7-8.1"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M10.5 12v4.5M13.5 12v4.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M4 11.5 12 5l8 6.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M6.5 10.5V20h11v-9.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M10 20v-5h4v5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function NewLessonIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect
        x="4"
        y="5"
        width="12"
        height="14"
        rx="3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.1"
      />
      <path
        d="M8 10h4M8 14h3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
      />
      <circle
        cx="17"
        cy="8"
        r="4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.1"
      />
      <path
        d="M17 6.2v3.6M15.2 8h3.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CurrentLessonIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M8 5.8v12.4c0 .8.9 1.3 1.6.8l8.6-6.2a1 1 0 0 0 0-1.6L9.6 5c-.7-.5-1.6 0-1.6.8Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.3"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SavedLessonsIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M7 7h10M7 12h10M7 17h6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.3"
        strokeLinecap="round"
      />
      <rect
        x="4"
        y="4"
        width="16"
        height="16"
        rx="3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.1"
      />
    </svg>
  );
}
function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M7 7l10 10M17 7 7 17"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function friendlyNewLessonError(error) {
  const rawMessage = String(error?.message || error || "").trim();
  const message = rawMessage || "Failed to create lesson.";
  const lowerMessage = message.toLowerCase();

  if (
    lowerMessage.includes("failed to fetch") ||
    lowerMessage.includes("networkerror") ||
    lowerMessage.includes("network error")
  ) {
    return "The app cannot reach the backend. Check that the server is running on http://127.0.0.1:8080.";
  }

  if (
    lowerMessage.includes("only public youtube") ||
    lowerMessage.includes("only youtube") ||
    lowerMessage.includes("invalid youtube") ||
    lowerMessage.includes("missing youtube url")
  ) {
    return "Please paste a valid public YouTube video link from youtube.com or youtu.be.";
  }

  if (
    lowerMessage.includes("private") ||
    lowerMessage.includes("drm") ||
    lowerMessage.includes("copyright") ||
    lowerMessage.includes("age-restricted") ||
    lowerMessage.includes("region-blocked") ||
    lowerMessage.includes("unavailable") ||
    lowerMessage.includes("sign in")
  ) {
    return "This YouTube video cannot be processed. Try another public video, or upload an MP3/WAV file instead.";
  }

  if (
    lowerMessage.includes("too large") ||
    lowerMessage.includes("80 mb")
  ) {
    return "This audio file is too large. Please upload an MP3 or WAV file up to 80 MB.";
  }

  if (
    lowerMessage.includes("unsupported audio") ||
    lowerMessage.includes("unsupported file") ||
    lowerMessage.includes(".wav or .mp3") ||
    lowerMessage.includes(".mp3 or .wav")
  ) {
    return "Unsupported audio file. Please upload a .mp3 or .wav file.";
  }

  if (
    lowerMessage.includes("timed out") ||
    lowerMessage.includes("timeout")
  ) {
    return "This took too long. Try a shorter audio file, or turn source separation off.";
  }

  if (
    lowerMessage.includes("source separation") ||
    lowerMessage.includes("demucs")
  ) {
    return "Source separation failed. Try creating the lesson again with “Use source separation” turned off.";
  }

  if (
    lowerMessage.includes("basic_pitch") ||
    lowerMessage.includes("basic pitch") ||
    lowerMessage.includes("transcription")
  ) {
    return "The AI could not transcribe this audio clearly. Try a cleaner piano recording or a shorter clip.";
  }

  if (
    lowerMessage.includes("ffmpeg") ||
    lowerMessage.includes("conversion")
  ) {
    return "The audio could not be converted. Try another YouTube video or upload an MP3/WAV file.";
  }

  if (
    lowerMessage.includes("no such option") ||
    lowerMessage.includes("yt-dlp")
  ) {
    return "The YouTube downloader is not configured correctly. Restart the backend and check yt-dlp inside Docker.";
  }

  return message;
}

function formatPlaybackTime(seconds = 0) {
  const safeSeconds = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safeSeconds / 60);
  const remainingSeconds = Math.floor(safeSeconds % 60);

  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}



/*
 * Common keyboard models with their factory key ranges.
 * Sources: manufacturer spec sheets (Casio SA-76: 44 keys F2-C6;
 * Yamaha 76-key portables: E1-G7; 61-key portables: C2-C7;
 * 49-key controllers: C3-C7; full pianos: A0-C8).
 */
const KEYBOARD_MODELS = [
  { id: "acoustic", label: "Acoustic piano", keys: 88, low: 21, high: 108 },
  { id: "yamaha-p45", label: "Yamaha P-45 / P-125", keys: 88, low: 21, high: 108 },
  { id: "casio-cdp", label: "Casio CDP-S110 / PX-770", keys: 88, low: 21, high: 108 },
  { id: "roland-fp", label: "Roland FP-10 / FP-30X", keys: 88, low: 21, high: 108 },
  { id: "kawai-es", label: "Kawai ES120", keys: 88, low: 21, high: 108 },
  { id: "yamaha-ew310", label: "Yamaha PSR-EW310 / EW425", keys: 76, low: 28, high: 103 },
  { id: "casio-wk", label: "Casio WK-6600", keys: 76, low: 28, high: 103 },
  { id: "yamaha-e373", label: "Yamaha PSR-E373 / E473", keys: 61, low: 36, high: 96 },
  { id: "casio-cts", label: "Casio CT-S300 / CT-X700", keys: 61, low: 36, high: 96 },
  { id: "korg-ek50", label: "Korg EK-50", keys: 61, low: 36, high: 96 },
  { id: "keystation-49", label: "M-Audio Keystation 49 (MIDI)", keys: 49, low: 48, high: 96 },
  { id: "casio-sa76", label: "Casio SA-76 / SA-81", keys: 44, low: 41, high: 84 },
  { id: "casio-sa46", label: "Casio SA-46 / SA-50", keys: 32, low: 53, high: 84 },
];

const PIANO_RANGE_PRESETS = [
  { id: "88", label: "88", low: 21, high: 108 },
  { id: "76", label: "76", low: 28, high: 103 },
  { id: "61", label: "61", low: 36, high: 96 },
  { id: "49", label: "49", low: 48, high: 96 },
  { id: "44", label: "44", low: 41, high: 84 },
  { id: "37", label: "37", low: 48, high: 84 },
  { id: "32", label: "32", low: 53, high: 84 },
];

const PIANO_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

function midiNoteLabel(midi) {
  const name = PIANO_NOTE_NAMES[((midi % 12) + 12) % 12];
  const octave = Math.floor(midi / 12) - 1;
  return `${name}${octave}`;
}

function loadStoredPianoRange() {
  try {
    const low = parseInt(localStorage.getItem("daitune-piano-low"), 10);
    const high = parseInt(localStorage.getItem("daitune-piano-high"), 10);

    if (Number.isFinite(low) && Number.isFinite(high) && high - low >= 12) {
      return { low, high };
    }
  } catch {
    /* ignore */
  }

  return { low: 36, high: 84 };
}

function App() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [tempo, setTempo] = useState(1);
  const [noteDisplayMode, setNoteDisplayMode] = useState("letters");
  const [noteViewMode, setNoteViewMode] = useState("practice");
  const [keyboardLabelMode, setKeyboardLabelMode] = useState("c-only");
  const [viewMode, setViewMode] = useState("blocks");
  const [activeHand, setActiveHand] = React.useState("both");
  const [currentLessonJobId, setCurrentLessonJobId] = useState(DEFAULT_LESSON_JOB_ID);
  const [pipelineRuns, setPipelineRuns] = useState([]);
  const [screenMode, setScreenMode] = useState("home");
  const [isSessionsOpen, setIsSessionsOpen] = useState(false);
  const [titleOverrides, setTitleOverrides] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("lessonTitleOverrides") || "{}");
    } catch {
      return {};
    }
  });
  const [lesson, setLesson] = useState(null);
  const [lessonNotes, setLessonNotes] = useState(demoNotes);
  const [lessonLoadStatus, setLessonLoadStatus] = useState("loading");
  const [isNewLessonOpen, setIsNewLessonOpen] = useState(false);
  const [newLessonTitle, setNewLessonTitle] = useState("");
  const [newLessonTitleSource, setNewLessonTitleSource] = useState("auto");
  const [newLessonSourceType, setNewLessonSourceType] = useState("youtube");
  const [newLessonFile, setNewLessonFile] = useState(null);
  const [newLessonSource, setNewLessonSource] = useState("");
  const [newLessonStatus, setNewLessonStatus] = useState("idle");
  const [newLessonError, setNewLessonError] = useState("");
  const [newLessonStep, setNewLessonStep] = useState("");
  const [newLessonHint, setNewLessonHint] = useState("");
  const [language, setLanguage] = useState(resolveInitialLanguage);

  // Live practice (microphone) state
  const [isMicEnabled, setIsMicEnabled] = useState(false);
  const [micStatus, setMicStatus] = useState("idle");
  const [detectedMidi, setDetectedMidi] = useState(null);
  const [noteJudgements, setNoteJudgements] = useState({});
  const [wrongFlashes, setWrongFlashes] = useState([]);
  const [wrongCount, setWrongCount] = useState(0);

  // Appearance
  const [uiThemeId, setUiThemeId] = useState(loadStoredUiThemeId);
  const [blockPaletteId, setBlockPaletteId] = useState(loadStoredBlockPaletteId);
  const [pianoRange, setPianoRange] = useState(loadStoredPianoRange);
  const [fitToRange, setFitToRange] = useState(() => {
    try {
      return localStorage.getItem("daitune-fit-range") !== "0";
    } catch {
      return true;
    }
  });
  const [hideLowConfidence, setHideLowConfidence] = useState(() => {
    try {
      return localStorage.getItem("daitune-hide-lowconf") === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("daitune-hide-lowconf", hideLowConfidence ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [hideLowConfidence]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Practice tools
  const [playMode, setPlayMode] = useState("flow"); // "flow" | "wait"
  const [metronomeOn, setMetronomeOn] = useState(false);
  const [metronomeBpm, setMetronomeBpm] = useState(90);
  const [loopRegion, setLoopRegion] = useState(null); // { a, b } musical seconds
  const [countdown, setCountdown] = useState(null);
  const [countdownEnabled, setCountdownEnabled] = useState(() => {
    try {
      return localStorage.getItem("daitune-countdown") !== "0";
    } catch {
      return true;
    }
  });
  const [showResults, setShowResults] = useState(null);
  const [progressSummaries, setProgressSummaries] = useState({});
  const [coachState, setCoachState] = useState({ status: "idle", plan: null });

  const openCoach = React.useCallback(
    async (delayMs = 0) => {
      const jobId = currentLessonJobIdRef.current;
      if (!jobId) return;

      setCoachState({ status: "loading", plan: null });

      if (delayMs > 0) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }

      try {
        const result = await requestCoachPlan(jobId, language);

        if (result.status === "ok" && result.plan) {
          setCoachState({ status: "ready", plan: result.plan });
        } else {
          setCoachState({ status: "empty", plan: null });
        }
      } catch {
        setCoachState({ status: "error", plan: null });
      }
    },
    [language]
  );

  const seekToMusicalTimeRef = useRef(() => {});

  const applyCoachSection = React.useCallback((section) => {
    setLoopRegion({ a: section.start, b: section.end });
    setTempo(section.tempo);
    setActiveHand(
      section.hand === "left" || section.hand === "right" ? section.hand : "both"
    );
    seekToMusicalTimeRef.current(section.start);
    setCoachState({ status: "idle", plan: null });
  }, []);

  const refreshProgressSummaries = React.useCallback(async () => {
    try {
      setProgressSummaries(await fetchProgressSummary());
    } catch {
      /* backend offline – badges just stay hidden */
    }
  }, []);

  useEffect(() => {
    refreshProgressSummaries();
  }, [refreshProgressSummaries]);
  const [midiStatus, setMidiStatus] = useState("off");

  useEffect(() => {
    applyUiTheme(uiThemeId);
  }, [uiThemeId]);

  useEffect(() => {
    applyBlockPalette(blockPaletteId);
  }, [blockPaletteId]);

  useEffect(() => {
    try {
      localStorage.setItem("daitune-piano-low", String(pianoRange.low));
      localStorage.setItem("daitune-piano-high", String(pianoRange.high));
    } catch {
      /* ignore */
    }
  }, [pianoRange]);

  useEffect(() => {
    try {
      localStorage.setItem("daitune-fit-range", fitToRange ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [fitToRange]);

  useEffect(() => {
    try {
      localStorage.setItem("daitune-countdown", countdownEnabled ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [countdownEnabled]);

  const uiTheme = React.useMemo(() => getUiTheme(uiThemeId), [uiThemeId]);
  const blockPalette = React.useMemo(
    () => getBlockPalette(blockPaletteId),
    [blockPaletteId]
  );

  const canvasPalette = React.useMemo(
    () => ({ leftHand: blockPalette.left, rightHand: blockPalette.right }),
    [blockPalette]
  );

  const sheetPalette = React.useMemo(
    () => ({
      left: buildSheetHand(blockPalette.left),
      right: buildSheetHand(blockPalette.right),
    }),
    [blockPalette]
  );

  const t = React.useCallback(
    (key) => getCopy(language, key),
    [language]
  );

  const toggleLanguage = React.useCallback(() => {
    setLanguage((currentLanguage) => (currentLanguage === "en" ? "bg" : "en"));
  }, []);

  const lessonMeta = lesson?.meta ?? {};
  const lessonDurationSeconds =
    Number(lessonMeta.duration_s) ||
    Math.max(...lessonNotes.map((note) => Number(note.end ?? 0)), FALLBACK_DURATION_SECONDS);

  const activePipelineRun = pipelineRuns.find(
    (run) => run.job_id === currentLessonJobId
  );

  const latestPipelineRun = pipelineRuns[0] ?? null;

  const lessonTitle =
    titleOverrides[currentLessonJobId] ||
    lessonMeta.title ||
    activePipelineRun?.session_title ||
    "Morning Light";
  const lessonSubtitle = lesson
    ? `${lessonMeta.transcription_method || "Demo lesson"} · ${lessonMeta.detected_key || "Unknown key"} · ${lessonMeta.time_signature || "4/4"}`
    : "Demo lesson · C Major · 4/4";

  const musicalTime = currentTime * tempo;

  const lessonDuration = React.useMemo(() => {
    return lessonNotes.reduce((maxEnd, note) => {
      const noteEnd = Number(note.end ?? note.start ?? 0);

      if (!Number.isFinite(noteEnd)) {
        return maxEnd;
      }

      return Math.max(maxEnd, noteEnd);
    }, 0);
  }, [lessonNotes]);

  const seekToMusicalTime = React.useCallback(
    (targetMusicalTime) => {
      const safeTempo = Math.max(0.01, Number(tempo) || 1);

      const clampedMusicalTime =
        lessonDuration > 0
          ? Math.min(Math.max(Number(targetMusicalTime) || 0, 0), lessonDuration)
          : Math.max(Number(targetMusicalTime) || 0, 0);
      triggeredNotesRef.current.clear();
      lastFrameRef.current = null;

      judgementsRef.current = {};
      setNoteJudgements({});
      setWrongFlashes([]);
      setWrongCount(0);

      setCurrentTime(clampedMusicalTime / safeTempo);
    },
    [lessonDuration, tempo]
  );

  const scrubberProgressPercent =
    lessonDuration > 0
      ? Math.min(100, Math.max(0, (musicalTime / lessonDuration) * 100))
      : 0;

  const lessonKeyPitchClasses = React.useMemo(
    () => parseKeySignature(lesson?.meta?.detected_key),
    [lesson]
  );

  const playableLessonNotes = React.useMemo(() => {
    if (noteViewMode === "raw") {
      return lessonNotes;
    }

    return buildPlayableNotes(lessonNotes, noteViewMode, {
      keyPitchClasses: lessonKeyPitchClasses,
    });
  }, [lessonNotes, noteViewMode, lessonKeyPitchClasses]);

  const rangedLessonNotes = React.useMemo(() => {
    if (!fitToRange) {
      return playableLessonNotes;
    }

    return fitNotesToRange(playableLessonNotes, pianoRange.low, pianoRange.high);
  }, [playableLessonNotes, fitToRange, pianoRange]);

  const confidenceFilteredNotes = React.useMemo(() => {
    if (!hideLowConfidence) {
      return rangedLessonNotes;
    }

    return rangedLessonNotes.filter((note) => {
      if (note.confidence === null || note.confidence === undefined) {
        return true; // unknown confidence is not "weak"
      }

      return confidenceLevel(note.confidence) !== "low";
    });
  }, [rangedLessonNotes, hideLowConfidence]);

  const hiddenLowConfidenceCount =
    rangedLessonNotes.length - confidenceFilteredNotes.length;

  const visibleLessonNotes = React.useMemo(() => {
    return confidenceFilteredNotes.filter((note) => {
      if (activeHand === "both") return true;
      return note.hand === activeHand;
    });
  }, [confidenceFilteredNotes, activeHand]);

  const reviewNoteCount = lessonNotes.filter(
    (note) => note.inCorrectionMask || note.in_correction_mask
  ).length;

  const unknownConfidenceCount = lessonNotes.filter(
    (note) => note.confidence === null || note.confidence === undefined
  ).length;
  const [useSourceSeparation, setUseSourceSeparation] = React.useState(false);
  const [isAudioPreprocessOpen, setIsAudioPreprocessOpen] = React.useState(false);
  const [audioPreprocessOptions, setAudioPreprocessOptions] = React.useState({
    trim_silence: true,
    normalize_audio: true,
    highpass_filter: true,
  });

  const isAnyAudioPreprocessingEnabled =
    audioPreprocessOptions.trim_silence ||
    audioPreprocessOptions.normalize_audio ||
    audioPreprocessOptions.highpass_filter;

  const areAllAudioPreprocessingOptionsEnabled =
    audioPreprocessOptions.trim_silence &&
    audioPreprocessOptions.normalize_audio &&
    audioPreprocessOptions.highpass_filter;
  function toggleAudioPreprocessOption(optionName) {
    setAudioPreprocessOptions((currentOptions) => ({
      ...currentOptions,
      [optionName]: !currentOptions[optionName],
    }));
  }

  function toggleAudioPreprocessingEnabled() {
    setAudioPreprocessOptions((currentOptions) => {
      const areAllEnabled =
        currentOptions.trim_silence &&
        currentOptions.normalize_audio &&
        currentOptions.highpass_filter;

      const nextValue = !areAllEnabled;

      return {
        trim_silence: nextValue,
        normalize_audio: nextValue,
        highpass_filter: nextValue,
      };
    });
  }
  const lastFrameRef = useRef(null);
  const synthRef = useRef(null);
  const metronomeSynthRef = useRef(null);
  const triggeredNotesRef = useRef(new Set());
  useEffect(() => {
      localStorage.setItem("lessonTitleOverrides", JSON.stringify(titleOverrides));
    }, [titleOverrides]);

  useEffect(() => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  }, [language]);

    useEffect(() => {
    let cancelled = false;

    async function loadPipelineRuns() {
      try {
        const runs = await fetchPipelineRuns(20);

        if (cancelled) return;

        setPipelineRuns(dedupeRunsByJobId(runs));
      } catch (error) {
        console.warn("Failed to load saved lessons:", error);
      }
    }

    loadPipelineRuns();

    return () => {
      cancelled = true;
    };
  }, []);

  // useEffect(() => {
  //   const reverb = new Tone.Reverb({
  //   decay: 3.2,
  //   wet: 0.26,
  // }).toDestination();

  // const compressor = new Tone.Compressor({
  //   threshold: -20,
  //   ratio: 2.6,
  //   attack: 0.035,
  //   release: 0.32,
  // }).connect(reverb);

  // const gain = new Tone.Gain(0.68).connect(compressor);

  // synthRef.current = new Tone.PolySynth(Tone.Synth, {
  //   maxPolyphony: 64,
  //   oscillator: {
  //     type: "triangle8",
  //   },
  //   envelope: {
  //     attack: 0.015,
  //     decay: 0.28,
  //     sustain: 0.28,
  //     release: 1.6,
  //   },
  // }).connect(gain);

  //   return () => {
  //     synthRef.current?.dispose();
  //   };
  // }, []);

  useEffect(() => {
    const reverb = new Tone.Reverb({
      decay: 3.6,
      wet: 0.18,
    }).toDestination();

    const compressor = new Tone.Compressor({
      threshold: -20,
      ratio: 2.4,
      attack: 0.035,
      release: 0.32,
    }).connect(reverb);

    const gain = new Tone.Gain(0.82).connect(compressor);

    const fallbackSynth = new Tone.PolySynth(Tone.Synth, {
      maxPolyphony: 64,
      oscillator: {
        type: "triangle8",
      },
      envelope: {
        attack: 0.015,
        decay: 0.28,
        sustain: 0.28,
        release: 1.6,
      },
    }).connect(gain);

    const pianoSampler = new Tone.Sampler({
      urls: {
        A0: "A0.mp3",
        C1: "C1.mp3",
        "D#1": "Ds1.mp3",
        "F#1": "Fs1.mp3",
        A1: "A1.mp3",
        C2: "C2.mp3",
        "D#2": "Ds2.mp3",
        "F#2": "Fs2.mp3",
        A2: "A2.mp3",
        C3: "C3.mp3",
        "D#3": "Ds3.mp3",
        "F#3": "Fs3.mp3",
        A3: "A3.mp3",
        C4: "C4.mp3",
        "D#4": "Ds4.mp3",
        "F#4": "Fs4.mp3",
        A4: "A4.mp3",
        C5: "C5.mp3",
        "D#5": "Ds5.mp3",
        "F#5": "Fs5.mp3",
        A5: "A5.mp3",
        C6: "C6.mp3",
        "D#6": "Ds6.mp3",
        "F#6": "Fs6.mp3",
        A6: "A6.mp3",
        C7: "C7.mp3",
        "D#7": "Ds7.mp3",
        "F#7": "Fs7.mp3",
        A7: "A7.mp3",
        C8: "C8.mp3",
      },
      baseUrl: "/samples/piano/",
      release: 1.4,
      onload: () => {
        synthRef.current = pianoSampler;
        fallbackSynth.dispose();
      },
    }).connect(gain);

    synthRef.current = fallbackSynth;

    const metronomeSynth = new Tone.Synth({
      oscillator: { type: "square" },
      envelope: { attack: 0.001, decay: 0.05, sustain: 0, release: 0.03 },
      volume: -10,
    }).connect(gain);

    metronomeSynthRef.current = metronomeSynth;

    return () => {
      metronomeSynth.dispose();
      metronomeSynthRef.current = null;
      pianoSampler.dispose();
      fallbackSynth.dispose();
      gain.dispose();
      compressor.dispose();
      reverb.dispose();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadLesson() {
      try {
        const loadedLesson = await fetchLesson(currentLessonJobId);

        if (cancelled) return;

        setLesson(loadedLesson);
        setLessonNotes(mapLessonNotesToUiNotes(loadedLesson.notes));
        setLessonLoadStatus("loaded");
        lastFrameRef.current = null;
        triggeredNotesRef.current.clear();
        resetPracticeScoring();
        setIsPlaying(false);
        setCurrentTime(0);

        restoreLessonState(
          currentLessonJobId,
          Number(loadedLesson?.meta?.duration_seconds) ||
            Number(loadedLesson?.duration_seconds) ||
            9999
        );
      } catch (error) {
        if (cancelled) return;

        console.warn("Using demoNotes fallback because lesson fetch failed:", error);
        setLesson(null);
        setLessonNotes(demoNotes);
        setLessonLoadStatus("fallback");
      }
    }

    loadLesson();

    return () => {
      cancelled = true;
    };
  }, [currentLessonJobId]);

  useEffect(() => {
    seekToMusicalTimeRef.current = seekToMusicalTime;
  }, [seekToMusicalTime]);

  /* ---------------- Live practice: scoring against the lesson ------------- */

  const HIT_WINDOW_EARLY_SECONDS = 0.35;
  const HIT_WINDOW_LATE_SECONDS = 0.25;
  const ALLOW_OCTAVE_TOLERANCE = true;

  const musicalTimeRef = useRef(0);
  const isPlayingRef = useRef(false);
  const visibleNotesRef = useRef(visibleLessonNotes);
  const judgementsRef = useRef({});
  const wrongEventsRef = useRef([]);
  const detectorRef = useRef(null);

  useEffect(() => {
    musicalTimeRef.current = musicalTime;
  }, [musicalTime]);

  useEffect(() => {
    isPlayingRef.current = isPlaying;
  }, [isPlaying]);

  useEffect(() => {
    visibleNotesRef.current = visibleLessonNotes;
  }, [visibleLessonNotes]);

  const resetPracticeScoring = React.useCallback(() => {
    judgementsRef.current = {};
    wrongEventsRef.current = [];
    setNoteJudgements({});
    setWrongFlashes([]);
    setWrongCount(0);
  }, []);

  const registerWrongNote = React.useCallback((midi) => {
    setWrongCount((count) => count + 1);

    if (wrongEventsRef.current.length < 300) {
      wrongEventsRef.current.push({
        t: musicalTimeRef.current,
        pitch: midi,
        kind: "wrong",
      });
    }

    const flashId = `${midi}-${Date.now()}`;
    setWrongFlashes((flashes) => [...flashes, { id: flashId, pitch: midi }]);

    setTimeout(() => {
      setWrongFlashes((flashes) =>
        flashes.filter((flash) => flash.id !== flashId)
      );
    }, 450);
  }, []);

  const handleDetectedNoteOn = React.useCallback(
    (midi) => {
      // Score only while the lesson is actually running.
      if (!isPlayingRef.current) return;

      const currentMusicalTime = musicalTimeRef.current;
      const judgements = judgementsRef.current;

      let exactMatch = null;
      let octaveMatch = null;

      for (const note of visibleNotesRef.current) {
        if (judgements[note.id]) continue;

        const windowStart = Number(note.start) - HIT_WINDOW_EARLY_SECONDS;
        const windowEnd = Number(note.end) + HIT_WINDOW_LATE_SECONDS;

        if (currentMusicalTime < windowStart || currentMusicalTime > windowEnd) {
          continue;
        }

        const distance = Math.abs(Number(note.pitch) - midi);

        if (distance === 0 && !exactMatch) {
          exactMatch = note;
          break;
        }

        if (ALLOW_OCTAVE_TOLERANCE && distance === 12 && !octaveMatch) {
          octaveMatch = note;
        }
      }

      const matched = exactMatch || octaveMatch;

      if (matched) {
        const next = { ...judgementsRef.current, [matched.id]: "hit" };
        judgementsRef.current = next;
        setNoteJudgements(next);
      } else {
        registerWrongNote(midi);
      }
    },
    [registerWrongNote]
  );

  const handleDetectedNoteOnRef = useRef(handleDetectedNoteOn);

  useEffect(() => {
    handleDetectedNoteOnRef.current = handleDetectedNoteOn;
  }, [handleDetectedNoteOn]);

  // Microphone lifecycle.
  useEffect(() => {
    if (!isMicEnabled) return undefined;

    let disposed = false;

    resetPracticeScoring();

    const detector = createMicPitchDetector({
      onStatus: (status) => {
        if (!disposed) setMicStatus(status);
      },
      onPitch: (frame) => {
        if (!disposed) setDetectedMidi(frame.midi);
      },
      onSilence: () => {
        if (!disposed) setDetectedMidi(null);
      },
      onNoteOn: (midi) => {
        if (!disposed) handleDetectedNoteOnRef.current(midi);
      },
    });

    detectorRef.current = detector;

    detector.start().catch(() => {
      if (!disposed) {
        setMicStatus("denied");
        setIsMicEnabled(false);
      }
    });

    return () => {
      disposed = true;
      detector.stop();
      detectorRef.current = null;
      setDetectedMidi(null);
      setMicStatus("idle");
    };
  }, [isMicEnabled, resetPracticeScoring]);

  // Missed-note sweep: notes whose window passed without a hit.
  useEffect(() => {
    if (!isMicEnabled) return undefined;

    const timer = setInterval(() => {
      if (!isPlayingRef.current) return;

      const currentMusicalTime = musicalTimeRef.current;
      const judgements = judgementsRef.current;
      let changed = false;
      const next = { ...judgements };

      if (playModeRef.current === "wait") return;

      for (const note of visibleNotesRef.current) {
        if (next[note.id]) continue;

        if (Number(note.end) + HIT_WINDOW_LATE_SECONDS < currentMusicalTime) {
          next[note.id] = "miss";
          changed = true;
        }
      }

      if (changed) {
        judgementsRef.current = next;
        setNoteJudgements(next);
      }
    }, 180);

    return () => clearInterval(timer);
  }, [isMicEnabled]);

  const practiceStats = React.useMemo(() => {
    let hits = 0;
    let missed = 0;

    for (const status of Object.values(noteJudgements)) {
      if (status === "hit") hits += 1;
      if (status === "miss") missed += 1;
    }

    const attempted = hits + missed + wrongCount;
    const accuracy = attempted > 0 ? Math.round((hits / attempted) * 100) : null;

    return { hits, missed, wrong: wrongCount, accuracy };
  }, [noteJudgements, wrongCount]);

  const wrongPitchSet = React.useMemo(
    () => new Set(wrongFlashes.map((flash) => flash.pitch)),
    [wrongFlashes]
  );

  /* --------------- Practice tools: wait mode, loop, metronome -------------- */

  const playModeRef = useRef(playMode);
  const loopRegionRef = useRef(loopRegion);
  const metronomeOnRef = useRef(metronomeOn);
  const metronomeBpmRef = useRef(metronomeBpm);
  const wrongCountRef = useRef(0);
  const screenModeRef = useRef(screenMode);
  const countdownTokenRef = useRef(0);

  /* Per-lesson session memory: position + player settings, local-first. */
  const lessonStateKey = (jobId) => `daitune-lesson-state:${jobId}`;

  const persistLessonState = React.useCallback(() => {
    const jobId = currentLessonJobIdRef.current;
    if (!jobId) return;

    try {
      localStorage.setItem(
        lessonStateKey(jobId),
        JSON.stringify({
          t: musicalTimeRef.current,
          tempo,
          hand: activeHand,
          view: noteViewMode,
          hideWeak: hideLowConfidence,
        })
      );
    } catch {
      /* ignore */
    }

    saveLessonPosition(jobId, musicalTimeRef.current, noteViewMode).catch(() => {});
  }, [tempo, activeHand, noteViewMode, hideLowConfidence]);

  const persistLessonStateRef = useRef(persistLessonState);

  useEffect(() => {
    persistLessonStateRef.current = persistLessonState;
  }, [persistLessonState]);

  // Save settings whenever they change, and position every few seconds while playing.
  useEffect(() => {
    persistLessonStateRef.current();
  }, [tempo, activeHand, noteViewMode, hideLowConfidence, persistLessonState]);

  useEffect(() => {
    if (!isPlaying) {
      persistLessonStateRef.current();
      return undefined;
    }

    const timer = setInterval(() => persistLessonStateRef.current(), 4000);
    return () => clearInterval(timer);
  }, [isPlaying]);

  const restoreLessonState = React.useCallback((jobId, durationSeconds) => {
    try {
      const raw = localStorage.getItem(lessonStateKey(jobId));

      if (!raw) {
        const remote = progressSummariesRef.current[jobId];
        const remoteT = Number(remote?.last_position_seconds);

        if (remoteT > 2 && remoteT < durationSeconds - 2) {
          setCurrentTime(remoteT);
        }
        if (["raw", "practice", "beginner"].includes(remote?.last_note_view)) {
          setNoteViewMode(remote.last_note_view);
        }
        return;
      }

      const saved = JSON.parse(raw);

      if (typeof saved.tempo === "number") setTempo(saved.tempo);
      if (saved.hand === "left" || saved.hand === "right" || saved.hand === "both") {
        setActiveHand(saved.hand);
      }
      if (["raw", "practice", "beginner"].includes(saved.view)) {
        setNoteViewMode(saved.view);
      }
      if (typeof saved.hideWeak === "boolean") setHideLowConfidence(saved.hideWeak);

      const safeTempo = typeof saved.tempo === "number" && saved.tempo > 0 ? saved.tempo : 1;
      if (
        typeof saved.t === "number" &&
        saved.t > 2 &&
        saved.t < durationSeconds - 2
      ) {
        setCurrentTime(saved.t / safeTempo);
      }
    } catch {
      /* ignore */
    }
  }, []);
  const currentLessonJobIdRef = useRef(null);
  const noteViewModeRef = useRef("practice");
  const refreshProgressSummariesRef = useRef(() => {});
  const progressSummariesRef = useRef({});

  useEffect(() => {
    progressSummariesRef.current = progressSummaries;
  }, [progressSummaries]);

  useEffect(() => {
    currentLessonJobIdRef.current = currentLessonJobId;
  }, [currentLessonJobId]);

  useEffect(() => {
    noteViewModeRef.current = noteViewMode;
  }, [noteViewMode]);

  useEffect(() => {
    refreshProgressSummariesRef.current = refreshProgressSummaries;
  }, [refreshProgressSummaries]);

  useEffect(() => {
    playModeRef.current = playMode;
  }, [playMode]);

  useEffect(() => {
    loopRegionRef.current = loopRegion;
  }, [loopRegion]);

  useEffect(() => {
    metronomeOnRef.current = metronomeOn;
  }, [metronomeOn]);

  useEffect(() => {
    metronomeBpmRef.current = metronomeBpm;
  }, [metronomeBpm]);

  useEffect(() => {
    wrongCountRef.current = wrongCount;
  }, [wrongCount]);

  useEffect(() => {
    screenModeRef.current = screenMode;
  }, [screenMode]);

  function playMetronomeClick(isAccent) {
    const metronome = metronomeSynthRef.current;
    if (!metronome) return;

    try {
      metronome.triggerAttackRelease(isAccent ? "C6" : "G5", 0.03);
    } catch {
      /* audio not started yet */
    }
  }

  const buildResultsSummary = React.useCallback(() => {
    let hits = 0;
    let missed = 0;

    for (const status of Object.values(judgementsRef.current)) {
      if (status === "hit") hits += 1;
      if (status === "miss") missed += 1;
    }

    const wrong = wrongCountRef.current;
    const attempted = hits + missed + wrong;

    if (attempted === 0) return null;

    const accuracy = Math.round((hits / attempted) * 100);
    const stars = accuracy >= 88 ? 3 : accuracy >= 65 ? 2 : accuracy >= 35 ? 1 : 0;

    return { hits, missed, wrong, accuracy, stars };
  }, []);

  // Live sound + scoring for MIDI keyboards and computer keys.
  const handleLiveNoteOn = React.useCallback((midi, velocity = 92) => {
    setDetectedMidi(midi);

    const synth = synthRef.current;

    if (synth) {
      try {
        synth.triggerAttack(
          midiToToneNote(midi),
          undefined,
          Math.min(0.95, Math.max(0.2, velocity / 127))
        );
      } catch {
        /* sampler still loading */
      }
    }

    handleDetectedNoteOnRef.current(midi);
  }, []);

  const handleLiveNoteOff = React.useCallback((midi) => {
    setDetectedMidi((current) => (current === midi ? null : current));

    const synth = synthRef.current;

    if (synth && typeof synth.triggerRelease === "function") {
      try {
        synth.triggerRelease(midiToToneNote(midi));
      } catch {
        /* ignore */
      }
    }
  }, []);

  // Computer keyboard piano – active on the lesson screen.
  useEffect(() => {
    if (screenMode !== "lesson") return undefined;

    const detach = attachComputerKeyboardPiano({
      onNoteOn: handleLiveNoteOn,
      onNoteOff: handleLiveNoteOff,
    });

    return detach;
  }, [screenMode, handleLiveNoteOn, handleLiveNoteOff]);

  // MIDI keyboard – connects automatically when available.
  useEffect(() => {
    const midi = createMidiInput({
      onNoteOn: handleLiveNoteOn,
      onNoteOff: handleLiveNoteOff,
      onStatus: setMidiStatus,
    });

    midi.start();

    return () => midi.stop();
  }, [handleLiveNoteOn, handleLiveNoteOff]);

  function setLoopPointA() {
    const a = musicalTimeRef.current;

    setLoopRegion((region) => {
      if (region && region.b !== null && region.b > a) {
        return { a, b: region.b };
      }
      return { a, b: null };
    });
  }

  function setLoopPointB() {
    const b = musicalTimeRef.current;

    setLoopRegion((region) => {
      const a = region?.a ?? 0;
      if (b <= a + 0.4) return region;
      return { a, b };
    });
  }

  function clearLoop() {
    setLoopRegion(null);
  }

  /* ------------------------------------------------------------------------ */

  function triggerNotesBetween(previousMusicalTime, nextMusicalTime) {
    const synth = synthRef.current;

    if (!synth) return;

    for (const note of visibleLessonNotes) {
      const alreadyTriggered = triggeredNotesRef.current.has(note.id);
      const isInWindow =
        note.start >= previousMusicalTime && note.start < nextMusicalTime;

      if (!alreadyTriggered && isInWindow) {
          const duration = Math.max((note.end - note.start) / tempo, 0.08);

          const normalizedVelocity = Math.min(
            0.95,
            Math.max(0.22, (note.velocity ?? 72) / 127)
          );

          const confidenceWeight =
            note.confidence === null || note.confidence === undefined
              ? 0.85
              : Math.min(1, Math.max(0.45, note.confidence));

          const expressiveVelocity = Math.pow(
            normalizedVelocity * confidenceWeight,
            0.82
          );

          synth.triggerAttackRelease(
            midiToToneNote(note.pitch),
            duration,
            undefined,
            expressiveVelocity
          );

          triggeredNotesRef.current.add(note.id);
        }
    }
  }

  useEffect(() => {
    let frameId;

    function tick(timestamp) {
      if (lastFrameRef.current === null) {
        lastFrameRef.current = timestamp;
      }

      const deltaSeconds = (timestamp - lastFrameRef.current) / 1000;
      lastFrameRef.current = timestamp;

      if (isPlaying) {
        setCurrentTime((time) => {
          let next = time + deltaSeconds;

          const previousMusicalTime = time * tempo;
          let nextMusicalTime = next * tempo;

          // Wait mode: freeze on every unplayed note until the learner
          // plays it (via mic, MIDI keyboard or computer keys).
          if (playModeRef.current === "wait") {
            let earliestPending = null;

            for (const note of visibleNotesRef.current) {
              if (judgementsRef.current[note.id]) continue;

              const noteStart = Number(note.start);

              if (
                noteStart <= nextMusicalTime &&
                (earliestPending === null || noteStart < earliestPending)
              ) {
                earliestPending = noteStart;
              }
            }

            if (
              earliestPending !== null &&
              nextMusicalTime > earliestPending + 0.02
            ) {
              nextMusicalTime = earliestPending + 0.02;
              next = nextMusicalTime / tempo;
            }
          } else {
            triggerNotesBetween(previousMusicalTime, nextMusicalTime);
          }

          // Metronome clicks on beat boundaries (accent every 4th beat).
          if (metronomeOnRef.current && nextMusicalTime > previousMusicalTime) {
            const beatSeconds = 60 / Math.max(30, metronomeBpmRef.current);
            const previousBeat = Math.floor(previousMusicalTime / beatSeconds);
            const nextBeat = Math.floor(nextMusicalTime / beatSeconds);

            if (nextBeat > previousBeat) {
              playMetronomeClick(nextBeat % 4 === 0);
            }
          }

          // A-B loop: wrap back and restart the section cleanly.
          const loop = loopRegionRef.current;

          if (loop && loop.b !== null && nextMusicalTime >= loop.b) {
            triggeredNotesRef.current.clear();
            judgementsRef.current = {};
            setNoteJudgements({});
            return loop.a / tempo;
          }

          if (next >= lessonDurationSeconds / tempo) {
            setIsPlaying(false);
            triggeredNotesRef.current.clear();

            const summary = buildResultsSummary();
            if (summary) {
              setShowResults(summary);

              const jobId = currentLessonJobIdRef.current;
              if (jobId) {
                const weakSpots = [];

                for (const [noteId, status] of Object.entries(judgementsRef.current)) {
                  if (status !== "miss") continue;
                  const note = visibleNotesRef.current.find((n) => n.id === noteId);
                  if (!note) continue;

                  weakSpots.push({
                    start: Number(note.start),
                    end: Number(note.end),
                    hand: note.hand === "left" || note.hand === "right" ? note.hand : null,
                    kind: "miss",
                  });
                }

                for (const event of wrongEventsRef.current) {
                  weakSpots.push({ start: event.t, end: event.t, kind: "wrong" });
                }

                weakSpots.sort((a, b) => a.start - b.start);

                const payload = {
                  job_id: jobId,
                  weak_spots: weakSpots.slice(0, 200),
                  hits: summary.hits,
                  missed: summary.missed,
                  wrong: summary.wrong,
                  accuracy: summary.accuracy,
                  stars: summary.stars,
                  mode: playModeRef.current,
                  note_view: noteViewModeRef.current,
                  tempo,
                  duration_seconds: lessonDurationSeconds,
                };

                setTimeout(() => {
                  saveLessonProgress(payload)
                    .then(() => refreshProgressSummariesRef.current())
                    .catch(() => {});
                }, 0);
              }
            }

            return 0;
          }

          return next;
        });
      }

      frameId = requestAnimationFrame(tick);
    }

    frameId = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(frameId);
  }, [isPlaying, tempo, visibleLessonNotes, lessonDurationSeconds]);

  async function togglePlayback() {
    await Tone.start();

    lastFrameRef.current = null;

    if (isPlaying) {
      countdownTokenRef.current += 1;
      setCountdown(null);
      setIsPlaying(false);
      return;
    }

    if (currentTime === 0) {
      triggeredNotesRef.current.clear();
      setShowResults(null);
    }

    if (countdownEnabled && currentTime === 0) {
      const token = countdownTokenRef.current + 1;
      countdownTokenRef.current = token;

      for (const step of [3, 2, 1]) {
        if (countdownTokenRef.current !== token) return;
        setCountdown(step);
        playMetronomeClick(step === 1);
        await new Promise((resolve) => setTimeout(resolve, 650));
      }

      if (countdownTokenRef.current !== token) return;
      setCountdown(null);
    }

    lastFrameRef.current = null;
    setIsPlaying(true);
  }

  function resetPlayback() {
    lastFrameRef.current = null;
    triggeredNotesRef.current.clear();
    resetPracticeScoring();
    setIsPlaying(false);
    setCurrentTime(0);
  }

  async function refreshPipelineRuns() {
  const runs = await fetchPipelineRuns(20);
  const dedupedRuns = dedupeRunsByJobId(runs);
  setPipelineRuns(dedupedRuns);
  return dedupedRuns;
  }

  function handleTempoChange(event) {
    setTempo(Number(event.target.value));
    lastFrameRef.current = null;
  }

  function handleSelectLesson(jobId) {
  if (!jobId) return;

    setCurrentLessonJobId(jobId);
    setScreenMode("lesson");
    setIsSessionsOpen(false);
  }

 function handleRenameLessonByJobId(jobId, currentTitle) {
  if (!jobId) return;

  const nextTitle = window.prompt(t("modal.lessonNamePrompt"), currentTitle);

  if (nextTitle === null) {
    return;
  }

  const cleanedTitle = nextTitle.trim();

  if (!cleanedTitle) {
    return;
  }

  setTitleOverrides((previous) => ({
    ...previous,
    [jobId]: cleanedTitle,
  }));
}

async function handleDeleteLessonByJobId(jobId, title) {
  if (!jobId) {
    return;
  }

  const confirmed = window.confirm(
    `${t("delete.confirmTitle")} "${title}"?\n\n${t("delete.confirmBody")}`
  );

  if (!confirmed) {
    return;
  }

  try {
    await deletePipelineRun(jobId);

    setTitleOverrides((previous) => {
      const next = { ...previous };
      delete next[jobId];
      return next;
    });

    await refreshPipelineRuns();

    setIsPlaying(false);
    setCurrentTime(0);
    setIsSessionsOpen(false);
    setScreenMode("home");

    if (jobId === currentLessonJobId) {
      setLesson(null);
      setLessonNotes(demoNotes);
      setLessonLoadStatus("fallback");
    }
  } catch (error) {
    window.alert(error.message || t("errors.deleteFailed"));
  }
}

function handleRenameLesson() {
  handleRenameLessonByJobId(currentLessonJobId, lessonTitle);
}

async function waitForLesson(jobId, attempts = 10) {
  let lastError = null;

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await fetchLesson(jobId);
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 1200));
    }
  }

  throw lastError || new Error(`Lesson ${jobId} was not available yet.`);
}

function setNewLessonProgress(stepKey) {
  const copy = progressCopyFor(stepKey, language);

  setNewLessonStep(copy.title);
  setNewLessonHint(copy.hint);
}

function resetNewLessonForm(sourceType = "youtube") {
  setNewLessonTitle("");
  setNewLessonTitleSource("auto");
  setNewLessonSource("");
  setNewLessonFile(null);
  setNewLessonSourceType(sourceType);
  setNewLessonStatus("idle");
  setNewLessonStep("");
  setNewLessonHint("");
  setNewLessonError("");
}

async function handleCreateNewLesson() {
  let title = (newLessonTitle ?? "").trim();
  let source = (newLessonSource ?? "").trim();
  let thumbnailUrl = "";

  if (newLessonSourceType === "youtube" && !title && source) {
    title = titleFromYouTubeUrl(source);
  }

  if (!title) {
    setNewLessonError(t("errors.enterTitle"));
    return;
  }

  const jobId = makeJobIdFromTitle(title);

  if (newLessonSourceType === "upload") {
    if (!newLessonFile) {
      setNewLessonError(t("errors.chooseFile"));
      return;
    }
  } else if (!source) {
    setNewLessonError(t("errors.enterSource"));
    return;
  }

  setNewLessonStatus("running");
  setNewLessonProgress("preparing");
  setNewLessonError("");

  try {
    if (newLessonSourceType === "upload") {
      setNewLessonProgress("uploading");

      const uploadResult = await uploadAudioFile({
        file: newLessonFile,
        jobId,
      });

      source = uploadResult.path;
    }

    if (newLessonSourceType === "youtube") {
      setNewLessonProgress("downloading");

      const shouldUseRemoteTitle = newLessonTitleSource === "auto";

      const youtubeResult = await uploadYoutubeAudio({
        url: source,
        jobId,
      });

      source = youtubeResult.path;
      thumbnailUrl = youtubeResult.thumbnail_url || "";

      if (youtubeResult.title && shouldUseRemoteTitle) {
        title = youtubeResult.title.trim();
        setNewLessonTitle(title);
      }
    }
    setNewLessonProgress(useSourceSeparation ? "separating" : "transcribing");

    await runAudioToAnalysis({
      source,
      job_id: jobId,
      processed_dir: "data/processed",
      stems_dir: "data/stems",
      artifacts_dir: "artifacts/tracer",
      use_basic_pitch: true,
      skip_separation: !useSourceSeparation,
      preprocess_audio: isAnyAudioPreprocessingEnabled,
      trim_silence: audioPreprocessOptions.trim_silence,
      normalize_audio: audioPreprocessOptions.normalize_audio,
      highpass_filter: audioPreprocessOptions.highpass_filter,
      persist: true,
      session_title: title,
    });

    if (thumbnailUrl) {
      await updatePipelineRunThumbnail(jobId, thumbnailUrl);
    }

    setNewLessonProgress("saving");

    setTitleOverrides((previous) => ({
      ...previous,
      [jobId]: title,
    }));

    await refreshPipelineRuns();

    setNewLessonProgress("loading");

    const loadedLesson = await waitForLesson(jobId);

    setLesson(loadedLesson);
    setLessonNotes(mapLessonNotesToUiNotes(loadedLesson.notes));
    setLessonLoadStatus("loaded");

    setCurrentLessonJobId(jobId);
    setScreenMode("lesson");

    setNewLessonProgress("done");
    setNewLessonStatus("idle");
    setIsNewLessonOpen(false);
    resetNewLessonForm("youtube");
    setIsSessionsOpen(false);

    lastFrameRef.current = null;
    triggeredNotesRef.current.clear();
    resetPracticeScoring();
    setIsPlaying(false);
    setCurrentTime(0);
  } catch (error) {
    setNewLessonStatus("error");
    setNewLessonStep("");
    setNewLessonHint("");
    setNewLessonError(friendlyNewLessonError(error));
  }
}

  const stageStateClass = isPlaying ? "is-playing" : "";
return (
    <main className="app-shell">
      <section className="lesson-layout">
        {screenMode === "lesson" && (
      <header className="top-player-bar">
          <div className="top-left">
            <button
              type="button"
              className="menu-button"
              aria-label="Open menu"
              onClick={() => setIsSessionsOpen(true)}
            >
              <MenuIcon />
            </button>

            <div className="lesson-heading-block">
              <p className="eyebrow">DaiTune</p>

              <div className="lesson-title-row">
                <h1 className="lesson-title">{lessonTitle}</h1>

                <button
                  type="button"
                  className="title-edit-button"
                  aria-label="Rename current lesson"
                  onClick={handleRenameLesson}
                >
                  <PencilIcon />
                </button>
              </div>

              <p className="lesson-subtitle">{lessonSubtitle}</p>

              {lessonLoadStatus === "fallback" && (
                <p className="lesson-load-status">{t("summary.fallback")}</p>
              )}

              <div className="lesson-ai-summary" aria-label="AI lesson summary">
                <span>{t("summary.reviewNotes")}: {reviewNoteCount}</span>
                <span>{t("summary.unknownConfidence")}: {unknownConfidenceCount}</span>
              </div>
            </div>
          </div>

          <div className="top-center">
            <div className="view-switch view-switch-hero" role="tablist" aria-label="View mode">
              <button
                type="button"
                className={viewMode === "blocks" ? "active" : ""}
                onClick={() => setViewMode("blocks")}
                aria-pressed={viewMode === "blocks"}
              >
                <img src={viewBlocksIcon} alt="" className="view-mode-image" aria-hidden="true" />
                <span className="view-mode-label">{t("view.blocks")}</span>
              </button>

              <button
                type="button"
                className={viewMode === "sheet" ? "active" : ""}
                onClick={() => setViewMode("sheet")}
                aria-pressed={viewMode === "sheet"}
              >
                <img src={viewSheetIcon} alt="" className="view-mode-image" aria-hidden="true" />
                <span className="view-mode-label">{t("view.sheet")}</span>
              </button>

              <button
                type="button"
                className={viewMode === "mix" ? "active" : ""}
                onClick={() => setViewMode("mix")}
                aria-pressed={viewMode === "mix"}
              >
                <img src={viewMixIcon} alt="" className="view-mode-image" aria-hidden="true" />
                <span className="view-mode-label">{t("view.mix")}</span>
              </button>
            </div>
          </div>

          <div className="top-right">
            <LanguageToggle language={language} onToggle={toggleLanguage} />

            <button
              type="button"
              className="settings-gear-button"
              onClick={() => setIsSettingsOpen((open) => !open)}
              aria-label="Settings"
              title={t("settings.title")}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path
                  d="M12 15.4a3.4 3.4 0 1 0 0-6.8 3.4 3.4 0 0 0 0 6.8Zm7.6-3.4c0 .5 0 .9-.1 1.3l2 1.6-1.9 3.3-2.4-.9c-.7.6-1.4 1-2.3 1.3l-.4 2.5h-3.9l-.4-2.5c-.8-.3-1.6-.7-2.3-1.3l-2.4.9-1.9-3.3 2-1.6a8 8 0 0 1 0-2.6l-2-1.6 1.9-3.3 2.4.9c.7-.6 1.5-1 2.3-1.3l.4-2.5h3.9l.4 2.5c.9.3 1.6.7 2.3 1.3l2.4-.9 1.9 3.3-2 1.6c.1.4.1.8.1 1.3Z"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinejoin="round"
                />
              </svg>
            </button>

            <div className="lesson-player-bar">
              <button
                type="button"
                className="lesson-player-toggle"
                onClick={togglePlayback}
                aria-label={isPlaying ? t("player.pausePlayback") : t("player.playLesson")}
                title={isPlaying ? t("common.pause") : t("common.play")}
              >
                <span className={`lesson-player-toggle-icon ${isPlaying ? "is-pause" : "is-play"}`}>
                  {isPlaying ? "❚❚" : "▶"}
                </span>
              </button>

              <div className="lesson-player-main">
                <div className="lesson-player-time-row">
                  <span className="lesson-player-label">{t("player.label")}</span>
                  <strong>
                    {formatPlaybackTime(musicalTime)} / {formatPlaybackTime(lessonDuration)}
                  </strong>
                </div>

                <input
                  className="lesson-player-scrubber"
                  type="range"
                  min="0"
                  max={Math.max(lessonDuration, 0.01)}
                  step="0.05"
                  value={Math.min(musicalTime, Math.max(lessonDuration, 0.01))}
                  onChange={(event) => seekToMusicalTime(Number(event.target.value))}
                  aria-label="Lesson player timeline"
                  style={{
                    "--scrubber-progress": `${scrubberProgressPercent}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </header>
        )}
        {screenMode === "home" && (
      <header className="home-app-header">
        <div className="home-brand-block">
          <div className="home-logo-slot" aria-label="DaiTune logo">
            <img src={daiTuneLogo} alt="DaiTune logo" />
          </div>

          <div>
            <p className="eyebrow">{t("brand.eyebrow")}</p>
            <h1>DaiTune</h1>
            <span>{t("brand.subtitle")}</span>
          </div>
        </div>

        <div className="home-header-actions">
          <LanguageToggle language={language} onToggle={toggleLanguage} />

            <button
              type="button"
              className="settings-gear-button"
              onClick={() => setIsSettingsOpen((open) => !open)}
              aria-label="Settings"
              title={t("settings.title")}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path
                  d="M12 15.4a3.4 3.4 0 1 0 0-6.8 3.4 3.4 0 0 0 0 6.8Zm7.6-3.4c0 .5 0 .9-.1 1.3l2 1.6-1.9 3.3-2.4-.9c-.7.6-1.4 1-2.3 1.3l-.4 2.5h-3.9l-.4-2.5c-.8-.3-1.6-.7-2.3-1.3l-2.4.9-1.9-3.3 2-1.6a8 8 0 0 1 0-2.6l-2-1.6 1.9-3.3 2.4.9c.7-.6 1.5-1 2.3-1.3l.4-2.5h3.9l.4 2.5c.9.3 1.6.7 2.3 1.3l2.4-.9 1.9 3.3-2 1.6c.1.4.1.8.1 1.3Z"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinejoin="round"
                />
              </svg>
            </button>

          <button
            type="button"
            className="secondary-control"
            disabled={!latestPipelineRun}
            onClick={() => {
              if (latestPipelineRun?.job_id) {
                handleSelectLesson(latestPipelineRun.job_id);
              }
            }}
          >
            {t("home.continueLatest")}
          </button>

          <button
            type="button"
            className="primary-control"
            onClick={() => {
              resetNewLessonForm("youtube");
              setIsNewLessonOpen(true);
            }}
          >
            {t("home.newLesson")}
          </button>
        </div>
      </header>
    )}
            {isSessionsOpen && (
          <div className="sessions-drawer-layer" aria-label="Application menu">
            <button
              type="button"
              className="sessions-drawer-backdrop"
              aria-label="Close menu"
              onClick={() => setIsSessionsOpen(false)}
            />

            <aside className="sessions-drawer" role="dialog" aria-label="Application menu">
              <div className="sessions-drawer-header drawer-header-with-logo">
                <div className="drawer-logo-slot" aria-label="DaiTune logo">
                  <img src={daiTuneLogo} alt="DaiTune logo" />
                </div>

                <div className="drawer-header-copy">
                  <p className="sessions-drawer-eyebrow">DaiTune</p>
                  <h2>{t("drawer.menu")}</h2>
                </div>

                <button
                  type="button"
                  className="sessions-close-button"
                  aria-label="Close menu"
                  onClick={() => setIsSessionsOpen(false)}
                >
                  <CloseIcon />
                </button>
              </div>

              <section className="drawer-section drawer-primary-actions">
                <button
                  type="button"
                  className="drawer-nav-button"
                  onClick={() => {
                    setScreenMode("home");
                    setIsSessionsOpen(false);
                    setIsPlaying(false);
                  }}
                >
                  <span className="drawer-nav-icon">
                    <HomeIcon />
                  </span>

                  <span className="drawer-nav-copy">
                    <strong>{t("drawer.home")}</strong>
                    <small>{t("drawer.homeHint")}</small>
                  </span>
                </button>

                <button
                  type="button"
                  className="drawer-nav-button drawer-nav-button-accent"
                  onClick={() => {
                    resetNewLessonForm("youtube");
                    setIsNewLessonOpen(true);
                  }}
                >
                  <span className="drawer-nav-icon">
                    <NewLessonIcon />
                  </span>

                  <span className="drawer-nav-copy">
                    <strong>{t("modal.newLesson")}</strong>
                    <small>{t("drawer.newLessonHint")}</small>
                  </span>
                </button>
              </section>

              <section className="drawer-section">
                <div className="drawer-section-header drawer-section-header-icon">
                  <span className="drawer-section-title-icon">
                    <CurrentLessonIcon />
                  </span>

                  <span>{t("drawer.currentLesson")}</span>
                </div>

                <div
                  className="session-list-item current-lesson-menu-card active"
                  role="button"
                  tabIndex={0}
                  onClick={() => {
                    setScreenMode("lesson");
                    setIsSessionsOpen(false);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setScreenMode("lesson");
                      setIsSessionsOpen(false);
                    }
                  }}
                >
                  <div className="session-list-main">
                    <strong>{lessonTitle}</strong>

                    <span>
                      {lessonMeta.detected_key || activePipelineRun?.detected_key || "Unknown key"} ·{" "}
                      {lessonNotes.length} notes ·{" "}
                      {lessonMeta.transcription_method || activePipelineRun?.transcription_method || "unknown"}
                    </span>
                  </div>

                  <div className="session-item-actions">
                    <button
                      type="button"
                      className="session-item-edit-button"
                      aria-label="Rename current lesson"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleRenameLesson();
                      }}
                    >
                      <PencilIcon />
                    </button>
                  </div>
                </div>
              </section>

              <section className="drawer-section drawer-section-flex">
                <div className="drawer-section-header drawer-section-header-icon">
                  <span className="drawer-section-title-icon">
                    <SavedLessonsIcon />
                  </span>
                  <span>{t("drawer.savedLessons")}</span>
                  <strong>{pipelineRuns.length}</strong>
                </div>

                <div className="sessions-list">
                  {pipelineRuns.map((run) => {
                    const runTitle = titleForRun(run, titleOverrides);
                    const isActive = run.job_id === currentLessonJobId;

                    return (
                      <div
                        key={`${run.id}-${run.job_id}`}
                        className={`session-list-item ${isActive ? "active" : ""}`}
                        role="button"
                        tabIndex={0}
                        onClick={() => handleSelectLesson(run.job_id)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            handleSelectLesson(run.job_id);
                          }
                        }}
                      >
                        <div className="session-list-main">
                          <strong>{runTitle}</strong>
                          <span>
                            {run.detected_key || "Unknown key"} · {run.note_count ?? 0} notes ·{" "}
                            {run.transcription_method || "unknown"}
                          </span>

                          {progressSummaries[run.job_id] && (
                            <span className="lesson-progress-badge">
                              {"★".repeat(progressSummaries[run.job_id].best_stars || 0)}
                              {"☆".repeat(3 - (progressSummaries[run.job_id].best_stars || 0))}
                              {" "}
                              {progressSummaries[run.job_id].best_accuracy}%
                            </span>
                          )}
                        </div>

                        <div className="session-item-actions">
                          <button
                            type="button"
                            className="session-item-edit-button"
                            aria-label={`Rename ${runTitle}`}
                            onClick={(event) => {
                              event.stopPropagation();
                              handleRenameLessonByJobId(run.job_id, runTitle);
                            }}
                          >
                            <PencilIcon />
                          </button>

                          <button
                            type="button"
                            className="session-item-delete-button"
                            aria-label={`Delete ${runTitle}`}
                            onClick={(event) => {
                              event.stopPropagation();
                              handleDeleteLessonByJobId(run.job_id, runTitle);
                            }}
                          >
                            <TrashIcon />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            </aside>
          </div>
        )}

        {isNewLessonOpen && (
        <div className="new-lesson-modal-layer" aria-label="New lesson modal">
          <button
            type="button"
            className="new-lesson-modal-backdrop"
            aria-label="Close new lesson modal"
            onClick={() => setIsNewLessonOpen(false)}
          />

          <section className="new-lesson-modal" role="dialog" aria-label="Create new lesson">
            <div className="new-lesson-modal-header">
              <div>
                <p className="sessions-drawer-eyebrow">{t("modal.createEyebrow")}</p>
                <h2>{t("modal.newLesson")}</h2>
              </div>

              <button
                type="button"
                className="sessions-close-button"
                aria-label="Close"
                onClick={() => setIsNewLessonOpen(false)}
              >
                <CloseIcon />
              </button>
            </div>

            <label className="new-lesson-field">
              <span>{t("modal.lessonTitle")}</span>

              <input
                value={newLessonTitle ?? ""}
                onChange={(event) => {
                  setNewLessonTitle(event.target.value ?? "");
                  setNewLessonTitleSource("user");
                }}
                placeholder={t("modal.titlePlaceholder")}
              />

              <small className="new-lesson-field-hint">
                {newLessonTitleSource === "auto"
                  ? t("modal.titleAutoHint")
                  : t("modal.titleCustomHint")}
              </small>
            </label>

            <div className="new-lesson-source-tabs">
              <button
                type="button"
                className={newLessonSourceType === "youtube" ? "active" : ""}
                onClick={() => {
                  resetNewLessonForm("youtube");
                }}
              >
                {t("modal.youtubeUrl")}
              </button>

              <button
                type="button"
                className={newLessonSourceType === "upload" ? "active" : ""}
                onClick={() => {
                  resetNewLessonForm("upload");
                }}
              >
                {t("modal.uploadFile")}
              </button>
            </div>

          {newLessonSourceType === "upload" ? (
            <label className="new-lesson-field">
              <span>{t("modal.audioFile")}</span>
              <input
                type="file"
                accept=".wav,.mp3,audio/wav,audio/mpeg"
                onChange={(event) => {
                  const file = event.target.files?.[0] || null;

                  setNewLessonFile(file);

                  if (file && !newLessonTitle.trim()) {
                    setNewLessonTitle(titleFromFilename(file.name));
                  }
                }}
              />
            </label>
          ) : (
            <label className="new-lesson-field">
              <span>{newLessonSourceType === "youtube" ? t("modal.youtubeUrl") : t("modal.audioSource")}</span>
             <input
                value={newLessonSource ?? ""}
                onChange={(event) => {
                  const value = event.target.value ?? "";

                  setNewLessonSource(value);

                  if (
                    newLessonSourceType === "youtube" &&
                    newLessonTitleSource === "auto"
                  ) {
                    const inferredTitle = titleFromYouTubeUrl(value);

                    if (inferredTitle) {
                      setNewLessonTitle(inferredTitle);
                    }
                  }
                }}
                placeholder={
                  newLessonSourceType === "youtube"
                    ? t("modal.youtubePlaceholder")
                    : t("modal.sourcePlaceholder")
                }
              />
            </label>
          )}

            <div className="new-lesson-preprocess-panel compact">
              <div className="new-lesson-preprocess-summary">
                <label className="preprocess-master-toggle">
                  <input
                    type="checkbox"
                    checked={areAllAudioPreprocessingOptionsEnabled}
                    onChange={toggleAudioPreprocessingEnabled}
                  />

                  <span>
                    <strong>{t("modal.preprocessing")}</strong>
                    <small>{t("modal.preprocessingHint")}</small>
                  </span>
                </label>

                <button
                  type="button"
                  className={`preprocess-expand-button ${
                    isAudioPreprocessOpen ? "open" : ""
                  }`}
                  aria-label={
                    isAudioPreprocessOpen
                      ? "Hide audio preprocessing details"
                      : "Show audio preprocessing details"
                  }
                  aria-expanded={isAudioPreprocessOpen}
                  onClick={() => setIsAudioPreprocessOpen((isOpen) => !isOpen)}
                >
                </button>
              </div>

              {isAudioPreprocessOpen && (
                <div className="new-lesson-preprocess-details">
                  <label className="preprocess-toggle-row">
                    <input
                      type="checkbox"
                      checked={audioPreprocessOptions.trim_silence}
                      onChange={() => toggleAudioPreprocessOption("trim_silence")}
                    />
                    <span>
                      <strong>{t("modal.trimSilence")}</strong>
                      <small>{t("modal.trimSilenceHint")}</small>
                    </span>
                  </label>

                  <label className="preprocess-toggle-row">
                    <input
                      type="checkbox"
                      checked={audioPreprocessOptions.normalize_audio}
                      onChange={() => toggleAudioPreprocessOption("normalize_audio")}
                    />
                    <span>
                      <strong>{t("modal.normalize")}</strong>
                      <small>{t("modal.normalizeHint")}</small>
                    </span>
                  </label>

                  <label className="preprocess-toggle-row">
                    <input
                      type="checkbox"
                      checked={audioPreprocessOptions.highpass_filter}
                      onChange={() => toggleAudioPreprocessOption("highpass_filter")}
                    />
                    <span>
                      <strong>{t("modal.highpass")}</strong>
                      <small>{t("modal.highpassHint")}</small>
                    </span>
                  </label>
                </div>
              )}
            </div>

            <div className="new-lesson-source-panel">
              <label className="source-separation-toggle">
                <input
                  type="checkbox"
                  checked={useSourceSeparation}
                  onChange={() => setUseSourceSeparation((currentValue) => !currentValue)}
                />

                <span>
                  <strong>{t("modal.sourceSeparation")}</strong>
                  <small>
                    {t("modal.sourceSeparationHint")}
                  </small>
                </span>
              </label>
            </div>

            {newLessonStatus === "running" && (
              <div className="new-lesson-processing-panel">
                <div className="new-lesson-processing-spinner" aria-hidden="true" />

                <div>
                  <strong>{newLessonStep || t("modal.processingFallbackTitle")}</strong>
                  <span>{newLessonHint || t("modal.processingFallbackHint")}</span>
                </div>
              </div>
            )}

            {newLessonError && (
              <p className="new-lesson-error">{newLessonError}</p>
            )}

            <div className="new-lesson-actions">
              <button
                type="button"
                className="secondary-control"
                onClick={() => setIsNewLessonOpen(false)}
                disabled={newLessonStatus === "running"}
              >
                {t("common.cancel")}
              </button>

              <button
                type="button"
                className="primary-control"
                onClick={handleCreateNewLesson}
                disabled={newLessonStatus === "running"}
              >
                {newLessonStatus === "running" ? t("common.working") : t("modal.createLesson")}
              </button>
            </div>
          </section>
        </div>
      )}

      {screenMode === "home" && (
        <section className="home-screen">
          <div className="home-hero-card">
            <div className="home-hero-copy">
              <p className="eyebrow">{t("home.quickStart")}</p>
              <h1>{t("home.title")}</h1>
              <p>
                {t("home.description")}
              </p>
            </div>

            <div className="home-quick-create">
              <div className="home-youtube-row">
                <input
                  value={newLessonSourceType === "youtube" ? newLessonSource ?? "" : ""}
                  onChange={(event) => {
                    const value = event.target.value ?? "";

                    setNewLessonSourceType("youtube");
                    setNewLessonSource(value);

                    if (newLessonTitleSource === "auto") {
                      const inferredTitle = titleFromYouTubeUrl(value);

                      if (inferredTitle) {
                        setNewLessonTitle(inferredTitle);
                      }
                    }
                  }}
                  placeholder={t("home.pasteYoutube")}
                />

                <button
                  type="button"
                  className="primary-control"
                  onClick={() => {
                    setNewLessonSourceType("youtube");
                    setIsNewLessonOpen(true);
                  }}
                >
                  {t("home.add")}
                </button>
              </div>

              <button
                type="button"
                className="home-upload-button"
                onClick={() => {
                  resetNewLessonForm("upload");
                  setIsNewLessonOpen(true);
                }}
              >
                {t("home.upload")}
              </button>
            </div>
          </div>

          <section className="home-library-section">
            <div className="home-section-header">
              <div>
                <p className="eyebrow">{t("home.library")}</p>
                <h2>{t("home.yourLessons")}</h2>
              </div>

              <span>{pipelineRuns.length} {t("common.saved")}</span>
            </div>

            <div className="home-lessons-grid">
              {pipelineRuns.map((run) => {
                const runTitle = titleForRun(run, titleOverrides);
                const thumbnailUrl = run.thumbnail_url || "";

                return (
                  <article
                    key={`${run.id}-${run.job_id}`}
                    className="home-lesson-card"
                  >
                    <button
                      type="button"
                      className="home-lesson-open-button"
                      onClick={() => handleSelectLesson(run.job_id)}
                    >
                      <div
                        className={`home-lesson-thumbnail ${thumbnailUrl ? "has-thumbnail" : ""}`}
                        aria-hidden="true"
                      >
                        {thumbnailUrl ? (
                          <img
                            src={thumbnailUrl}
                            alt=""
                            loading="lazy"
                            referrerPolicy="no-referrer"
                          />
                        ) : (
                          <>
                            <span />
                            <span />
                            <span />
                            <span />
                          </>
                        )}
                      </div>

                      <strong>{runTitle}</strong>

                      <span>
                        {run.detected_key || "Unknown key"} · {run.note_count ?? 0} notes
                      </span>

                      <small>{run.transcription_method || "unknown"}</small>

                      {progressSummaries[run.job_id] && (
                        <span className="lesson-progress-badge">
                          {"★".repeat(progressSummaries[run.job_id].best_stars || 0)}
                          {"☆".repeat(3 - (progressSummaries[run.job_id].best_stars || 0))}
                          {" "}
                          {progressSummaries[run.job_id].best_accuracy}% ·{" "}
                          {progressSummaries[run.job_id].attempts}×
                        </span>
                      )}
                    </button>

                    <button
                      type="button"
                      className="home-lesson-delete-button"
                      aria-label={`Delete ${runTitle}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDeleteLessonByJobId(run.job_id, runTitle);
                      }}
                    >
                      <TrashIcon />
                    </button>
                  </article>
                );
              })}
            </div>
          </section>
        </section>
      )}
        {isSettingsOpen && (
          <>
            <div
              className="settings-backdrop"
              onClick={() => setIsSettingsOpen(false)}
            />
            <aside className="settings-panel" aria-label={t("settings.title")}>
              <header className="settings-panel-header">
                <strong>{t("settings.title")}</strong>
                <button
                  type="button"
                  className="settings-close-button"
                  onClick={() => setIsSettingsOpen(false)}
                >
                  ✕
                </button>
              </header>

              <section className="settings-section">
                <span className="settings-section-label">{t("settings.theme")}</span>
                <div className="theme-swatch-row">
                  {UI_THEMES.map((theme) => (
                    <button
                      key={theme.id}
                      type="button"
                      className={`theme-swatch ${uiThemeId === theme.id ? "active" : ""}`}
                      onClick={() => setUiThemeId(theme.id)}
                      title={theme.label}
                    >
                      <span
                        className="theme-swatch-dot"
                        style={{
                          background: `linear-gradient(135deg, ${theme.stage[0]} 0%, ${theme.stage[2]} 50%, ${theme.stage[4]} 100%)`,
                        }}
                      />
                      <span className="theme-swatch-label">{theme.label}</span>
                    </button>
                  ))}
                </div>
              </section>

              <section className="settings-section">
                <span className="settings-section-label">{t("settings.blocks")}</span>
                <div className="theme-swatch-row">
                  {BLOCK_PALETTES.map((palette) => (
                    <button
                      key={palette.id}
                      type="button"
                      className={`theme-swatch ${blockPaletteId === palette.id ? "active" : ""}`}
                      onClick={() => setBlockPaletteId(palette.id)}
                      title={palette.label}
                    >
                      <span className="block-swatch-dot">
                        <span style={{ background: palette.left.fill }} />
                        <span style={{ background: palette.right.fill }} />
                      </span>
                      <span className="theme-swatch-label">{palette.label}</span>
                    </button>
                  ))}
                </div>
              </section>

              <section className="settings-section">
                <span className="settings-section-label">{t("settings.piano")}</span>

                <select
                  className="piano-model-select"
                  value={
                    KEYBOARD_MODELS.find(
                      (model) =>
                        model.low === pianoRange.low && model.high === pianoRange.high
                    )?.id ?? ""
                  }
                  onChange={(event) => {
                    const model = KEYBOARD_MODELS.find(
                      (candidate) => candidate.id === event.target.value
                    );

                    if (model) {
                      setPianoRange({ low: model.low, high: model.high });
                    }
                  }}
                >
                  <option value="">{t("settings.pianoModel")}</option>

                  {[88, 76, 61, 49, 44, 32].map((keyCount) => (
                    <optgroup
                      key={keyCount}
                      label={`${keyCount} ${t("settings.pianoKeys")}`}
                    >
                      {KEYBOARD_MODELS.filter(
                        (model) => model.keys === keyCount
                      ).map((model) => (
                        <option key={model.id} value={model.id}>
                          {model.label} · {midiNoteLabel(model.low)}–{midiNoteLabel(model.high)}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>

                <div className="piano-range-presets">
                  {PIANO_RANGE_PRESETS.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      className={`piano-preset-chip ${
                        pianoRange.low === preset.low && pianoRange.high === preset.high
                          ? "active"
                          : ""
                      }`}
                      onClick={() => setPianoRange({ low: preset.low, high: preset.high })}
                      title={`${midiNoteLabel(preset.low)} – ${midiNoteLabel(preset.high)}`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>

                <div className="piano-range-selects">
                  <label>
                    <span>{t("settings.pianoFrom")}</span>
                    <select
                      value={pianoRange.low}
                      onChange={(event) => {
                        const low = Number(event.target.value);
                        setPianoRange((range) => ({
                          low,
                          high: Math.max(range.high, low + 12),
                        }));
                      }}
                    >
                      {Array.from({ length: 108 - 21 + 1 }, (_, index) => 21 + index)
                        .filter((midi) => midi <= pianoRange.high - 12)
                        .map((midi) => (
                          <option key={midi} value={midi}>
                            {midiNoteLabel(midi)}
                          </option>
                        ))}
                    </select>
                  </label>

                  <label>
                    <span>{t("settings.pianoTo")}</span>
                    <select
                      value={pianoRange.high}
                      onChange={(event) => {
                        const high = Number(event.target.value);
                        setPianoRange((range) => ({
                          low: Math.min(range.low, high - 12),
                          high,
                        }));
                      }}
                    >
                      {Array.from({ length: 108 - 21 + 1 }, (_, index) => 21 + index)
                        .filter((midi) => midi >= pianoRange.low + 12)
                        .map((midi) => (
                          <option key={midi} value={midi}>
                            {midiNoteLabel(midi)}
                          </option>
                        ))}
                    </select>
                  </label>

                  <span className="piano-range-count">
                    {pianoRange.high - pianoRange.low + 1} {t("settings.pianoKeys")}
                  </span>
                </div>

                <label className="settings-toggle-row">
                  <input
                    type="checkbox"
                    checked={fitToRange}
                    onChange={(event) => setFitToRange(event.target.checked)}
                  />
                  <span>{t("settings.fitRange")}</span>
                </label>
              </section>

              <section className="settings-section">
                <label className="settings-toggle-row">
                  <input
                    type="checkbox"
                    checked={countdownEnabled}
                    onChange={(event) => setCountdownEnabled(event.target.checked)}
                  />
                  <span>{t("settings.countdown")}</span>
                </label>
              </section>

              <section className="settings-section settings-meta">
                <span>
                  {t("settings.midi")}:{" "}
                  <strong className={`midi-status midi-status-${midiStatus}`}>
                    {midiStatus}
                  </strong>
                </span>
                <span className="settings-keys-hint">{t("settings.keysHint")}</span>
              </section>
            </aside>
          </>
        )}

        {screenMode === "lesson" && (
        <section className={`lesson-stage ${stageStateClass} view-mode-${viewMode}`}>
          {coachState.status !== "idle" && (
            <div className="coach-overlay" role="dialog" aria-label={t("coach.title")}>
              <div className="coach-card">
                <div className="coach-card-header">
                  <strong>{t("coach.title")}</strong>
                  <button
                    type="button"
                    className="settings-close-button"
                    onClick={() => setCoachState({ status: "idle", plan: null })}
                  >
                    ✕
                  </button>
                </div>

                {coachState.status === "loading" && (
                  <p className="coach-status">{t("coach.loading")}</p>
                )}

                {coachState.status === "empty" && (
                  <p className="coach-status">{t("coach.empty")}</p>
                )}

                {coachState.status === "error" && (
                  <p className="coach-status">{t("coach.error")}</p>
                )}

                {coachState.status === "ready" && coachState.plan && (
                  <>
                    <p className="coach-overall-tip">{coachState.plan.overall_tip}</p>

                    {(coachState.plan.recommended_view ||
                      coachState.plan.recommended_tempo) && (
                      <div className="coach-recommended-row">
                        <span>{t("coach.recommended")}:</span>

                        {coachState.plan.recommended_view && (
                          <button
                            type="button"
                            className="coach-chip"
                            onClick={() =>
                              setNoteViewMode(coachState.plan.recommended_view)
                            }
                          >
                            {coachState.plan.recommended_view === "beginner"
                              ? t("notes.beginner")
                              : "Practice"}{" "}
                            · {t("coach.apply")}
                          </button>
                        )}

                        {coachState.plan.recommended_tempo && (
                          <button
                            type="button"
                            className="coach-chip"
                            onClick={() =>
                              setTempo(coachState.plan.recommended_tempo)
                            }
                          >
                            {Math.round(coachState.plan.recommended_tempo * 100)}% ·{" "}
                            {t("coach.apply")}
                          </button>
                        )}
                      </div>
                    )}

                    <div className="coach-sections">
                      {coachState.plan.sections.map((section, index) => (
                        <div key={index} className="coach-section">
                          <div className="coach-section-main">
                            <strong>
                              {formatPlaybackTime(section.start)} – {formatPlaybackTime(section.end)}
                            </strong>

                            <span className="coach-section-meta">
                              {section.hand === "left"
                                ? t("coach.handLeft")
                                : section.hand === "right"
                                  ? t("coach.handRight")
                                  : t("coach.handBoth")}{" "}
                              · {section.errors} {t("coach.errorsWord")} ·{" "}
                              {Math.round(section.tempo * 100)}%
                            </span>

                            <span className="coach-section-tip">{section.tip}</span>
                          </div>

                          <button
                            type="button"
                            className="coach-practice-button"
                            onClick={() => applyCoachSection(section)}
                          >
                            {t("coach.practice")}
                          </button>
                        </div>
                      ))}

                      {coachState.plan.sections.length === 0 && (
                        <p className="coach-status">{coachState.plan.overall_tip}</p>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {countdown !== null && (
            <div className="countdown-overlay" aria-hidden="true">
              <span key={countdown} className="countdown-number">
                {countdown}
              </span>
            </div>
          )}

          {showResults && (
            <div className="results-overlay">
              <div className="results-card">
                <h3>{t("results.title")}</h3>

                <div className="results-stars" aria-hidden="true">
                  {[0, 1, 2].map((index) => (
                    <span
                      key={index}
                      className={`results-star ${index < showResults.stars ? "earned" : ""}`}
                    >
                      ★
                    </span>
                  ))}
                </div>

                <div className="results-accuracy">{showResults.accuracy}%</div>

                <div className="results-breakdown">
                  <span className="practice-stat hit">✓ {showResults.hits}</span>
                  <span className="practice-stat miss">○ {showResults.missed}</span>
                  <span className="practice-stat wrong">✕ {showResults.wrong}</span>
                </div>

                <div className="results-actions">
                  <button
                    type="button"
                    onClick={() => {
                      setShowResults(null);
                      openCoach(700);
                    }}
                  >
                    {t("coach.button")} 🎯
                  </button>

                  <button
                    type="button"
                    className="primary-control"
                    onClick={() => {
                      setShowResults(null);
                      resetPracticeScoring();
                      togglePlayback();
                    }}
                  >
                    {t("results.tryAgain")}
                  </button>
                  <button
                    type="button"
                    className="secondary-control"
                    onClick={() => setShowResults(null)}
                  >
                    {t("results.close")}
                  </button>
                </div>
              </div>
            </div>
          )}

          {viewMode === "blocks" && (
            <>
              <div className="waterfall-frame">
                <WaterfallCanvas
                  notes={visibleLessonNotes}
                  noteViewMode={noteViewMode}
                  currentTime={currentTime}
                  musicalTime={musicalTime}
                  tempo={tempo}
                  noteDisplayMode={noteDisplayMode}
                  judgements={noteJudgements}
                  colors={canvasPalette}
                  stage={uiTheme.stage}
                  lowestPitch={pianoRange.low}
                  highestPitch={pianoRange.high}
                />
              </div>

              <PianoKeyboard
                notes={visibleLessonNotes}
                currentTime={currentTime}
                musicalTime={musicalTime}
                tempo={tempo}
                labelMode={keyboardLabelMode}
                livePitch={detectedMidi}
                wrongPitches={wrongPitchSet}
                lowestPitch={pianoRange.low}
                highestPitch={pianoRange.high}
              />
            </>
          )}

          {viewMode === "sheet" && (
            <SheetView
              notes={visibleLessonNotes}
              musicalTime={musicalTime}
              durationSeconds={lessonDurationSeconds}
              onSeek={seekToMusicalTime}
              judgements={noteJudgements}
              noteDisplayMode={noteDisplayMode}
              handColors={sheetPalette}
            />
          )}

          {viewMode === "mix" && (
            <>
              <SheetView
                compact
                notes={visibleLessonNotes}
                musicalTime={musicalTime}
                durationSeconds={lessonDurationSeconds}
                onSeek={seekToMusicalTime}
                judgements={noteJudgements}
                noteDisplayMode={noteDisplayMode}
                handColors={sheetPalette}
              />

              <div className="waterfall-frame mix-waterfall-frame">
                <WaterfallCanvas
                  notes={visibleLessonNotes}
                  noteViewMode={noteViewMode}
                  currentTime={currentTime}
                  musicalTime={musicalTime}
                  tempo={tempo}
                  noteDisplayMode={noteDisplayMode}
                  judgements={noteJudgements}
                  colors={canvasPalette}
                  stage={uiTheme.stage}
                  lowestPitch={pianoRange.low}
                  highestPitch={pianoRange.high}
                />
              </div>

              <PianoKeyboard
                notes={visibleLessonNotes}
                currentTime={currentTime}
                musicalTime={musicalTime}
                tempo={tempo}
                labelMode={keyboardLabelMode}
                livePitch={detectedMidi}
                wrongPitches={wrongPitchSet}
                lowestPitch={pianoRange.low}
                highestPitch={pianoRange.high}
              />
            </>
          )}
        </section>
        )}
        {screenMode === "lesson" && (
        <footer className="controls-card controls-card-polished">
          <div className="transport-group controls-transport-section">
            <button className="primary-control" onClick={togglePlayback}>
              {isPlaying ? t("common.pause") : t("common.play")}
            </button>

            <button className="secondary-control" onClick={resetPlayback}>
              {t("common.reset")}
            </button>
          </div>

          <label className="tempo-control controls-tempo-section">
            <span>{t("controls.tempo")}</span>

            <input
              type="range"
              min="0.25"
              max="1.5"
              step="0.05"
              value={tempo}
              onChange={handleTempoChange}
            />

            <strong>{Math.round(tempo * 100)}%</strong>
          </label>

          <div className="mini-control-pill display-pill" aria-label="Note display mode">
            <span className="mini-mode-label">{t("controls.display")}</span>

            <div className="mini-mode-switch">
              <button
                type="button"
                className={noteDisplayMode === "blank" ? "active" : ""}
                onClick={() => setNoteDisplayMode("blank")}
              >
                Blank
              </button>

              <button
                type="button"
                className={noteDisplayMode === "letters" ? "active" : ""}
                onClick={() => setNoteDisplayMode("letters")}
              >
                A–G
              </button>

              <button
                type="button"
                className={noteDisplayMode === "symbol" ? "active" : ""}
                onClick={() => setNoteDisplayMode("symbol")}
              >
                ♪
              </button>
            </div>
          </div>

          <div
            className="mini-control-pill notes-view-pill notes-pill"
            aria-label="Note view mode"
          >
            <span className="mini-mode-label">{t("controls.notes")}</span>

            <div className="mini-mode-switch">
              <button
                type="button"
                className={noteViewMode === "raw" ? "active" : ""}
                onClick={() => setNoteViewMode("raw")}
              >
                Raw
              </button>

              <button
                type="button"
                className={noteViewMode === "practice" ? "active" : ""}
                onClick={() => setNoteViewMode("practice")}
              >
                Practice
              </button>

              <button
                type="button"
                className={noteViewMode === "beginner" ? "active" : ""}
                onClick={() => setNoteViewMode("beginner")}
              >
                {t("notes.beginner")}
              </button>
            </div>
          </div>

          <button
            type="button"
            className="mini-control-pill coach-pill"
            onClick={() => openCoach()}
          >
            <span className="coach-pill-icon" aria-hidden="true">🎯</span>
            <span className="mini-mode-label">{t("coach.button")}</span>
          </button>

          <div className="mini-control-pill weak-pill" aria-label="Low-confidence notes">
            <span className="mini-mode-label">{t("controls.weak")}</span>

            <div className="mini-mode-switch">
              <button
                type="button"
                className={!hideLowConfidence ? "active" : ""}
                onClick={() => setHideLowConfidence(false)}
              >
                {t("weak.show")}
              </button>

              <button
                type="button"
                className={hideLowConfidence ? "active" : ""}
                onClick={() => setHideLowConfidence(true)}
              >
                {t("weak.hide")}
              </button>
            </div>

            {hideLowConfidence && hiddenLowConfidenceCount > 0 && (
              <span className="weak-hidden-count">
                {hiddenLowConfidenceCount} {t("weak.hiddenCount")}
              </span>
            )}
          </div>

          <div className="mini-control-pill mic-pill" aria-label="Live microphone practice">
            <span className="mini-mode-label">{t("controls.mic")}</span>

            <div className="mini-mode-switch">
              <button
                type="button"
                className={!isMicEnabled ? "active" : ""}
                onClick={() => setIsMicEnabled(false)}
              >
                {t("mic.off")}
              </button>

              <button
                type="button"
                className={isMicEnabled ? "active" : ""}
                onClick={() => setIsMicEnabled(true)}
              >
                {t("mic.on")}
              </button>
            </div>

            {isMicEnabled && (
              <span className={`mic-status mic-status-${micStatus}`}>
                {micStatus === "listening"
                  ? detectedMidi !== null
                    ? midiToToneNote(detectedMidi)
                    : t("mic.listening")
                  : micStatus === "denied"
                    ? t("mic.denied")
                    : t("mic.starting")}
              </span>
            )}
          </div>

          {isMicEnabled && (
            <div className="practice-stats" aria-label="Live practice score">
              <span className="practice-stat hit">
                ✓ {practiceStats.hits}
              </span>
              <span className="practice-stat miss">
                ○ {practiceStats.missed}
              </span>
              <span className="practice-stat wrong">
                ✕ {practiceStats.wrong}
              </span>
              {practiceStats.accuracy !== null && (
                <span className="practice-stat accuracy">
                  {practiceStats.accuracy}%
                </span>
              )}
            </div>
          )}

          <div className="mini-control-pill mode-pill" aria-label="Play mode" title={t("mode.waitHint")}>
            <span className="mini-mode-label">{t("controls.mode")}</span>

            <div className="mini-mode-switch">
              <button
                type="button"
                className={playMode === "flow" ? "active" : ""}
                onClick={() => setPlayMode("flow")}
              >
                {t("mode.flow")}
              </button>

              <button
                type="button"
                className={playMode === "wait" ? "active" : ""}
                onClick={() => setPlayMode("wait")}
              >
                {t("mode.wait")}
              </button>
            </div>
          </div>

          <div className="mini-control-pill metronome-pill" aria-label="Metronome">
            <span className="mini-mode-label">{t("controls.metronome")}</span>

            <div className="mini-mode-switch">
              <button
                type="button"
                className={!metronomeOn ? "active" : ""}
                onClick={() => setMetronomeOn(false)}
              >
                {t("mic.off")}
              </button>

              <button
                type="button"
                className={metronomeOn ? "active" : ""}
                onClick={() => setMetronomeOn(true)}
              >
                {t("mic.on")}
              </button>
            </div>

            {metronomeOn && (
              <input
                type="number"
                className="metronome-bpm-input"
                min={30}
                max={220}
                value={metronomeBpm}
                onChange={(event) =>
                  setMetronomeBpm(
                    Math.max(30, Math.min(220, Number(event.target.value) || 90))
                  )
                }
                aria-label="Metronome BPM"
              />
            )}
          </div>

          <div className="mini-control-pill loop-pill" aria-label="Practice loop">
            <span className="mini-mode-label">{t("controls.loop")}</span>

            <div className="mini-mode-switch">
              <button type="button" onClick={setLoopPointA}>
                {t("loop.setA")}
              </button>

              <button
                type="button"
                onClick={setLoopPointB}
                disabled={!loopRegion}
              >
                {t("loop.setB")}
              </button>

              {loopRegion && (
                <button
                  type="button"
                  className="loop-clear-button"
                  onClick={clearLoop}
                  title={t("loop.clear")}
                >
                  ✕
                </button>
              )}
            </div>

            {loopRegion && (
              <span className={`loop-range ${loopRegion.b !== null ? "armed" : ""}`}>
                {formatPlaybackTime(loopRegion.a)}
                {" – "}
                {loopRegion.b !== null ? formatPlaybackTime(loopRegion.b) : "…"}
              </span>
            )}
          </div>

          <div className="mini-control-pill keys-pill" aria-label="Keyboard label mode">
            <span className="mini-mode-label">{t("controls.keys")}</span>

            <div className="mini-mode-switch">
              <button
                type="button"
                className={keyboardLabelMode === "off" ? "active" : ""}
                onClick={() => setKeyboardLabelMode("off")}
              >
                Off
              </button>

              <button
                type="button"
                className={keyboardLabelMode === "c-only" ? "active" : ""}
                onClick={() => setKeyboardLabelMode("c-only")}
              >
                C
              </button>

              <button
                type="button"
                className={keyboardLabelMode === "all" ? "active" : ""}
                onClick={() => setKeyboardLabelMode("all")}
              >
                All
              </button>
            </div>
          </div>

          <HandsControl
            activeHand={activeHand}
            onChange={setActiveHand}
          />
        </footer>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
