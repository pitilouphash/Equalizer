"""
Audio spectrum processing utilities for UI visualizations.

The module exposes a small pipeline that accepts raw audio blocks
(`numpy.ndarray`), applies a window, computes an FFT, aggregates the
spectrum into logarithmic bands, normalizes the result in dBFS and
optionally smooths the output using an exponential moving average (EMA).
A simple frame limiter is provided to throttle UI redraws to a target FPS.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal, Sequence, Tuple

import numpy as np

WindowType = Literal["hann", "hamming"]


def apply_window(samples: np.ndarray, window: WindowType = "hann") -> np.ndarray:
    """Apply a Hann or Hamming window to the input samples.

    Parameters
    ----------
    samples:
        The mono audio block.
    window:
        The window type to apply ("hann" or "hamming").
    """

    if window not in ("hann", "hamming"):
        raise ValueError(f"Unsupported window '{window}'")

    window_fn = np.hanning if window == "hann" else np.hamming
    return samples * window_fn(samples.size)


def compute_fft(samples: np.ndarray, sample_rate: int) -> Tuple[np.ndarray, np.ndarray]:
    """Compute the single-sided FFT of the input samples.

    Returns
    -------
    freqs:
        Frequency bin centers in Hz.
    magnitudes:
        Magnitude spectrum (linear scale).
    """

    spectrum = np.fft.rfft(samples)
    magnitudes = np.abs(spectrum) / samples.size
    freqs = np.fft.rfftfreq(samples.size, 1 / sample_rate)
    return freqs, magnitudes


def _log_space_edges(fmin: float, fmax: float, bands_per_octave: int) -> np.ndarray:
    octaves = np.log2(fmax / fmin)
    steps = int(octaves * bands_per_octave)
    return fmin * np.power(2.0, np.arange(steps + 1) / bands_per_octave)


def aggregate_bands(
    freqs: np.ndarray,
    magnitudes: np.ndarray,
    sample_rate: int,
    fmin: float = 20.0,
    fmax: float | None = None,
    bands_per_octave: int = 3,
) -> Tuple[np.ndarray, np.ndarray]:
    """Aggregate FFT magnitudes into logarithmically spaced bands.

    Parameters
    ----------
    freqs:
        Frequency bin centers from :func:`numpy.fft.rfftfreq`.
    magnitudes:
        Linear magnitudes that align with `freqs`.
    sample_rate:
        Sampling rate of the original signal.
    fmin, fmax:
        Frequency bounds (Hz). `fmax` defaults to Nyquist.
    bands_per_octave:
        Number of bands per octave (3 produces ISO-style 1/3 octave bands).
    """

    nyquist = sample_rate / 2
    upper = nyquist if fmax is None else min(fmax, nyquist)
    edges = _log_space_edges(fmin, upper, bands_per_octave)

    band_levels: list[float] = []
    band_centers: list[float] = []
    for low, high in zip(edges[:-1], edges[1:]):
        mask = (freqs >= low) & (freqs < high)
        if not np.any(mask):
            band_levels.append(0.0)
        else:
            band_levels.append(float(np.mean(magnitudes[mask])))
        band_centers.append(np.sqrt(low * high))

    return np.array(band_centers), np.array(band_levels)


def to_dbfs(levels: np.ndarray, ref: float = 1.0) -> np.ndarray:
    """Convert linear magnitudes to dBFS with a small floor to avoid ``-inf``."""

    floor = np.finfo(float).tiny
    return 20 * np.log10(np.maximum(levels, floor) / ref)


def ema(previous: np.ndarray | None, current: np.ndarray, alpha: float) -> np.ndarray:
    """Apply an exponential moving average between two spectra."""

    if previous is None:
        return current
    return alpha * current + (1 - alpha) * previous


@dataclass
class FrameLimiter:
    """Utility to throttle updates to a target frames-per-second."""

    fps: float
    _last_time: float = field(default_factory=time.monotonic)

    def should_render(self) -> bool:
        interval = 1.0 / self.fps
        now = time.monotonic()
        if now - self._last_time >= interval:
            self._last_time = now
            return True
        return False


@dataclass
class VisualizerPipeline:
    """Process raw audio blocks into smoothed spectral band data."""

    sample_rate: int
    window: WindowType = "hann"
    fmin: float = 20.0
    fmax: float | None = None
    bands_per_octave: int = 3
    ema_alpha: float = 0.5
    _previous_bands: np.ndarray | None = None

    def process(self, samples: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
        """Run the full processing pipeline for a single audio block."""

        block = np.asarray(samples, dtype=float)
        windowed = apply_window(block, self.window)
        freqs, magnitudes = compute_fft(windowed, self.sample_rate)
        centers, band_levels = aggregate_bands(
            freqs,
            magnitudes,
            sample_rate=self.sample_rate,
            fmin=self.fmin,
            fmax=self.fmax,
            bands_per_octave=self.bands_per_octave,
        )
        smoothed = ema(self._previous_bands, band_levels, self.ema_alpha)
        self._previous_bands = smoothed
        return centers, to_dbfs(smoothed)
