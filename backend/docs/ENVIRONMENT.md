# Environment and Hardware Verification

## Target Hardware

```text
Machine: ASUS ROG Zephyrus G16 GA605
GPU: NVIDIA RTX 4070 Laptop
VRAM limit: 8 GB
Backend runtime: Docker container
Python: 3.11
Day 6 VRAM Smoke Verification

Measured with:

backend/app/scripts/measure_vram.py
Demucs htdemucs
Command: demucs -n htdemucs
Input: short smoke WAV
Duration: 15.734 seconds
Peak GPU memory: 2495 MB
Status: PASS
Full audio-to-analysis pipeline
Pipeline:
extract_audio
→ separate_sources
→ separation_quality
→ adaptive audio selection
→ transcribe_audio / Basic Pitch
→ tracer analysis
→ key detection
→ HVS

Duration: 13.673 seconds
Peak GPU memory: 2387 MB
Status: PASS
Decision
8 GB VRAM limit: satisfied for current smoke inputs.
Demucs and Basic Pitch are safe to run sequentially.
No evidence of VRAM overlap in the current sequential pipeline.
Notes

These measurements are smoke verification numbers, not final benchmark numbers.

Longer MAESTRO or real piano recordings still need to be measured during baseline/evaluation phases.
