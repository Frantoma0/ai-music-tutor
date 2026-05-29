from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pretty_midi


@dataclass(frozen=True)
class NoteEvent:
    index: int
    pitch: int
    start: float
    end: float


def load_events(midi_path: str) -> list[NoteEvent]:
    midi = pretty_midi.PrettyMIDI(midi_path)
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


def f1_from_counts(tp: int, est_count: int, ref_count: int) -> dict[str, float]:
    precision = tp / est_count if est_count else 0.0
    recall = tp / ref_count if ref_count else 0.0
    f1 = 2 * tp / (est_count + ref_count) if est_count + ref_count else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def greedy_match(
    *,
    ref_events: list[NoteEvent],
    est_events: list[NoteEvent],
    onset_tolerance: float,
    require_pitch: bool,
) -> list[dict[str, Any]]:
    candidates: list[tuple[float, int, int]] = []

    for ref_pos, ref in enumerate(ref_events):
        for est_pos, est in enumerate(est_events):
            onset_delta = abs(ref.start - est.start)

            if onset_delta > onset_tolerance:
                continue

            if require_pitch and ref.pitch != est.pitch:
                continue

            candidates.append((onset_delta, ref_pos, est_pos))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))

    used_ref: set[int] = set()
    used_est: set[int] = set()
    matches: list[dict[str, Any]] = []

    for onset_delta, ref_pos, est_pos in candidates:
        if ref_pos in used_ref or est_pos in used_est:
            continue

        ref = ref_events[ref_pos]
        est = est_events[est_pos]

        used_ref.add(ref_pos)
        used_est.add(est_pos)

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


def load_selected_candidates(mask_path: str | None) -> list[dict[str, Any]]:
    if not mask_path:
        return []

    path = Path(mask_path)

    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))

    return [
        item for item in data.get("candidates", [])
        if item.get("selected")
    ]


def candidate_start(candidate: dict[str, Any]) -> float | None:
    for key in ["start", "onset", "start_time"]:
        value = candidate.get(key)
        if isinstance(value, (int, float)):
            return float(value)

    return None


def candidate_pitch(candidate: dict[str, Any]) -> int | None:
    value = candidate.get("pitch")
    return int(value) if isinstance(value, int) else None


def find_est_for_candidate(
    *,
    candidate: dict[str, Any],
    est_events: list[NoteEvent],
    tolerance: float,
) -> int | None:
    pitch = candidate_pitch(candidate)
    start = candidate_start(candidate)

    if pitch is None or start is None:
        return None

    possible = [
        event for event in est_events
        if event.pitch == pitch and abs(event.start - start) <= tolerance
    ]

    if not possible:
        return None

    best = min(possible, key=lambda event: abs(event.start - start))
    return best.index


def diagnose_correctable_errors(
    *,
    reference_path: str,
    est_path: str,
    mask_path: str | None,
    output_path: str,
    onset_tolerance: float = 0.05,
    candidate_match_tolerance: float = 0.02,
) -> dict[str, Any]:
    ref_events = load_events(reference_path)
    est_events = load_events(est_path)

    pitch_matches = greedy_match(
        ref_events=ref_events,
        est_events=est_events,
        onset_tolerance=onset_tolerance,
        require_pitch=True,
    )

    matched_ref_indices = {item["ref_index"] for item in pitch_matches}
    matched_est_indices = {item["est_index"] for item in pitch_matches}

    unmatched_ref = [
        item for item in ref_events
        if item.index not in matched_ref_indices
    ]

    unmatched_est = [
        item for item in est_events
        if item.index not in matched_est_indices
    ]

    onset_only_matches = greedy_match(
        ref_events=unmatched_ref,
        est_events=unmatched_est,
        onset_tolerance=onset_tolerance,
        require_pitch=False,
    )

    bucket_by_est_index: dict[int, str] = {}

    correctable = []
    uncorrectable = []

    for item in onset_only_matches:
        abs_delta = abs(int(item["pitch_delta"]))

        if 1 <= abs_delta <= 2:
            bucket = "correctable_pitch_error_le_2"
            correctable.append(item)
        else:
            bucket = "uncorrectable_pitch_error_gt_2"
            uncorrectable.append(item)

        bucket_by_est_index[int(item["est_index"])] = bucket

    onset_matched_est = {int(item["est_index"]) for item in onset_only_matches}
    onset_matched_ref = {int(item["ref_index"]) for item in onset_only_matches}

    spurious_est = [
        item for item in unmatched_est
        if item.index not in onset_matched_est
    ]

    undetected_ref = [
        item for item in unmatched_ref
        if item.index not in onset_matched_ref
    ]

    for item in pitch_matches:
        bucket_by_est_index[int(item["est_index"])] = "already_correct_tp"

    for item in spurious_est:
        bucket_by_est_index[item.index] = "spurious_or_timing_fp"

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
    oracle_ceiling_f1 = baseline["f1"] + oracle_gain

    selected_candidates = load_selected_candidates(mask_path)

    selected_bucket_counts: dict[str, int] = {}
    selected_items = []

    for candidate in selected_candidates:
        est_index = find_est_for_candidate(
            candidate=candidate,
            est_events=est_events,
            tolerance=candidate_match_tolerance,
        )

        bucket = (
            "not_matched_to_est"
            if est_index is None
            else bucket_by_est_index.get(est_index, "unknown")
        )

        selected_bucket_counts[bucket] = selected_bucket_counts.get(bucket, 0) + 1

        selected_items.append(
            {
                "candidate_id": candidate.get("id"),
                "est_index": est_index,
                "pitch": candidate.get("pitch"),
                "start": candidate_start(candidate),
                "bucket": bucket,
            }
        )

    report = {
        "status": "completed",
        "reference_path": reference_path,
        "est_path": est_path,
        "mask_path": mask_path,
        "onset_tolerance": onset_tolerance,
        "candidate_match_tolerance": candidate_match_tolerance,
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
        "oracle_optimal_v4_f1": oracle_ceiling_f1,
        "selected_candidate_count": len(selected_candidates),
        "selected_bucket_counts": selected_bucket_counts,
        "selected_items": selected_items,
        "examples": {
            "correctable_pitch_error_le_2": correctable[:20],
            "uncorrectable_pitch_error_gt_2": uncorrectable[:20],
            "spurious_or_timing_fp": [
                {
                    "est_index": item.index,
                    "pitch": item.pitch,
                    "start": item.start,
                    "end": item.end,
                }
                for item in spurious_est[:20]
            ],
            "undetected_fn": [
                {
                    "ref_index": item.index,
                    "pitch": item.pitch,
                    "start": item.start,
                    "end": item.end,
                }
                for item in undetected_ref[:20]
            ],
        },
        "error": None,
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    return report


def print_summary(report: dict[str, Any]) -> None:
    print("=" * 72)
    print("CORRECTABLE ERROR DECOMPOSITION")
    print("=" * 72)

    print(f"reference_note_count: {report['reference_note_count']}")
    print(f"estimated_note_count:  {report['estimated_note_count']}")

    print()
    print("BASELINE ONSET+PITCH")
    baseline = report["baseline_onset_pitch"]
    print(f"precision: {baseline['precision']:.6f}")
    print(f"recall:    {baseline['recall']:.6f}")
    print(f"f1:        {baseline['f1']:.6f}")

    print()
    print("ERROR BUCKETS")
    print(f"already_correct_tp:             {report['already_correct_tp_count']}")
    print(f"correctable_pitch_error_le_2:    {report['correctable_pitch_error_le_2_count']}")
    print(f"uncorrectable_pitch_error_gt_2:  {report['uncorrectable_pitch_error_gt_2_count']}")
    print(f"spurious_or_timing_fp:           {report['spurious_or_timing_fp_count']}")
    print(f"undetected_fn:                   {report['undetected_fn_count']}")

    print()
    print("ORACLE V4 CEILING")
    print(f"f1_step_per_perfect_fix: {report['f1_step_per_perfect_fix']:.6f}")
    print(f"oracle_gain:             {report['oracle_optimal_v4_gain']:.6f}")
    print(f"oracle_f1_ceiling:       {report['oracle_optimal_v4_f1']:.6f}")

    print()
    print("SELECTED CANDIDATE OVERLAP")
    print(f"selected_candidate_count: {report['selected_candidate_count']}")

    for bucket, count in sorted(report["selected_bucket_counts"].items()):
        print(f"{bucket}: {count}")

    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True)
    parser.add_argument("--est", required=True)
    parser.add_argument("--mask-path", default=None)
    parser.add_argument("--output", required=True)
    parser.add_argument("--onset-tolerance", type=float, default=0.05)
    parser.add_argument("--candidate-match-tolerance", type=float, default=0.02)

    args = parser.parse_args()

    try:
        report = diagnose_correctable_errors(
            reference_path=args.reference,
            est_path=args.est,
            mask_path=args.mask_path,
            output_path=args.output,
            onset_tolerance=args.onset_tolerance,
            candidate_match_tolerance=args.candidate_match_tolerance,
        )
    except Exception as exc:
        report = {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }

    print_summary(report)

    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
