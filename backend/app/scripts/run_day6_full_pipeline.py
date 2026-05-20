from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf

from app.pipeline.orchestrator import run_audio_to_analysis_pipeline


Path("data/samples").mkdir(parents=True, exist_ok=True)

sample_rate = 16_000
duration = 1.0

t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
audio = 0.2 * np.sin(2 * np.pi * 440.0 * t)

source_path = "data/samples/day6_vram_full_pipeline_source.wav"
sf.write(source_path, audio, sample_rate)

result = run_audio_to_analysis_pipeline(
    source=source_path,
    job_id="day6-vram-full-pipeline",
    use_basic_pitch=True,
    selected_stem="other",
)

print(json.dumps(result.to_dict(), indent=2))

if result.status != "completed":
    raise SystemExit(1)
