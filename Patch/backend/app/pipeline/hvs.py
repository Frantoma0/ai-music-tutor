from __future__ import annotations

from pathlib import Path

import pretty_midi
from music21 import pitch

_MAJOR_SCALE_INTERVALS = {0, 2, 4, 5, 7, 9, 11}
_MINOR_SCALE_INTERVALS = {0, 2, 3, 5, 7, 8, 10}

_MAJOR_TRIAD_INTERVALS = {0, 4, 7}
_MINOR_TRIAD_INTERVALS = {0, 3, 7}


def _parse_key_profile(detected_key: str) -> tuple[set[int], set[int]]:
    """
    Convert a music21-style key label like 'C major' or 'A minor'
    into scale and tonic-triad pitch-class sets.
    """
    parts = detected_key.strip().split()

    if len(parts) < 2:
        raise ValueError(f"Invalid detected key label: {detected_key}")

    mode = parts[-1].lower()
    tonic_name = " ".join(parts[:-1]).replace("-", "b")

    tonic_pc = pitch.Pitch(tonic_name).pitchClass

    if mode == "major":
        scale_intervals = _MAJOR_SCALE_INTERVALS
        triad_intervals = _MAJOR_TRIAD_INTERVALS
    elif mode == "minor":
        scale_intervals = _MINOR_SCALE_INTERVALS
        triad_intervals = _MINOR_TRIAD_INTERVALS
    else:
        raise ValueError(f"Unsupported key mode: {mode}")

    scale_pcs = {(tonic_pc + interval) % 12 for interval in scale_intervals}
    triad_pcs = {(tonic_pc + interval) % 12 for interval in triad_intervals}

    return scale_pcs, triad_pcs


def compute_hvs_score_from_midi(midi_path: str | Path, detected_key: str) -> float:
    """
    Compute a lightweight Harmony Validation Score.

    The score is intentionally simple for Day 3:
    - 70% of the score rewards notes that belong to the detected key scale.
    - 30% rewards notes that belong to the tonic triad.

    This gives us a deterministic 0.0-1.0 signal that can later be replaced
    with a richer harmonic/contextual metric.
    """
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    scale_pcs, triad_pcs = _parse_key_profile(detected_key)

    weighted_total = 0.0
    weighted_scale_hits = 0.0
    weighted_triad_hits = 0.0

    for instrument in midi.instruments:
        if instrument.is_drum:
            continue

        for note in instrument.notes:
            duration = max(0.0, float(note.end - note.start))

            if duration <= 0:
                continue

            pitch_class = note.pitch % 12

            weighted_total += duration

            if pitch_class in scale_pcs:
                weighted_scale_hits += duration

            if pitch_class in triad_pcs:
                weighted_triad_hits += duration

    if weighted_total == 0:
        return 0.0

    scale_score = weighted_scale_hits / weighted_total
    triad_score = weighted_triad_hits / weighted_total

    score = (0.7 * scale_score) + (0.3 * triad_score)

    return round(max(0.0, min(1.0, score)), 4)
