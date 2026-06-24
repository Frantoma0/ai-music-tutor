const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const DEFAULT_LESSON_JOB_ID =
  import.meta.env.VITE_LESSON_JOB_ID || "demo-morning-light-lesson";

export async function fetchLesson(jobId = DEFAULT_LESSON_JOB_ID) {
  const response = await fetch(`${API_BASE_URL}/api/lessons/${jobId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch lesson ${jobId}: ${response.status}`);
  }

  return response.json();
}

export function mapLessonNotesToUiNotes(notes = []) {
  return notes.map((note) => {
    const start = Number(note.start ?? 0);
    const end = Number(note.end ?? start);

    return {
      ...note,
      pitchName: note.pitch_name,
      pitch_name: note.pitch_name,
      start,
      end,
      duration: Number(note.duration ?? Math.max(end - start, 0)),
      confidence: note.confidence,
      hand: note.hand ?? "unknown",
      hvsScore: note.hvs_score,
      hvsLabel: note.hvs_label,
      hvsReason: note.hvs_reason,
      inCorrectionMask: Boolean(note.in_correction_mask),
      correctionStatus: note.correction_status ?? "none",
      originalPitch: note.original_pitch,
      correctionReason: note.correction_reason,
    };
  });
}
export async function fetchPipelineRuns(limit = 20) {
  const response = await fetch(`${API_BASE_URL}/api/tools/list_pipeline_runs/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      payload: { limit },
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch pipeline runs: ${response.status}`);
  }

  const result = await response.json();

  if (result.status !== "success") {
    throw new Error(result.error || "Pipeline runs request failed");
  }

  return result.data?.runs ?? [];
}

export function dedupeRunsByJobId(runs = []) {
  const byJobId = new Map();

  for (const run of runs) {
    if (!run?.job_id || run.status !== "completed") {
      continue;
    }

    if (!byJobId.has(run.job_id)) {
      byJobId.set(run.job_id, run);
    }
  }

  return Array.from(byJobId.values());
}

export function titleForRun(run, titleOverrides = {}) {
  const override = titleOverrides[run?.job_id];

  if (override?.trim()) {
    return override.trim();
  }

  if (run?.session_title?.trim()) {
    return run.session_title.trim();
  }

  if (run?.source) {
    const filename = run.source.split("/").pop();

    if (filename) {
      return filename.replace(/\.[^.]+$/, "");
    }
  }

  return run?.job_id || "Untitled lesson";
}

export async function runAudioToAnalysis(payload) {
  const response = await fetch(`${API_BASE_URL}/api/tools/run_audio_to_analysis/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      payload,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to run audio analysis: ${response.status}`);
  }

  const result = await response.json();

  if (result.status !== "success") {
    throw new Error(result.error || result.data?.error || "Audio analysis failed");
  }

  return result.data;
}

export function makeJobIdFromTitle(title) {
  const cleaned = title
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9а-я]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);

  return `${cleaned || "lesson"}-${Date.now().toString(36)}`;
}

export async function uploadAudioFile({ file, jobId }) {
  const formData = new FormData();

  formData.append("job_id", jobId);
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/uploads/audio`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to upload audio file: ${response.status} ${errorText}`);
  }

  const result = await response.json();

  if (result.status !== "success") {
    throw new Error(result.detail || "Audio upload failed");
  }

  return result;
}

export function titleFromFilename(filename = "") {
  const withoutExtension = filename.replace(/\.[^.]+$/, "");

  const withoutLeadingId = withoutExtension.replace(/^\d+[-_\s]+/, "");

  const cleaned = withoutLeadingId
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (!cleaned) {
    return "Uploaded lesson";
  }

  const shortTitle = cleaned.length > 72
    ? `${cleaned.slice(0, 72).trim()}...`
    : cleaned;

  return shortTitle.replace(/\b\w/g, (char) => char.toUpperCase());
}