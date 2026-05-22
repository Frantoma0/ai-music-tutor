from __future__ import annotations

from app.pipeline.correction_mask import build_correction_mask


def test_correction_mask_selects_low_confidence_notes_when_hvs_is_high():
    result = build_correction_mask(
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
                "pitch": 64,
                "pitch_name": "E4",
                "start": 1.0,
                "end": 2.0,
                "confidence": 0.9,
            },
        ],
        global_hvs_score=0.8,
        confidence_threshold=0.7,
        hvs_threshold=0.6,
    )

    data = result.to_dict()

    assert data["status"] == "completed"
    assert data["note_count"] == 2
    assert data["selected_count"] == 1

    assert data["candidates"][0]["selected"] is True
    assert data["candidates"][0]["reason"] == "low_confidence_high_hvs"

    assert data["candidates"][1]["selected"] is False
    assert data["candidates"][1]["reason"] == "confidence_above_threshold"


def test_correction_mask_does_not_select_low_confidence_when_hvs_is_low():
    result = build_correction_mask(
        [
            {
                "id": "n0",
                "pitch": 60,
                "pitch_name": "C4",
                "confidence": 0.5,
            }
        ],
        global_hvs_score=0.4,
        confidence_threshold=0.7,
        hvs_threshold=0.6,
    )

    data = result.to_dict()

    assert data["selected_count"] == 0
    assert data["candidates"][0]["selected"] is False
    assert data["candidates"][0]["reason"] == "hvs_below_threshold_or_missing"


def test_correction_mask_can_use_hvs_only_fallback_when_confidence_is_missing():
    result = build_correction_mask(
        [
            {
                "id": "n0",
                "pitch": 60,
                "pitch_name": "C4",
                "confidence": None,
            }
        ],
        global_hvs_score=0.8,
        confidence_threshold=0.7,
        hvs_threshold=0.6,
        allow_hvs_only_fallback=True,
    )

    data = result.to_dict()

    assert data["selected_count"] == 1
    assert data["candidates"][0]["selected"] is True
    assert data["candidates"][0]["reason"] == "confidence_missing_hvs_only_fallback"


def test_correction_mask_selects_when_hvs_equals_threshold():
    result = build_correction_mask(
        [
            {
                "id": "n0",
                "pitch": 61,
                "pitch_name": "C#4",
                "confidence": 0.5,
                "hvs_score": 0.6,
            }
        ],
        global_hvs_score=0.0,
        confidence_threshold=0.7,
        hvs_threshold=0.6,
    )

    data = result.to_dict()

    assert data["selected_count"] == 1
    assert data["candidates"][0]["selected"] is True
    assert data["candidates"][0]["reason"] == "low_confidence_high_hvs"
