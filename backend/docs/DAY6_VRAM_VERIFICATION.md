# Day 6 — VRAM Verification Report

## Context

Day 6 focuses on validating the source separation stage and the current end-to-end backend mini-pipeline under the project hardware constraint:

```text
GPU VRAM limit: 8 GB

The tested pipeline is:

source audio
→ extract_audio
→ normalized WAV
→ separate_sources with Demucs htdemucs
→ selected other.wav stem
→ Basic Pitch transcription
→ MIDI output
→ music21 key detection
→ HVS score
→ JSON result
Measurement Method

A lightweight VRAM monitoring helper was added:

backend/app/scripts/measure_vram.py

It runs a command and samples nvidia-smi during execution.

Measured values are written to CSV files under:

artifacts/metrics/

These CSV files are runtime artifacts and should not be committed unless explicitly needed.

Measurement 1 — Demucs htdemucs

Command measured:

demucs -n htdemucs -o data/stems/day6-vram-demucs data/processed/day4-api-extract/input.wav

Result:

label: demucs_htdemucs_day6
return_code: 0
duration_seconds: 15.734
peak_gpu_memory_used_mb: 2495

Interpretation:

Demucs htdemucs completed successfully.
Peak VRAM usage was approximately 2.5 GB.
This is well below the 8 GB VRAM project limit.
Measurement 2 — Full Audio-to-Analysis Pipeline

Command measured:

python app/scripts/run_day6_full_pipeline.py

Pipeline result:

extract_audio: completed
separate_sources: completed
run_tracer_bullet: completed
transcription_method: basic_pitch
detected_key: D major
hvs_score: 1.0
error: null

VRAM result:

label: full_audio_to_analysis_day6
return_code: 0
duration_seconds: 13.673
peak_gpu_memory_used_mb: 2387

Interpretation:

The complete current backend pipeline completed successfully.
Peak VRAM usage was approximately 2.4 GB.
This is well below the 8 GB VRAM project limit.
Pass/Fail Decision
Demucs VRAM peak: 2495 MB / 8192 MB → PASS
Full pipeline VRAM peak: 2387 MB / 8192 MB → PASS

The current implementation satisfies the VRAM constraint for the tested short smoke input.

Important Notes

The test input is a short 1-second synthetic WAV signal. Therefore, the measurements are valid as a smoke verification, but not yet as final performance evidence for longer music pieces.

Longer MAESTRO or real piano examples should be measured later to document realistic memory and latency behavior.

Basic Pitch emitted optional dependency warnings for CoreML, TFLite and TensorFlow. These warnings are not blocking because the Basic Pitch path completed successfully and produced MIDI output.

Current Decision

Demucs remains enabled in the mixed-audio pipeline.

For solo piano audio, a future optimization may skip source separation when the system detects that the input is already piano-only. This should be treated as an optimization, not a blocker.

Current Status
Day 6 VRAM smoke verification: PASS
Demucs peak VRAM: ~2.5 GB
Full pipeline peak VRAM: ~2.4 GB
8 GB limit: satisfied

