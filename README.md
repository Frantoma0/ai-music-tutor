# DaiTune — AI Music Tutor

DaiTune turns any piano recording into an interactive lesson. Paste a YouTube
link or upload an MP3/WAV, and the pipeline separates the audio, transcribes it
to MIDI, analyzes the harmony and builds a playable lesson with a falling-notes
view, sheet music and live feedback from a microphone or a MIDI keyboard.

Everything runs locally: FastAPI + SQLite on the backend, React on the
frontend, and an optional local LLM (Ollama) used only inside strictly bounded
agents.

## Features

- **Ingestion pipeline** — yt-dlp / file upload, Demucs source separation,
  Basic Pitch transcription with tunable thresholds, key detection and
  harmonic analysis (per-note HVS scores).
- **Bounded correction agent** — a local LLM proposes pitch corrections for a
  small set of suspicious notes; a deterministic validator checks every
  proposal and a full trace (`agent_trace.json`) is stored. The raw
  transcription is never silently overwritten.
- **Lesson player** — falling-notes waterfall, grand-staff sheet view and a
  mixed mode; Wait mode, A–B loop, metronome, count-in, tempo control and a
  three-star results screen.
- **Live practice** — microphone pitch detection (autocorrelation with
  first-peak selection) or Web MIDI; hit/miss/wrong scoring with octave
  tolerance.
- **Note levels** — Raw / Practice / Beginner. The cleanup passes remove
  transcription artifacts (dust, harmonic ghosts, sustained overtones,
  out-of-key noise) while a skyline guard protects the melody and the bass.
- **My piano** — pick an exact key range, a preset size (88/76/61/49/44/37/32)
  or a concrete keyboard model (Yamaha, Casio, Roland, Kawai, Korg, M-Audio);
  songs are transposed and folded to fit the instrument.
- **Practice Coach agent** — turns recorded weak spots into a plan: which
  sections to loop, at what tempo, with which hand. Deterministic core, LLM
  only rewrites the tip texts, full trace in `coach_trace.json`.
- **Progress tracking** — every attempt is stored (SQLite); the library shows
  best stars, best accuracy and attempt counts, and lessons resume from the
  last position.
- **UI** — six themes with full-surface coverage, six block palettes,
  responsive layout down to phone widths, English and Bulgarian localization.

## Architecture

```
frontend/   React + Vite single-page app (player, library, settings)
backend/    FastAPI application
  app/pipeline/     audio ingestion, separation, transcription, harmony
  app/agent/        bounded transcription-correction and practice-coach agents
  app/mcp_tools/    tool registry (18 tools) exposed via /api/tools
  app/db/           SQLite schema, pipeline runs, progress, plans
  tests/            pytest suite
docs/       environment notes and development log
```

## Getting started

With Docker (recommended — includes Ollama for the optional LLM features):

```bash
docker compose up --build
```

Frontend: http://localhost:3000 · Backend API: http://localhost:8080

Manual setup:

```bash
# backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev
```

## Development

Backend:

```bash
cd backend
python -m pytest          # 165 tests
ruff check app tests      # lint
black app tests           # formatting
```

Frontend:

```bash
cd frontend
npm test                  # unit tests (playability filters, pitch detection)
npm run lint              # ESLint
npm run build             # production build
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DAITUNE_BP_ONSET_THRESHOLD` | `0.60` | Basic Pitch onset threshold (higher = fewer note starts) |
| `DAITUNE_BP_FRAME_THRESHOLD` | `0.40` | Frame threshold (higher = fewer weak sustains) |
| `DAITUNE_BP_MIN_NOTE_LENGTH_MS` | `110` | Minimum note length in milliseconds |
| `DAITUNE_BP_MIN_FREQUENCY_HZ` | `30` | Lower frequency bound for transcription |
| `DAITUNE_BP_MAX_FREQUENCY_HZ` | `4200` | Upper frequency bound for transcription |
| `DAITUNE_COACH_USE_LLM` | `1` | Set to `0` to run the practice coach fully deterministically |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Local LLM endpoint used by the agents |
| `OLLAMA_MODEL` | `qwen3:8b` | Model used for bounded agent enrichment |
