from __future__ import annotations

from app.pipeline.harmony_analysis import (
    analyze_notes_harmony,
    classify_note_hvs,
    merge_hvs_into_notes,
)


def test_classify_note_hvs_in_major_key():
    assert classify_note_hvs(60, detected_key="C major") == (
        0.0,
        "stable_chord_tone",
        "pitch_class_in_tonic_triad",
    )

    assert classify_note_hvs(62, detected_key="C major") == (
        0.3,
        "diatonic_non_chord_tone",
        "pitch_class_in_key_scale",
    )

    assert classify_note_hvs(61, detected_key="C major") == (
        0.6,
        "chromatic_neighbor",
        "pitch_class_one_semitone_from_scale",
    )


def test_classify_note_hvs_chromatic_neighbor_when_one_semitone_from_scale():
    score, label, reason = classify_note_hvs(66, detected_key="C major")

    assert score == 0.6
    assert label == "chromatic_neighbor"
    assert reason == "pitch_class_one_semitone_from_scale"


def test_analyze_notes_harmony_returns_per_note_scores():
    result = analyze_notes_harmony(
        [
            {
                "id": "n0",
                "pitch": 60,
                "pitch_name": "C4",
                "start": 0.0,
                "end": 1.0,
                "confidence": 0.5,
            },
            {
                "id": "n1",
                "pitch": 61,
                "pitch_name": "C#4",
                "start": 1.0,
                "end": 2.0,
                "confidence": 0.4,
            },
        ],
        detected_key="C major",
    )

    data = result.to_dict()

    assert data["status"] == "completed"
    assert data["detected_key"] == "C major"
    assert data["tonic"] == "C"
    assert data["mode"] == "major"
    assert data["note_count"] == 2

    assert data["notes"][0]["hvs_score"] == 0.0
    assert data["notes"][0]["hvs_label"] == "stable_chord_tone"

    assert data["notes"][1]["hvs_score"] == 0.6
    assert data["notes"][1]["hvs_label"] == "chromatic_neighbor"


def test_merge_hvs_into_notes_preserves_original_note_fields():
    notes = [
        {
            "id": "n0",
            "pitch": 60,
            "pitch_name": "C4",
            "confidence": 0.5,
        }
    ]

    result = analyze_notes_harmony(
        notes,
        detected_key="C major",
    )

    merged = merge_hvs_into_notes(notes, result)

    assert merged[0]["id"] == "n0"
    assert merged[0]["pitch"] == 60
    assert merged[0]["confidence"] == 0.5
    assert merged[0]["hvs_score"] == 0.0
    assert merged[0]["hvs_label"] == "stable_chord_tone"
    assert merged[0]["hvs_reason"] == "pitch_class_in_tonic_triad"
