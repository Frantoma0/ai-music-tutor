from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

DEFAULT_SOLO_PIANO_THRESHOLD = 0.05


@dataclass
class SeparationQualityResult:
    input_wav: str
    selected_stem: str
    selected_stem_path: str | None
    decision: str
    recommended_audio_path: str | None
    likely_solo_piano: bool
    total_energy: float
    selected_stem_energy: float
    non_selected_energy: float
    non_selected_energy_ratio: float
    stem_energies: dict[str, float]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _read_audio_energy(path: str | Path) -> float:
    audio, _ = sf.read(str(path), always_2d=True)

    if audio.size == 0:
        return 0.0

    samples = audio.astype(np.float64)

    return float(np.mean(samples * samples))


def analyze_separation_quality(
    input_wav: str | Path,
    stems: dict[str, str],
    selected_stem: str = "other",
    solo_piano_threshold: float = DEFAULT_SOLO_PIANO_THRESHOLD,
) -> SeparationQualityResult:
    """
    Analyze Demucs stem energy distribution.

    If non-selected stems have very low energy compared to the total stem energy,
    the input is likely already solo piano / piano-dominant. In that case, the
    original normalized WAV can be preferred in a future optimized path.

    This is a lightweight heuristic, not a final MIR classifier.
    """
    input_wav = Path(input_wav)

    stem_energies = {
        stem_name: _read_audio_energy(stem_path)
        for stem_name, stem_path in stems.items()
        if Path(stem_path).exists()
    }

    selected_stem_path = stems.get(selected_stem)
    selected_stem_energy = stem_energies.get(selected_stem, 0.0)

    total_energy = float(sum(stem_energies.values()))
    non_selected_energy = max(0.0, total_energy - selected_stem_energy)

    if total_energy <= 0:
        return SeparationQualityResult(
            input_wav=str(input_wav),
            selected_stem=selected_stem,
            selected_stem_path=selected_stem_path,
            decision="use_selected_stem",
            recommended_audio_path=selected_stem_path,
            likely_solo_piano=False,
            total_energy=0.0,
            selected_stem_energy=selected_stem_energy,
            non_selected_energy=0.0,
            non_selected_energy_ratio=0.0,
            stem_energies=stem_energies,
            reason="Stem energy is zero or unavailable; using selected stem as safe fallback.",
        )

    non_selected_energy_ratio = non_selected_energy / total_energy
    likely_solo_piano = non_selected_energy_ratio <= solo_piano_threshold

    if likely_solo_piano:
        return SeparationQualityResult(
            input_wav=str(input_wav),
            selected_stem=selected_stem,
            selected_stem_path=selected_stem_path,
            decision="prefer_original_wav",
            recommended_audio_path=str(input_wav),
            likely_solo_piano=True,
            total_energy=round(total_energy, 8),
            selected_stem_energy=round(selected_stem_energy, 8),
            non_selected_energy=round(non_selected_energy, 8),
            non_selected_energy_ratio=round(non_selected_energy_ratio, 6),
            stem_energies={k: round(v, 8) for k, v in stem_energies.items()},
            reason=(
                "Non-selected stems have very low energy; input appears solo piano "
                "or piano-dominant, so future pipeline runs may skip separation."
            ),
        )

    return SeparationQualityResult(
        input_wav=str(input_wav),
        selected_stem=selected_stem,
        selected_stem_path=selected_stem_path,
        decision="use_selected_stem",
        recommended_audio_path=selected_stem_path,
        likely_solo_piano=False,
        total_energy=round(total_energy, 8),
        selected_stem_energy=round(selected_stem_energy, 8),
        non_selected_energy=round(non_selected_energy, 8),
        non_selected_energy_ratio=round(non_selected_energy_ratio, 6),
        stem_energies={k: round(v, 8) for k, v in stem_energies.items()},
        reason=(
            "Non-selected stems contain meaningful energy; input appears mixed, "
            "so the selected separated stem should be used."
        ),
    )
