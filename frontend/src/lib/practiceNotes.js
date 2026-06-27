const DEFAULT_MAX_MERGE_GAP_SECONDS = 0.06;

function handsAreCompatible(firstHand, secondHand) {
  if (!firstHand || !secondHand) return true;
  if (firstHand === "unknown" || secondHand === "unknown") return true;
  return firstHand === secondHand;
}

function mergeConfidence(firstConfidence, secondConfidence) {
  if (firstConfidence === null || firstConfidence === undefined) {
    return secondConfidence;
  }

  if (secondConfidence === null || secondConfidence === undefined) {
    return firstConfidence;
  }

  return Math.max(firstConfidence, secondConfidence);
}

function mergeVelocity(firstVelocity, secondVelocity) {
  const first = Number(firstVelocity ?? 72);
  const second = Number(secondVelocity ?? 72);

  return Math.round((first + second) / 2);
}

function canMergeNotes(previousNote, currentNote, maxGapSeconds) {
  if (!previousNote || !currentNote) return false;

  if (previousNote.pitch !== currentNote.pitch) {
    return false;
  }

  if (!handsAreCompatible(previousNote.hand, currentNote.hand)) {
    return false;
  }

  const previousEnd = Number(previousNote.end ?? previousNote.start ?? 0);
  const currentStart = Number(currentNote.start ?? 0);

  const gap = currentStart - previousEnd;

  return gap >= -0.02 && gap <= maxGapSeconds;
}

function mergeTwoNotes(previousNote, currentNote) {
  const previousStart = Number(previousNote.start ?? 0);
  const previousEnd = Number(previousNote.end ?? previousStart);
  const currentStart = Number(currentNote.start ?? 0);
  const currentEnd = Number(currentNote.end ?? currentStart);

  const start = Math.min(previousStart, currentStart);
  const end = Math.max(previousEnd, currentEnd);

  const mergedIds = [
    ...(previousNote.mergedIds ?? [previousNote.id]),
    ...(currentNote.mergedIds ?? [currentNote.id]),
  ].filter(Boolean);

  return {
    ...previousNote,
    id: `practice-${mergedIds.join("-")}`,
    start,
    end,
    duration: Math.max(end - start, 0),
    confidence: mergeConfidence(previousNote.confidence, currentNote.confidence),
    velocity: mergeVelocity(previousNote.velocity, currentNote.velocity),
    hand:
      previousNote.hand && previousNote.hand !== "unknown"
        ? previousNote.hand
        : currentNote.hand,
    mergedIds,
    isPracticeMerged: true,
    practiceMergeCount: mergedIds.length,
  };
}

export function buildPracticeNotes(notes = [], options = {}) {
  const maxGapSeconds =
    Number(options.maxGapSeconds ?? DEFAULT_MAX_MERGE_GAP_SECONDS);

  const sortedNotes = [...notes].sort((first, second) => {
    const startDiff = Number(first.start ?? 0) - Number(second.start ?? 0);

    if (startDiff !== 0) {
      return startDiff;
    }

    return Number(first.pitch ?? 0) - Number(second.pitch ?? 0);
  });

  const result = [];

  for (const note of sortedNotes) {
    const previousNote = result[result.length - 1];

    if (canMergeNotes(previousNote, note, maxGapSeconds)) {
      result[result.length - 1] = mergeTwoNotes(previousNote, note);
    } else {
      result.push({
        ...note,
        mergedIds: note.mergedIds ?? [note.id].filter(Boolean),
        isPracticeMerged: Boolean(note.isPracticeMerged),
        practiceMergeCount: note.practiceMergeCount ?? 1,
      });
    }
  }

  return result;
}

export function getPracticeNoteStats(rawNotes = [], practiceNotes = []) {
  return {
    rawCount: rawNotes.length,
    practiceCount: practiceNotes.length,
    mergedCount: Math.max(rawNotes.length - practiceNotes.length, 0),
  };
}
