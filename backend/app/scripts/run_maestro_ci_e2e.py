from __future__ import annotations

import csv
import json
import subprocess
import time
from pathlib import Path

from app.pipeline.orchestrator import run_audio_to_analysis_pipeline


def _find_soundfont() -> Path:
    candidates = [
        Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"),
        Path("/usr/share/soundfonts/default.sf2"),
        Path("/usr/share/sounds/sf2/default-GM.sf2"),
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError("No FluidSynth soundfont found.")


def _render_midi_to_wav(midi_path: Path, wav_path: Path, soundfont: Path) -> None:
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    if wav_path.exists() and wav_path.stat().st_size > 0:
        return

    subprocess.run(
        [
            "fluidsynth",
            "-ni",
            str(soundfont),
            str(midi_path),
            "-F",
            str(wav_path),
            "-r",
            "44100",
        ],
        check=True,
    )


def main() -> int:
    selection_path = Path("data/maestro/v3.0.0/selection/ci_pieces.csv")
    midi_root = Path("data/maestro/v3.0.0/maestro-v3.0.0")
    rendered_dir = Path("data/maestro/v3.0.0/rendered/ci")
    report_path = Path("artifacts/metrics/day8_maestro_ci_e2e_report.json")

    soundfont = _find_soundfont()

    with selection_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    results = []

    for index, row in enumerate(rows, start=1):
        midi_path = midi_root / row["midi_filename"]
        wav_path = rendered_dir / (Path(row["midi_filename"]).stem + ".wav")
        job_id = f"day8-maestro-ci-{index:02d}-e2e"

        print(f"\n=== CI {index}/{len(rows)} ===")
        print("Composer:", row["canonical_composer"])
        print("Title:", row["canonical_title"])
        print("Duration:", row["duration"])
        print("MIDI:", midi_path)
        print("WAV:", wav_path)

        if not midi_path.exists():
            item = {
                "index": index,
                "status": "error",
                "error": f"MIDI not found: {midi_path}",
                "midi_path": str(midi_path),
            }
            print(json.dumps(item, indent=2, ensure_ascii=False))
            results.append(item)
            continue

        started = time.monotonic()

        try:
            _render_midi_to_wav(midi_path, wav_path, soundfont)

            result = run_audio_to_analysis_pipeline(
                source=str(wav_path),
                job_id=job_id,
                use_basic_pitch=True,
                selected_stem="other",
            )

            data = result.to_dict()
            transcription = data.get("transcription", {})
            notes = transcription.get("notes", [])

            item = {
                "index": index,
                "job_id": job_id,
                "status": data.get("status"),
                "composer": row["canonical_composer"],
                "title": row["canonical_title"],
                "duration": float(row["duration"]),
                "source_wav": str(wav_path),
                "final_audio_path": data.get("final_audio_path"),
                "midi_path": data.get("midi_path"),
                "detected_key": data.get("detected_key"),
                "hvs_score": data.get("hvs_score"),
                "transcription_method": transcription.get("transcription_method"),
                "note_count": transcription.get("note_count"),
                "first_note_confidence": notes[0].get("confidence") if notes else None,
                "error": data.get("error"),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }

        except Exception as exc:
            item = {
                "index": index,
                "job_id": job_id,
                "status": "error",
                "composer": row["canonical_composer"],
                "title": row["canonical_title"],
                "duration": float(row["duration"]),
                "source_wav": str(wav_path),
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }

        print(json.dumps(item, indent=2, ensure_ascii=False))
        results.append(item)

    report = {
        "status": "completed" if all(item["status"] == "completed" for item in results) else "error",
        "count": len(results),
        "results": results,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n=== REPORT ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
