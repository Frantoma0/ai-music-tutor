import argparse
import json
import statistics
from pathlib import Path

import mir_eval
import numpy as np
import pretty_midi


def load_notes(midi_path: str) -> tuple[np.ndarray, np.ndarray]:
    pm = pretty_midi.PrettyMIDI(midi_path)
    onsets: list[float] = []
    offsets: list[float] = []
    pitches: list[int] = []

    for instrument in pm.instruments:
        for note in instrument.notes:
            if note.end > note.start:
                onsets.append(note.start)
                offsets.append(note.end)
                pitches.append(note.pitch)

    if not onsets:
        return np.zeros((0, 2), dtype=float), np.zeros((0,), dtype=int)

    intervals = np.column_stack([np.array(onsets, dtype=float), np.array(offsets, dtype=float)])
    midi = np.array(pitches, dtype=int)
    order = np.argsort(intervals[:, 0])

    return intervals[order], midi[order]


def midi_to_hz(midi: np.ndarray) -> np.ndarray:
    return 440.0 * (2.0 ** ((midi.astype(float) - 69.0) / 12.0))


def evaluate(
    ref_intervals: np.ndarray,
    ref_midi: np.ndarray,
    est_intervals: np.ndarray,
    est_midi: np.ndarray,
    onset_tolerance: float,
    offset_ratio: float | None,
    pitch_tolerance: float,
) -> dict[str, float]:
    if ref_intervals.shape[0] == 0 or est_intervals.shape[0] == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "overlap": 0.0}

    precision, recall, f1, overlap = mir_eval.transcription.precision_recall_f1_overlap(
        ref_intervals,
        midi_to_hz(ref_midi),
        est_intervals,
        midi_to_hz(est_midi),
        onset_tolerance=onset_tolerance,
        pitch_tolerance=pitch_tolerance,
        offset_ratio=offset_ratio,
    )

    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "overlap": float(overlap),
    }


def onset_sweep(
    ref_intervals: np.ndarray,
    ref_midi: np.ndarray,
    est_intervals: np.ndarray,
    est_midi: np.ndarray,
    tolerances: list[float],
    offset_ratio: float | None,
    pitch_tolerance: float,
) -> list[dict[str, float]]:
    results: list[dict[str, float]] = []

    for tol in tolerances:
        row = evaluate(
            ref_intervals,
            ref_midi,
            est_intervals,
            est_midi,
            tol,
            offset_ratio,
            pitch_tolerance,
        )
        row["onset_tolerance"] = tol
        results.append(row)

    return results


def pitch_shift_sweep(
    ref_intervals: np.ndarray,
    ref_midi: np.ndarray,
    est_intervals: np.ndarray,
    est_midi: np.ndarray,
    shifts: list[int],
    onset_tolerance: float,
    offset_ratio: float | None,
    pitch_tolerance: float,
) -> list[dict[str, float]]:
    results: list[dict[str, float]] = []

    for shift in shifts:
        row = evaluate(
            ref_intervals,
            ref_midi,
            est_intervals,
            est_midi + shift,
            onset_tolerance,
            offset_ratio,
            pitch_tolerance,
        )
        row["semitone_shift"] = float(shift)
        results.append(row)

    return results


def best_global_shift(
    ref_intervals: np.ndarray,
    ref_midi: np.ndarray,
    est_intervals: np.ndarray,
    est_midi: np.ndarray,
    search_range: int,
    onset_tolerance: float,
    offset_ratio: float | None,
    pitch_tolerance: float,
) -> dict[str, float]:
    candidates = pitch_shift_sweep(
        ref_intervals,
        ref_midi,
        est_intervals,
        est_midi,
        list(range(-search_range, search_range + 1)),
        onset_tolerance,
        offset_ratio,
        pitch_tolerance,
    )

    return max(candidates, key=lambda row: row["f1"])


def chroma_evaluate(
    ref_intervals: np.ndarray,
    ref_midi: np.ndarray,
    est_intervals: np.ndarray,
    est_midi: np.ndarray,
    onset_tolerance: float,
    offset_ratio: float | None,
) -> dict[str, float]:
    ref_chroma = (ref_midi % 12) + 60
    est_chroma = (est_midi % 12) + 60

    return evaluate(
        ref_intervals,
        ref_chroma,
        est_intervals,
        est_chroma,
        onset_tolerance,
        offset_ratio,
        50.0,
    )


def note_stats(intervals: np.ndarray, midi: np.ndarray) -> dict[str, float]:
    if intervals.shape[0] == 0:
        return {
            "note_count": 0,
            "first_onset": 0.0,
            "last_offset": 0.0,
            "span": 0.0,
            "duration_mean": 0.0,
            "duration_median": 0.0,
            "duration_min": 0.0,
            "duration_max": 0.0,
            "pitch_min": 0,
            "pitch_max": 0,
        }

    durations = (intervals[:, 1] - intervals[:, 0]).tolist()

    return {
        "note_count": int(intervals.shape[0]),
        "first_onset": float(intervals[:, 0].min()),
        "last_offset": float(intervals[:, 1].max()),
        "span": float(intervals[:, 1].max() - intervals[:, 0].min()),
        "duration_mean": float(statistics.fmean(durations)),
        "duration_median": float(statistics.median(durations)),
        "duration_min": float(min(durations)),
        "duration_max": float(max(durations)),
        "pitch_min": int(midi.min()),
        "pitch_max": int(midi.max()),
    }


def rank_suspects(report: dict, jump_threshold: float) -> list[dict[str, object]]:
    baseline_f1 = report["baseline"]["f1"]
    suspects: list[dict[str, object]] = []

    best_shift = report["best_global_shift"]

    if best_shift["semitone_shift"] != 0.0:
        delta = best_shift["f1"] - baseline_f1

        if delta > jump_threshold:
            label = "octave_or_transposition_mismatch"

            if int(best_shift["semitone_shift"]) % 12 == 0:
                label = "octave_mismatch"

            suspects.append(
                {
                    "suspect": label,
                    "f1_gain": delta,
                    "detail": f"best F1 at semitone_shift={int(best_shift['semitone_shift'])}",
                }
            )

    widest = max(report["onset_sweep"], key=lambda row: row["onset_tolerance"])
    delta_onset = widest["f1"] - baseline_f1

    if delta_onset > jump_threshold:
        suspects.append(
            {
                "suspect": "onset_misalignment",
                "f1_gain": delta_onset,
                "detail": f"F1 rises to {widest['f1']:.4f} at onset_tolerance={widest['onset_tolerance']}",
            }
        )

    no_offset = report["offset_comparison"]["without_offset"]["f1"]
    delta_offset = no_offset - baseline_f1

    if delta_offset > jump_threshold:
        suspects.append(
            {
                "suspect": "offset_duration_matching",
                "f1_gain": delta_offset,
                "detail": f"F1 rises to {no_offset:.4f} when offset matching is disabled",
            }
        )

    chroma_f1 = report["chroma"]["f1"]
    delta_chroma = chroma_f1 - baseline_f1

    if delta_chroma > jump_threshold:
        suspects.append(
            {
                "suspect": "octave_errors_pitch_class_matches",
                "f1_gain": delta_chroma,
                "detail": f"chroma F1 {chroma_f1:.4f} far above pitch F1 {baseline_f1:.4f}",
            }
        )

    ref_span = report["reference_stats"]["span"]
    est_span = report["est_stats"]["span"]
    onset_gap = abs(report["reference_stats"]["first_onset"] - report["est_stats"]["first_onset"])

    if ref_span > 0 and est_span > 0:
        span_ratio = max(ref_span, est_span) / max(min(ref_span, est_span), 1e-6)

        if span_ratio > 1.5 or onset_gap > 1.0:
            suspects.append(
                {
                    "suspect": "segment_or_piece_mismatch",
                    "f1_gain": 0.0,
                    "detail": f"ref span {ref_span:.2f}s vs est span {est_span:.2f}s, onset gap {onset_gap:.2f}s",
                }
            )

    return sorted(suspects, key=lambda item: item["f1_gain"], reverse=True)


def fmt_row(row: dict[str, float], key: str) -> str:
    return (
        f"{row.get(key, 0.0):>10}  "
        f"P={row['precision']:.4f}  "
        f"R={row['recall']:.4f}  "
        f"F1={row['f1']:.4f}  "
        f"overlap={row['overlap']:.4f}"
    )


def print_report(report: dict) -> None:
    print("=" * 72)
    print("BASELINE ALIGNMENT DIAGNOSIS")
    print("=" * 72)

    baseline = report["baseline"]
    reproduction = report["reproduction"]

    print(
        f"baseline  P={baseline['precision']:.6f}  "
        f"R={baseline['recall']:.6f}  "
        f"F1={baseline['f1']:.6f}  "
        f"overlap={baseline['overlap']:.6f}"
    )

    print(
        f"reproduction vs expected F1={reproduction['expected_f1']:.6f}  "
        f"diff={reproduction['diff']:.6f}  -> {reproduction['status']}"
    )

    if reproduction["status"] != "MATCH":
        print(
            "WARNING: harness does not reproduce production F1. "
            "Sweep results below are not comparable to production until this matches."
        )

    print("-" * 72)
    print("ONSET TOLERANCE SWEEP")

    for row in report["onset_sweep"]:
        print(fmt_row(row, "onset_tolerance"))

    print("-" * 72)
    print("OFFSET MATCHING")

    offset_comparison = report["offset_comparison"]

    print(f"with offset    F1={offset_comparison['with_offset']['f1']:.4f}")
    print(f"without offset F1={offset_comparison['without_offset']['f1']:.4f}")

    print("-" * 72)
    print("OCTAVE / TRANSPOSITION SWEEP")

    for row in report["octave_sweep"]:
        print(fmt_row(row, "semitone_shift"))

    best_shift = report["best_global_shift"]

    print(
        f"best global shift = {int(best_shift['semitone_shift'])} semitones  "
        f"F1={best_shift['f1']:.4f}"
    )

    print("-" * 72)
    print("CHROMA (PITCH-CLASS) F1")
    print(f"chroma F1={report['chroma']['f1']:.4f}  pitch F1={baseline['f1']:.4f}")

    print("-" * 72)
    print("NOTE STATISTICS")

    reference_stats = report["reference_stats"]
    est_stats = report["est_stats"]

    print(
        f"reference  count={reference_stats['note_count']}  "
        f"span={reference_stats['span']:.2f}s  "
        f"onset[{reference_stats['first_onset']:.2f},{reference_stats['last_offset']:.2f}]  "
        f"pitch[{reference_stats['pitch_min']},{reference_stats['pitch_max']}]  "
        f"dur_med={reference_stats['duration_median']:.3f}s"
    )

    print(
        f"estimate   count={est_stats['note_count']}  "
        f"span={est_stats['span']:.2f}s  "
        f"onset[{est_stats['first_onset']:.2f},{est_stats['last_offset']:.2f}]  "
        f"pitch[{est_stats['pitch_min']},{est_stats['pitch_max']}]  "
        f"dur_med={est_stats['duration_median']:.3f}s"
    )

    print("-" * 72)
    print("RANKED SUSPECTS")

    if not report["suspects"]:
        print("no single condition produced an F1 jump above the threshold")

    for suspect in report["suspects"]:
        print(
            f"- {suspect['suspect']}  " f"(+{suspect['f1_gain']:.4f} F1)  " f"{suspect['detail']}"
        )

    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True)
    parser.add_argument("--est", required=True)
    parser.add_argument("--onset-tolerances", default="0.025,0.05,0.10,0.20,0.50")
    parser.add_argument("--octave-shifts", default="-24,-12,0,12,24")
    parser.add_argument("--shift-search-range", type=int, default=12)
    parser.add_argument("--pitch-tolerance", type=float, default=50.0)
    parser.add_argument("--default-onset-tolerance", type=float, default=0.05)
    parser.add_argument("--default-offset-ratio", type=float, default=0.2)
    parser.add_argument("--expected-f1", type=float, default=0.048951)
    parser.add_argument("--reproduction-tolerance", type=float, default=1e-3)
    parser.add_argument("--jump-threshold", type=float, default=0.10)
    parser.add_argument("--output", default="artifacts/diagnostics/day15_baseline_alignment.json")

    args = parser.parse_args()

    onset_tolerances = [float(item) for item in args.onset_tolerances.split(",")]
    octave_shifts = [int(item) for item in args.octave_shifts.split(",")]

    ref_intervals, ref_midi = load_notes(args.reference)
    est_intervals, est_midi = load_notes(args.est)

    baseline = evaluate(
        ref_intervals,
        ref_midi,
        est_intervals,
        est_midi,
        args.default_onset_tolerance,
        args.default_offset_ratio,
        args.pitch_tolerance,
    )

    diff = abs(baseline["f1"] - args.expected_f1)

    reproduction = {
        "expected_f1": args.expected_f1,
        "measured_f1": baseline["f1"],
        "diff": diff,
        "status": "MATCH" if diff <= args.reproduction_tolerance else "MISMATCH",
    }

    report = {
        "reference": args.reference,
        "est": args.est,
        "baseline": baseline,
        "reproduction": reproduction,
        "onset_sweep": onset_sweep(
            ref_intervals,
            ref_midi,
            est_intervals,
            est_midi,
            onset_tolerances,
            args.default_offset_ratio,
            args.pitch_tolerance,
        ),
        "offset_comparison": {
            "with_offset": evaluate(
                ref_intervals,
                ref_midi,
                est_intervals,
                est_midi,
                args.default_onset_tolerance,
                args.default_offset_ratio,
                args.pitch_tolerance,
            ),
            "without_offset": evaluate(
                ref_intervals,
                ref_midi,
                est_intervals,
                est_midi,
                args.default_onset_tolerance,
                None,
                args.pitch_tolerance,
            ),
        },
        "octave_sweep": pitch_shift_sweep(
            ref_intervals,
            ref_midi,
            est_intervals,
            est_midi,
            octave_shifts,
            args.default_onset_tolerance,
            args.default_offset_ratio,
            args.pitch_tolerance,
        ),
        "best_global_shift": best_global_shift(
            ref_intervals,
            ref_midi,
            est_intervals,
            est_midi,
            args.shift_search_range,
            args.default_onset_tolerance,
            args.default_offset_ratio,
            args.pitch_tolerance,
        ),
        "chroma": chroma_evaluate(
            ref_intervals,
            ref_midi,
            est_intervals,
            est_midi,
            args.default_onset_tolerance,
            args.default_offset_ratio,
        ),
        "reference_stats": note_stats(ref_intervals, ref_midi),
        "est_stats": note_stats(est_intervals, est_midi),
    }

    report["suspects"] = rank_suspects(report, args.jump_threshold)

    print_report(report)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"written: {output_path}")


if __name__ == "__main__":
    main()
