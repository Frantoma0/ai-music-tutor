from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path


def read_gpu_memory_mb() -> int | None:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        values = [int(line.strip()) for line in completed.stdout.splitlines() if line.strip()]

        if not values:
            return None

        return max(values)

    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure peak GPU memory while running a command.")
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("command", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if not args.command:
        raise SystemExit("No command provided.")

    command = args.command

    if command and command[0] == "--":
        command = command[1:]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    samples: list[tuple[float, int | None]] = []

    started_at = time.time()
    process = subprocess.Popen(command)

    while process.poll() is None:
        elapsed = time.time() - started_at
        memory_mb = read_gpu_memory_mb()
        samples.append((elapsed, memory_mb))
        time.sleep(args.interval)

    return_code = process.wait()

    elapsed = time.time() - started_at
    memory_mb = read_gpu_memory_mb()
    samples.append((elapsed, memory_mb))

    valid_values = [value for _, value in samples if value is not None]
    peak_mb = max(valid_values) if valid_values else None

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "elapsed_seconds", "gpu_memory_used_mb"])

        for elapsed_seconds, value in samples:
            writer.writerow([args.label, round(elapsed_seconds, 3), value])

    print(
        {
            "label": args.label,
            "return_code": return_code,
            "duration_seconds": round(elapsed, 3),
            "peak_gpu_memory_used_mb": peak_mb,
            "samples_path": str(output_path),
        }
    )

    return return_code


if __name__ == "__main__":
    sys.exit(main())
