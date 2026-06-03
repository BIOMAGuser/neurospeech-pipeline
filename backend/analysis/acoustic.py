"""
Acoustic feature extraction via Praat (parselmouth).

Computes voice-quality features used in dysarthria / Parkinson's research:
F0 statistics, jitter (local/rap/ppq5), shimmer (local/apq3/apq5/apq11),
HNR, and MFCC-13 (mean + std).

References: Shen et al. 2025, Sci Rep 15:11687 — uses parselmouth with
"To Pitch", "Get Jitter (local)", "Get Shimmer (local)" and harmonicity.
"""

import logging
from pathlib import Path

import numpy as np
import parselmouth
from parselmouth.praat import call
from pydub import AudioSegment

logger = logging.getLogger(__name__)

# Praat defaults — pitch range covers male and female adult speakers.
# Sex-specific overrides (M: 75-300 Hz, F: 100-600 Hz per Iyer et al. 2023)
# can be added in a follow-up.
PITCH_FLOOR_HZ = 75.0
PITCH_CEILING_HZ = 500.0
TARGET_SAMPLE_RATE = 16000

# Common args for jitter/shimmer Praat calls:
# (start_time, end_time, period_floor, period_ceiling, max_period_factor[, max_amplitude_factor])
_JITTER_ARGS = (0, 0, 0.0001, 0.02, 1.3)
_SHIMMER_ARGS = (0, 0, 0.0001, 0.02, 1.3, 1.6)


def _load_sound(audio_path: Path) -> parselmouth.Sound:
    """Load any audio file, downmix to mono, resample to 16 kHz, normalize."""
    audio = AudioSegment.from_file(str(audio_path))
    audio = audio.set_channels(1).set_frame_rate(TARGET_SAMPLE_RATE)
    samples = np.array(audio.get_array_of_samples(), dtype=np.float64)
    peak = float(np.max(np.abs(samples)))
    if peak > 0:
        samples /= peak
    return parselmouth.Sound(samples, sampling_frequency=TARGET_SAMPLE_RATE)


def _safe(fn, *args, **kwargs):
    """Run a feature extractor; return (value, None) or (None, error_str)."""
    try:
        val = fn(*args, **kwargs)
        if val is None:
            return None, "returned None"
        # Praat returns NaN for undefined values
        if isinstance(val, float) and (val != val):  # NaN check
            return None, "NaN"
        return float(val), None
    except Exception as e:
        return None, str(e)


def _f0_stats(sound: parselmouth.Sound) -> dict:
    out = {
        "f0_mean_hz": None,
        "f0_std_hz": None,
        "f0_min_hz": None,
        "f0_max_hz": None,
    }
    try:
        pitch = sound.to_pitch(pitch_floor=PITCH_FLOOR_HZ, pitch_ceiling=PITCH_CEILING_HZ)
        f0 = pitch.selected_array["frequency"]
        voiced = f0[f0 > 0]
        if len(voiced) == 0:
            return out
        out["f0_mean_hz"] = float(voiced.mean())
        out["f0_std_hz"] = float(voiced.std())
        out["f0_min_hz"] = float(voiced.min())
        out["f0_max_hz"] = float(voiced.max())
    except Exception as e:
        logger.warning("F0 extraction failed: %s", e)
    return out


def _jitter_shimmer(sound: parselmouth.Sound) -> dict:
    out = {
        "jitter_local": None,
        "jitter_rap": None,
        "jitter_ppq5": None,
        "shimmer_local": None,
        "shimmer_apq3": None,
        "shimmer_apq5": None,
        "shimmer_apq11": None,
    }
    try:
        pp = call(sound, "To PointProcess (periodic, cc)", PITCH_FLOOR_HZ, PITCH_CEILING_HZ)
    except Exception as e:
        logger.warning("PointProcess creation failed: %s", e)
        return out

    out["jitter_local"], _ = _safe(call, pp, "Get jitter (local)", *_JITTER_ARGS)
    out["jitter_rap"], _ = _safe(call, pp, "Get jitter (rap)", *_JITTER_ARGS)
    out["jitter_ppq5"], _ = _safe(call, pp, "Get jitter (ppq5)", *_JITTER_ARGS)

    out["shimmer_local"], _ = _safe(call, [sound, pp], "Get shimmer (local)", *_SHIMMER_ARGS)
    out["shimmer_apq3"], _ = _safe(call, [sound, pp], "Get shimmer (apq3)", *_SHIMMER_ARGS)
    out["shimmer_apq5"], _ = _safe(call, [sound, pp], "Get shimmer (apq5)", *_SHIMMER_ARGS)
    out["shimmer_apq11"], _ = _safe(call, [sound, pp], "Get shimmer (apq11)", *_SHIMMER_ARGS)
    return out


def _hnr_stats(sound: parselmouth.Sound) -> dict:
    out = {"hnr_mean_db": None, "hnr_std_db": None}
    try:
        harmonicity = call(sound, "To Harmonicity (cc)", 0.01, PITCH_FLOOR_HZ, 0.1, 1.0)
        values = np.asarray(harmonicity.values).flatten()
        # Praat marks undefined frames as -200 dB
        defined = values[values > -100]
        if len(defined) == 0:
            return out
        out["hnr_mean_db"] = float(defined.mean())
        out["hnr_std_db"] = float(defined.std())
    except Exception as e:
        logger.warning("HNR extraction failed: %s", e)
    return out


def _mfcc_stats(sound: parselmouth.Sound, n_coef: int = 13) -> dict:
    out = {}
    for i in range(1, n_coef + 1):
        out[f"mfcc_{i}_mean"] = None
        out[f"mfcc_{i}_std"] = None
    try:
        mfcc = sound.to_mfcc(number_of_coefficients=n_coef)
        # to_array() returns shape (n_coef + 1, n_frames); index 0 is the energy/DC term.
        arr = np.asarray(mfcc.to_array())
        if arr.ndim != 2 or arr.shape[1] == 0:
            return out
        for i in range(1, n_coef + 1):
            if i >= arr.shape[0]:
                break
            row = arr[i]
            out[f"mfcc_{i}_mean"] = float(row.mean())
            out[f"mfcc_{i}_std"] = float(row.std())
    except Exception as e:
        logger.warning("MFCC extraction failed: %s", e)
    return out


def compute_acoustic_features(audio_path: Path) -> dict:
    """
    Compute the full acoustic feature set from an audio file.

    Returns a flat dict with 39 keys. Any feature that fails extraction is
    set to None — extraction never raises on a per-feature basis.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    sound = _load_sound(audio_path)

    features: dict = {}
    features.update(_f0_stats(sound))
    features.update(_jitter_shimmer(sound))
    features.update(_hnr_stats(sound))
    features.update(_mfcc_stats(sound, n_coef=13))

    features["_audio_duration_s"] = float(sound.duration)
    return features
