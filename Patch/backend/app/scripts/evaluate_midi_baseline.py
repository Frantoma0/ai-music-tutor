from __future__ import annotations

import argparse
import json
from pathlib import Path

import mir_eval
import numpy as np
import pretty_midi


def _load_notes(midi_path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    midi = pretty_midi.PrettyMIDI(str(midi_path))

    intervals: list[tuple[float, float]] = []
    pitches: list[int] = []

    for instrument in midi.instruments:
        if instrument.is_drum:
            continue

        for note in instrument.notes:
            if note.end <= note.start:
                continue

            intervals.append((float(note.start), float(note.end)))
            pitches.append(int(note.pitch))

    sorted_pairs = sorted(
        zip(intervals, pitches, strict=False), key=lambda item: (item[0][0], item[1])
    )

    if not sorted_pairs:
        return np.empty((0, 2), dtype=float), np.empty((0,), dtype=int)

    sorted_intervals, sorted_pitches = zip(*sorted_pairs, strict=False)

    return (
        np.asarray(sorted_intervals, dtype=float),
        np.asarray(sorted_pitches, dtype=int),
    )


def evaluate_midi_pair(
    reference_midi: str | Path,
    estimated_midi: str | Path,
    onset_tolerance: float = 0.05,
    offset_ratio: float | None = 0.2,
) -> dict:
    ref_intervals, ref_pitches = _load_notes(reference_midi)
    est_intervals, est_pitches = _load_notes(estimated_midi)

    if ref_intervals.size == 0:
        return {
            "status": "error",
            "error": "Reference MIDI has no notes.",
            "reference_note_count": 0,
            "estimated_note_count": len(est_intervals),
        }

    if est_intervals.size == 0:
        return {
            "status": "completed",
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "overlap": 0.0,
            "reference_note_count": len(ref_intervals),
            "estimated_note_count": 0,
            "onset_tolerance": onset_tolerance,
            "offset_ratio": offset_ratio,
            "error": None,
        }

    precision, recall, f1, overlap = mir_eval.transcription.precision_recall_f1_overlap(
        ref_intervals,
        ref_pitches,
        est_intervals,
        est_pitches,
        onset_tolerance=onset_tolerance,
        offset_ratio=offset_ratio,
    )

    return {
        "status": "completed",
        "precision": round(float(precision), 6),
        "recall": round(float(recall), 6),
        "f1": round(float(f1), 6),
        "overlap": round(float(overlap), 6),
        "reference_note_count": len(ref_intervals),
        "estimated_note_count": len(est_intervals),
        "onset_tolerance": onset_tolerance,
        "offset_ratio": offset_ratio,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate predicted MIDI against reference MIDI.")
    parser.add_argument("--reference-midi", required=True)
    parser.add_argument("--estimated-midi", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--onset-tolerance", type=float, default=0.05)
    parser.add_argument("--offset-ratio", type=float, default=0.2)

    args = parser.parse_args()

    result = evaluate_midi_pair(
        reference_midi=args.reference_midi,
        estimated_midi=args.estimated_midi,
        onset_tolerance=args.onset_tolerance,
        offset_ratio=args.offset_ratio,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
