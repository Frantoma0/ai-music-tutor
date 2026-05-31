# Devlog — 2026-05-31 — Lesson API + UI Integration

## Summary

Today’s work connected the AI Music Tutor frontend to a real backend lesson contract. The project now has an end-to-end vertical slice where a persisted lesson in SQLite is exposed through FastAPI and consumed by the React waterfall piano UI.

## Completed

### Backend

- Added a UI-facing lesson REST contract.
- Added `LessonResponse`, `LessonMeta`, `LessonNote`, and `LessonVersions` schemas.
- Implemented lesson preparation logic that assembles:
  - transcription notes,
  - HVS labels and scores,
  - correction mask membership,
  - hand assignment using a C4 split heuristic,
  - correction status placeholders.
- Added `GET /api/lessons/{job_id}`.
- Added `GET /api/lessons/{job_id}/midi/raw`.
- Added corrected MIDI placeholder endpoint returning 404 until corrected MIDI is available.
- Added startup database initialization.
- Added Vite dev CORS origins for frontend integration.
- Added a seeded demo lesson:
  - `demo-morning-light-lesson`
  - title: `Morning Light`
  - key: `C major`
  - tempo: `100 BPM`
  - time signature: `4/4`
  - notes: `8`
- Generated a real demo MIDI file for the raw MIDI endpoint.

### Frontend

- Added `src/api/lessonApi.js`.
- Replaced local-only `demoNotes` usage with backend lesson fetching.
- Kept `demoNotes` as a development fallback with explicit console warning.
- Connected the UI to `GET /api/lessons/demo-morning-light-lesson`.
- Updated title/subtitle to use backend lesson metadata.
- Added real playback progress in the top progress bar.
- Added AI summary chips:
  - review notes count,
  - unknown confidence count.
- Added real hand filtering:
  - Left,
  - Both,
  - Right.
- Updated confidence visualization:
  - backend `in_correction_mask` drives low-confidence/review styling,
  - `confidence: null` is treated as unknown confidence, not low confidence.
- Fixed waterfall/piano timing mismatch by introducing a shared musical time basis.
- Adjusted waterfall hit line so falling blocks visually align with piano key activation.
- Improved Symbols mode:
  - natural notes use compact note symbols,
  - sharp notes show a larger sharp sign,
  - symbols are drawn as canvas mini notation rather than generic text.

## Validation

Backend tests:

```text
147 passed, 3 skipped

Frontend production build:

vite build completed successfully

Manual checks:

Backend lesson endpoint returns LessonResponse.
Raw MIDI endpoint returns a valid MIDI file.
Frontend fetches backend lesson data successfully after CORS fix.
Waterfall blocks and piano key activation are visually synchronized.
Blocks / Sheet / Mix modes remain available.
Blank / Letters / Symbols display modes work.
Left / Both / Right hand filtering works.
Low confidence/review note visualization works from backend data.
Current Known Warnings
FastAPI on_event("startup") is deprecated and should later be migrated to lifespan.
Some legacy async DB tests are skipped because they are missing explicit async test handling.
Tone.js AudioContext warning appears before user gesture; this is expected browser behavior.
Favicon 404 is cosmetic.
Next Steps
Add GET /api/lessons to list saved lessons.
Add sidebar/drawer for lesson navigation.
Allow opening selected lessons from backend instead of hardcoded demo job id.
Connect real pipeline runs to prepare_lesson.
Add practice session persistence:
started/ended time,
progress,
mistakes,
statistics.
Add WebSocket progress for long-running upload/transcription/correction pipeline.
Replace the demo seed with real uploaded/performed lesson data.
Optionally migrate FastAPI startup initialization to lifespan.
