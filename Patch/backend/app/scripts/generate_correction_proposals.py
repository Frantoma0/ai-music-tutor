from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.pipeline.correction_proposals import build_correction_proposals_from_mask


def generate_correction_proposals(
    *,
    mask_path: str | Path,
    output: str | Path,
    max_proposals: int | None = None,
) -> dict:
    mask_path = Path(mask_path)
    output_path = Path(output)

    mask_data = json.loads(mask_path.read_text(encoding="utf-8"))

    batch = build_correction_proposals_from_mask(
        mask_data,
        source_mask_path=str(mask_path),
        max_proposals=max_proposals,
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
        "mask_path": str(mask_path),
        "output": str(output_path),
        "candidate_count": data["candidate_count"],
        "selected_candidate_count": data["selected_candidate_count"],
        "proposal_count": data["proposal_count"],
        "error": data["error"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate safe correction proposals from a correction mask artifact."
    )
    parser.add_argument("--mask-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-proposals", type=int, default=None)

    args = parser.parse_args()

    result = generate_correction_proposals(
        mask_path=args.mask_path,
        output=args.output,
        max_proposals=args.max_proposals,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
