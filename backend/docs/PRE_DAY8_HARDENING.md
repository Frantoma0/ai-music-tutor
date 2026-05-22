
## H3b: MAESTRO CI 5-piece end-to-end hardening

Status: PASS

Five MAESTRO v3.0.0 MIDI files were selected from the test split and rendered to WAV with FluidSynth.

The full T1-T3 pipeline completed successfully for all 5 pieces.

```text
CI-01: completed | notes=548  | key=F major  | hvs=0.8065 | first_conf=0.722311 | elapsed=23.907s
CI-02: completed | notes=781  | key=D minor  | hvs=0.8187 | first_conf=0.701895 | elapsed=24.296s
CI-03: completed | notes=1120 | key=A minor  | hvs=0.7991 | first_conf=0.443076 | elapsed=27.705s
CI-04: completed | notes=1051 | key=A- major | hvs=0.8238 | first_conf=0.818045 | elapsed=29.383s
CI-05: completed | notes=1189 | key=F minor  | hvs=0.8281 | first_conf=0.60837  | elapsed=29.773s

Conclusion:

T1-T3 pipeline is no longer validated only on toy/synthetic 1-second inputs.
It has passed a 5-piece MAESTRO-derived CI hardening run with real MIDI-derived piano material.

Remaining limitation:

These are FluidSynth-rendered WAV files from MAESTRO MIDI, not original Disklavier WAV recordings.
Formal evaluation should still use original MAESTRO audio if storage permits.


## H5: Explicit GPU / sequential guard

Status: PASS

A process-local GPU sequential guard was added:

```text
backend/app/pipeline/resource_guard.py

The orchestrator now wraps GPU-heavy sections:

separate_sources
run_tracer_bullet

Purpose:

Prevent concurrent Demucs / Basic Pitch execution inside the same backend process.

Current limitation:

The guard is process-local and does not coordinate across multiple backend worker processes.
This is acceptable for the current Docker/dev backend setup, which runs the API as a single backend process.

Validation:

test_resource_guard.py verifies that concurrent threads are serialized.
The full test suite remains green.

