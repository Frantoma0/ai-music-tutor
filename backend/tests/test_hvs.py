from __future__ import annotations

from pathlib import Path

import pretty_midi

from app.pipeline.hvs import compute_hvs_score_from_midi


def _write_midi(path: Path, pitches: list[int]) -> None:
    midi = pretty_midi.PrettyMIDI()
    piano = pretty_midi.Instrument(program=0, name="Test Piano")

    start = 0.0
    for midi_pitch in pitches:
        piano.notes.append(
            pretty_midi.Note(
                velocity=90,
                pitch=midi_pitch,
                start=start,
                end=start + 0.5,
            )
        )
        start += 0.5

    midi.instruments.append(piano)
    midi.write(str(path))


def test_hvs_scores_tonic_major_triad_high(tmp_path):
    midi_path = tmp_path / "c_major.mid"
    _write_midi(midi_path, [60, 64, 67, 72])

    score = compute_hvs_score_from_midi(midi_path, "C major")

    assert score == 1.0


def test_hvs_scores_chromatic_material_lower(tmp_path):
    midi_path = tmp_path / "chromatic.mid"
    _write_midi(midi_path, [60, 61, 62, 63])

    score = compute_hvs_score_from_midi(midi_path, "C major")

    assert 0.0 < score < 1.0


def test_hvs_returns_zero_for_empty_midi(tmp_path):
    midi_path = tmp_path / "empty.mid"

    midi = pretty_midi.PrettyMIDI()
    midi.write(str(midi_path))

    score = compute_hvs_score_from_midi(midi_path, "C major")

    assert score == 0.0
