from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.pipeline.correction_validation import validate_correction_proposals


def validate_correction_proposals_file(
    *,
    proposals_path: str | Path,
    output: str | Path,
    midi_mutation_allowed: bool = False,
) -> dict:
    proposals_path = Path(proposals_path)
    output_path = Path(output)

    proposals_data = json.loads(proposals_path.read_text(encoding="utf-8"))

    batch = validate_correction_proposals(
        proposals_data,
        source_proposals_path=str(proposals_path),
        midi_mutation_allowed=midi_mutation_allowed,
    )

    data = batch.to_dict()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "status": data["status"],
        "job_id": data["job_id"],
        "proposals_path": str(proposals_path),
        "output": str(output_path),
        "proposal_count": data["proposal_count"],
        "approved_count": data["approved_count"],
        "rejected_count": data["rejected_count"],
        "midi_mutation_allowed": data["midi_mutation_allowed"],
        "error": data["error"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate correction proposals before any MIDI mutation.")
    parser.add_argument("--proposals-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--allow-midi-mutation",
        action="store_true",
        help="Marks the validation batch as allowing MIDI mutation after validation. Default is false.",
    )

    args = parser.parse_args()

    result = validate_correction_proposals_file(
        proposals_path=args.proposals_path,
        output=args.output,
        midi_mutation_allowed=args.allow_midi_mutation,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
