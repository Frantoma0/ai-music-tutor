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
