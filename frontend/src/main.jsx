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
import SheetPreview from "./components/SheetPreview.jsx";
import { demoNotes } from "./lib/demoNotes";
import {
  DEFAULT_LESSON_JOB_ID,
  dedupeRunsByJobId,
  deletePipelineRun,
  fetchLesson,
  fetchPipelineRuns,
  updatePipelineRunThumbnail,
  isGeneratedYouTubeTitle,
  makeJobIdFromTitle,
  mapLessonNotesToUiNotes,
  runAudioToAnalysis,
  titleForRun,
  titleFromFilename,
  titleFromYouTubeUrl,
  uploadAudioFile,
  uploadYoutubeAudio,
} from "./api/lessonApi";

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

      setCurrentTime(clampedMusicalTime / safeTempo);
    },
    [lessonDuration, tempo]
  );

  const scrubberProgressPercent =
    lessonDuration > 0
      ? Math.min(100, Math.max(0, (musicalTime / lessonDuration) * 100))
      : 0;

  const visibleLessonNotes = React.useMemo(() => {
    return lessonNotes.filter((note) => {
      if (activeHand === "both") return true;
      return note.hand === activeHand;
    });
  }, [lessonNotes, activeHand]);

  const noteViewHint =
    noteViewMode === "practice"
      ? "Practice view keeps original timing and only adds visual guidance."
      : "Raw view shows the original transcription.";

  const progressPercent = Math.max(
    0,
    Math.min(100, Math.round((musicalTime / Math.max(lessonDurationSeconds, 0.01)) * 100))
  );

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
        console.log("Acoustic piano samples loaded");
        synthRef.current = pianoSampler;
        fallbackSynth.dispose();
      },
    }).connect(gain);

    synthRef.current = fallbackSynth;

    return () => {
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
        setIsPlaying(false);
        setCurrentTime(0);
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
          const next = time + deltaSeconds;

          const previousMusicalTime = time * tempo;
          const nextMusicalTime = next * tempo;

          triggerNotesBetween(previousMusicalTime, nextMusicalTime);

          if (next >= lessonDurationSeconds / tempo) {
            setIsPlaying(false);
            triggeredNotesRef.current.clear();
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

    if (!isPlaying && currentTime === 0) {
      triggeredNotesRef.current.clear();
    }

    setIsPlaying((value) => !value);
  }

  function resetPlayback() {
    lastFrameRef.current = null;
    triggeredNotesRef.current.clear();
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
        {screenMode === "lesson" && (
        <section className={`lesson-stage ${stageStateClass} view-mode-${viewMode}`}>
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
                />
              </div>

              <PianoKeyboard
                notes={visibleLessonNotes}
                currentTime={currentTime}
                musicalTime={musicalTime}
                tempo={tempo}
                labelMode={keyboardLabelMode}
              />
            </>
          )}

          {viewMode === "sheet" && (
            <SheetPreview />
          )}

          {viewMode === "mix" && (
            <>
              <SheetPreview compact />

              <div className="waterfall-frame mix-waterfall-frame">
                <WaterfallCanvas
                  notes={visibleLessonNotes}
                  noteViewMode={noteViewMode}
                  currentTime={currentTime}
                  musicalTime={musicalTime}
                  tempo={tempo}
                  noteDisplayMode={noteDisplayMode}
                />
              </div>

              <PianoKeyboard
                notes={visibleLessonNotes}
                currentTime={currentTime}
                musicalTime={musicalTime}
                tempo={tempo}
                labelMode={keyboardLabelMode}
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
            </div>
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
