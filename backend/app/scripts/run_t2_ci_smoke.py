from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from app.pipeline.source_separation import separate_sources


def _write_synthetic_wav(path: Path, frequency: float, sample_rate: int = 44_100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    duration_seconds = 1.0
    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
    )

    audio = 0.18 * np.sin(2 * np.pi * frequency * t)
    sf.write(path, audio, sample_rate)


def _find_existing_wavs() -> list[Path]:
    search_roots = [
        Path("data/maestro/ci_wavs"),
        Path("data/maestro"),
        Path("data/samples"),
    ]

    wavs: list[Path] = []

    for root in search_roots:
        if root.exists():
            wavs.extend(sorted(root.rglob("*.wav")))

    return wavs


def _ensure_five_inputs() -> list[Path]:
    existing = _find_existing_wavs()

    selected: list[Path] = []

    for path in existing:
        if path.is_file() and path.stat().st_size > 0:
            selected.append(path)
        if len(selected) >= 5:
            return selected[:5]

    fixture_dir = Path("data/samples/ci_t2_smoke")
    frequencies = [220.0, 261.63, 329.63, 392.0, 440.0]

    for index, frequency in enumerate(frequencies, start=1):
        path = fixture_dir / f"ci_t2_smoke_{index:02d}.wav"
        if not path.exists():
            _write_synthetic_wav(path, frequency=frequency)
        selected.append(path)

    return selected[:5]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run T2 source separation smoke on 5 CI inputs.")
    parser.add_argument("--output-dir", default="data/stems")
    parser.add_argument("--job-prefix", default="day6-t2-ci-smoke")
    parser.add_argument("--report", default="artifacts/metrics/day6_t2_ci_smoke_report.json")
    args = parser.parse_args()

    inputs = _ensure_five_inputs()

    results = []

    for index, wav_path in enumerate(inputs, start=1):
        job_id = f"{args.job_prefix}-{index:02d}"

        result = separate_sources(
            wav_path=wav_path,
            output_dir=args.output_dir,
            job_id=job_id,
            selected_stem="other",
        )

        data = result.to_dict()
        data["source_index"] = index
        data["source_path"] = str(wav_path)
        results.append(data)

    report = {
        "status": (
            "completed" if all(item["status"] == "completed" for item in results) else "error"
        ),
        "count": len(results),
        "results": results,
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
