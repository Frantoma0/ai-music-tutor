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


def load_events(path: str) -> list[NoteEvent]:
    midi = pretty_midi.PrettyMIDI(path)
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
    candidates = []

    for ref in ref_events:
        for est in est_events:
            onset_delta = abs(ref.start - est.start)

            if onset_delta > onset_tolerance:
                continue

            if require_pitch and ref.pitch != est.pitch:
                continue

            candidates.append((onset_delta, ref.index, est.index, ref, est))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))

    used_ref = set()
    used_est = set()
    matches = []

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True)
    parser.add_argument("--est", required=True)
    parser.add_argument("--notes-path", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--onset-tolerance", type=float, default=0.05)

    args = parser.parse_args()

    ref_events = load_events(args.reference)
    est_events = load_events(args.est)
    notes = json.loads(Path(args.notes_path).read_text(encoding="utf-8"))

    pitch_matches = greedy_match(
        ref_events,
        est_events,
        onset_tolerance=args.onset_tolerance,
        require_pitch=True,
    )

    matched_ref = {item["ref_index"] for item in pitch_matches}
    matched_est = {item["est_index"] for item in pitch_matches}

    unmatched_ref = [item for item in ref_events if item.index not in matched_ref]
    unmatched_est = [item for item in est_events if item.index not in matched_est]

    onset_matches = greedy_match(
        unmatched_ref,
        unmatched_est,
        onset_tolerance=args.onset_tolerance,
        require_pitch=False,
    )

    bucket_by_est: dict[int, str] = {}
    match_by_est: dict[int, dict[str, Any]] = {}

    for item in pitch_matches:
        bucket_by_est[item["est_index"]] = "already_correct_tp"
        match_by_est[item["est_index"]] = item

    for item in onset_matches:
        abs_delta = abs(int(item["pitch_delta"]))
        bucket = (
            "correctable_pitch_error_le_2"
            if 1 <= abs_delta <= 2
            else "uncorrectable_pitch_error_gt_2"
        )

        bucket_by_est[item["est_index"]] = bucket
        match_by_est[item["est_index"]] = item

    for est in est_events:
        bucket_by_est.setdefault(est.index, "spurious_or_timing_fp")

    rows = []

    for note, est in zip(notes, est_events, strict=False):
        match = match_by_est.get(est.index, {})

        rows.append(
            {
                "id": note["id"],
                "est_index": est.index,
                "bucket": bucket_by_est[est.index],
                "pitch": est.pitch,
                "pitch_name": note.get("pitch_name"),
                "start": est.start,
                "end": est.end,
                "duration": est.end - est.start,
                "confidence": note.get("confidence"),
                "ref_index": match.get("ref_index"),
                "ref_pitch": match.get("ref_pitch"),
                "ref_start": match.get("ref_start"),
                "onset_delta": match.get("onset_delta"),
                "pitch_delta": match.get("pitch_delta"),
            }
        )

    bucket_counts: dict[str, int] = {}

    for row in rows:
        bucket_counts[row["bucket"]] = bucket_counts.get(row["bucket"], 0) + 1

    report = {
        "status": "completed",
        "reference_note_count": len(ref_events),
        "estimated_note_count": len(est_events),
        "onset_tolerance": args.onset_tolerance,
        "bucket_counts": bucket_counts,
        "rows": rows,
    }

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(
        json.dumps(
            {
                "status": "completed",
                "bucket_counts": bucket_counts,
                "output_json": str(output_json),
                "output_csv": str(output_csv),
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
