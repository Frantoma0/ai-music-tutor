from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pretty_midi


@dataclass(frozen=True)
class NoteEvent:
    index: int
    pitch: int
    start: float
    end: float


def load_events(path: Path) -> list[NoteEvent]:
    midi = pretty_midi.PrettyMIDI(str(path))
    events: list[NoteEvent] = []

    for instrument in midi.instruments:
        if instrument.is_drum:
            continue

        for note in instrument.notes:
            if note.end <= note.start:
                continue

            events.append(
                NoteEvent(
                    index=len(events),
                    pitch=int(note.pitch),
                    start=float(note.start),
                    end=float(note.end),
                )
            )

    return sorted(events, key=lambda item: (item.start, item.pitch, item.end))


def greedy_match(
    ref_events: list[NoteEvent],
    est_events: list[NoteEvent],
    *,
    onset_tolerance: float,
    require_pitch: bool,
) -> list[dict[str, Any]]:
    candidates: list[tuple[float, int, int, NoteEvent, NoteEvent]] = []

    for ref in ref_events:
        for est in est_events:
            onset_delta = abs(ref.start - est.start)

            if onset_delta > onset_tolerance:
                continue

            if require_pitch and ref.pitch != est.pitch:
                continue

            candidates.append((onset_delta, ref.index, est.index, ref, est))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))

    used_ref: set[int] = set()
    used_est: set[int] = set()
    matches: list[dict[str, Any]] = []

    for onset_delta, _ref_index, _est_index, ref, est in candidates:
        if ref.index in used_ref or est.index in used_est:
            continue

        used_ref.add(ref.index)
        used_est.add(est.index)

        matches.append(
            {
                "ref_index": ref.index,
                "est_index": est.index,
                "ref_pitch": ref.pitch,
                "est_pitch": est.pitch,
                "ref_start": ref.start,
                "est_start": est.start,
                "onset_delta": onset_delta,
                "pitch_delta": ref.pitch - est.pitch,
            }
        )

    return matches


def f1_from_counts(tp: int, est_count: int, ref_count: int) -> dict[str, float]:
    precision = tp / est_count if est_count else 0.0
    recall = tp / ref_count if ref_count else 0.0
    f1 = 2 * tp / (est_count + ref_count) if est_count + ref_count else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def decompose_piece(
    *,
    reference_midi: Path,
    estimated_midi: Path,
    onset_tolerance: float,
) -> dict[str, Any]:
    ref_events = load_events(reference_midi)
    est_events = load_events(estimated_midi)

    pitch_matches = greedy_match(
        ref_events,
        est_events,
        onset_tolerance=onset_tolerance,
        require_pitch=True,
    )

    matched_ref = {item["ref_index"] for item in pitch_matches}
    matched_est = {item["est_index"] for item in pitch_matches}

    unmatched_ref = [item for item in ref_events if item.index not in matched_ref]
    unmatched_est = [item for item in est_events if item.index not in matched_est]

    onset_matches = greedy_match(
        unmatched_ref,
        unmatched_est,
        onset_tolerance=onset_tolerance,
        require_pitch=False,
    )

    correctable = []
    uncorrectable = []

    for item in onset_matches:
        abs_delta = abs(int(item["pitch_delta"]))

        if 1 <= abs_delta <= 2:
            correctable.append(item)
        else:
            uncorrectable.append(item)

    onset_matched_ref = {item["ref_index"] for item in onset_matches}
    onset_matched_est = {item["est_index"] for item in onset_matches}

    spurious_est = [
        item for item in unmatched_est
        if item.index not in onset_matched_est
    ]

    undetected_ref = [
        item for item in unmatched_ref
        if item.index not in onset_matched_ref
    ]

    baseline = f1_from_counts(
        tp=len(pitch_matches),
        est_count=len(est_events),
        ref_count=len(ref_events),
    )

    f1_step_per_fix = (
        2 / (len(est_events) + len(ref_events))
        if len(est_events) + len(ref_events)
        else 0.0
    )

    oracle_gain = len(correctable) * f1_step_per_fix

    return {
        "reference_note_count": len(ref_events),
        "estimated_note_count": len(est_events),
        "already_correct_tp_count": len(pitch_matches),
        "correctable_pitch_error_le_2_count": len(correctable),
        "uncorrectable_pitch_error_gt_2_count": len(uncorrectable),
        "spurious_or_timing_fp_count": len(spurious_est),
        "undetected_fn_count": len(undetected_ref),
        "baseline_onset_pitch": baseline,
        "f1_step_per_perfect_fix": f1_step_per_fix,
        "oracle_optimal_v4_gain": oracle_gain,
        "oracle_optimal_v4_f1": baseline["f1"] + oracle_gain,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci-csv", required=True)
    parser.add_argument("--maestro-root", required=True)
    parser.add_argument("--tracer-root", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--onset-tolerance", type=float, default=0.05)

    args = parser.parse_args()

    ci_csv = Path(args.ci_csv)
    maestro_root = Path(args.maestro_root)
    tracer_root = Path(args.tracer_root)

    rows = list(csv.DictReader(ci_csv.open(newline="", encoding="utf-8")))

    piece_reports: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        job_id = f"day9-maestro-ci-persisted-{index:02d}-e2e"
        tracer_dir = tracer_root / job_id

        reference_midi = maestro_root / row["midi_filename"]
        estimated_midi = tracer_dir / "output.mid"
        notes_path = tracer_dir / "notes.json"

        piece: dict[str, Any] = {
            "piece_index": index,
            "job_id": job_id,
            "composer": row["canonical_composer"],
            "title": row["canonical_title"],
            "reference_midi": str(reference_midi),
            "estimated_midi": str(estimated_midi),
            "notes_path": str(notes_path),
            "reference_exists": reference_midi.exists(),
            "estimated_exists": estimated_midi.exists(),
            "notes_exists": notes_path.exists(),
            "status": "pending",
            "error": None,
        }

        if not reference_midi.exists() or not estimated_midi.exists():
            piece["status"] = "missing_input"
            piece["error"] = "Missing reference MIDI or estimated output MIDI."
            piece_reports.append(piece)
            continue

        try:
            metrics = decompose_piece(
                reference_midi=reference_midi,
                estimated_midi=estimated_midi,
                onset_tolerance=args.onset_tolerance,
            )
            piece.update(metrics)
            piece["status"] = "completed"
        except Exception as exc:
            piece["status"] = "error"
            piece["error"] = f"{type(exc).__name__}: {exc}"

        piece_reports.append(piece)

    completed = [item for item in piece_reports if item["status"] == "completed"]

    aggregate = {
        "piece_count": len(piece_reports),
        "completed_piece_count": len(completed),
        "missing_or_failed_piece_count": len(piece_reports) - len(completed),
        "reference_note_count": sum(item.get("reference_note_count", 0) for item in completed),
        "estimated_note_count": sum(item.get("estimated_note_count", 0) for item in completed),
        "already_correct_tp_count": sum(item.get("already_correct_tp_count", 0) for item in completed),
        "correctable_pitch_error_le_2_count": sum(item.get("correctable_pitch_error_le_2_count", 0) for item in completed),
        "uncorrectable_pitch_error_gt_2_count": sum(item.get("uncorrectable_pitch_error_gt_2_count", 0) for item in completed),
        "spurious_or_timing_fp_count": sum(item.get("spurious_or_timing_fp_count", 0) for item in completed),
        "undetected_fn_count": sum(item.get("undetected_fn_count", 0) for item in completed),
    }

    aggregate_baseline = f1_from_counts(
        tp=aggregate["already_correct_tp_count"],
        est_count=aggregate["estimated_note_count"],
        ref_count=aggregate["reference_note_count"],
    )

    aggregate["baseline_onset_pitch"] = aggregate_baseline

    denom = aggregate["estimated_note_count"] + aggregate["reference_note_count"]
    aggregate["f1_step_per_perfect_fix"] = 2 / denom if denom else 0.0
    aggregate["oracle_optimal_v4_gain"] = (
        aggregate["correctable_pitch_error_le_2_count"]
        * aggregate["f1_step_per_perfect_fix"]
    )
    aggregate["oracle_optimal_v4_f1"] = (
        aggregate_baseline["f1"] + aggregate["oracle_optimal_v4_gain"]
    )

    report = {
        "status": "completed",
        "onset_tolerance": args.onset_tolerance,
        "ci_csv": str(ci_csv),
        "maestro_root": str(maestro_root),
        "tracer_root": str(tracer_root),
        "aggregate": aggregate,
        "pieces": piece_reports,
    }

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    csv_fields = [
        "piece_index",
        "job_id",
        "composer",
        "title",
        "status",
        "reference_note_count",
        "estimated_note_count",
        "already_correct_tp_count",
        "correctable_pitch_error_le_2_count",
        "uncorrectable_pitch_error_gt_2_count",
        "spurious_or_timing_fp_count",
        "undetected_fn_count",
        "baseline_f1",
        "oracle_optimal_v4_gain",
        "oracle_optimal_v4_f1",
        "error",
    ]

    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()

        for item in piece_reports:
            baseline = item.get("baseline_onset_pitch") or {}
            writer.writerow(
                {
                    "piece_index": item["piece_index"],
                    "job_id": item["job_id"],
                    "composer": item["composer"],
                    "title": item["title"],
                    "status": item["status"],
                    "reference_note_count": item.get("reference_note_count"),
                    "estimated_note_count": item.get("estimated_note_count"),
                    "already_correct_tp_count": item.get("already_correct_tp_count"),
                    "correctable_pitch_error_le_2_count": item.get("correctable_pitch_error_le_2_count"),
                    "uncorrectable_pitch_error_gt_2_count": item.get("uncorrectable_pitch_error_gt_2_count"),
                    "spurious_or_timing_fp_count": item.get("spurious_or_timing_fp_count"),
                    "undetected_fn_count": item.get("undetected_fn_count"),
                    "baseline_f1": baseline.get("f1"),
                    "oracle_optimal_v4_gain": item.get("oracle_optimal_v4_gain"),
                    "oracle_optimal_v4_f1": item.get("oracle_optimal_v4_f1"),
                    "error": item.get("error"),
                }
            )

    print(json.dumps({
        "status": "completed",
        "piece_count": aggregate["piece_count"],
        "completed_piece_count": aggregate["completed_piece_count"],
        "aggregate": aggregate,
        "output_json": str(output_json),
        "output_csv": str(output_csv),
    }, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
