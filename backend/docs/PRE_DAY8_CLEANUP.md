# Pre-Day-8 Cleanup Report

## Purpose

Before starting Day 8 T1-T3 pipeline integration, all known mini-tasks and leftovers from Days 6-7 were reviewed and either completed or explicitly deferred.

## Completed

### 1. VRAM documentation

VRAM smoke verification was documented in:

```text
backend/docs/ENVIRONMENT.md
cat > backend/docs/PRE_DAY8_CLEANUP.md <<'MD'
# Pre-Day-8 Cleanup Report

## Purpose

Before starting Day 8 T1-T3 pipeline integration, all known mini-tasks and leftovers from Days 6-7 were reviewed and either completed or explicitly deferred.

## Completed

### 1. VRAM documentation

VRAM smoke verification was documented in:

```text
backend/docs/ENVIRONMENT.md

Recorded values:

Demucs htdemucs peak: 2495 MB
Full audio-to-analysis pipeline peak: 2387 MB
8 GB VRAM limit: PASS
2. T2 5-input CI smoke

Added:

backend/app/scripts/run_t2_ci_smoke.py

Purpose:

Run separate_sources() on 5 CI inputs and write a report to:
artifacts/metrics/day6_t2_ci_smoke_report.json

If MAESTRO/FluidSynth WAV files are available, the script uses existing WAV files.
If fewer than 5 WAV files are available, it generates short synthetic CI smoke fixtures.

3. T3 data/midi compatibility mirror

Primary transcription artifacts remain under:

artifacts/transcription/{job_id}/

A compatibility mirror was added under:

data/midi/{job_id}/

containing:

output.mid
notes.json
result.json

This keeps the implementation aligned with the roadmap wording while preserving the artifact-based architecture.

Explicitly Deferred
Basic Pitch per-note confidence

Current T3 MVP returns:

confidence: null

Per-note confidence extraction is deferred until Basic Pitch note-level outputs are available in a stable way.

CP1 / CP2

Current T2 uses:

separation_quality heuristic
adaptive audio selection

SNR-based CP1 and explicit CP2 are deferred as SHOULD items.
They are not blockers before Day 8.

Ready for Day 8

Day 8 can start when:

pytest -q is green
T2 5-input smoke is completed
git status is clean

