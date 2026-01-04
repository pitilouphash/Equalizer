# Equalizer visualizer utilities

This repository contains a small Python module to convert captured audio blocks
into smoothed spectral band values that can be rendered as bars or gradients in
an overlay UI.

## Features
- Hann/Hamming windowing to reduce spectral leakage before FFT processing.
- Single-sided FFT with numpy to extract magnitude spectra.
- Logarithmic (1/3-octave by default) band aggregation and dBFS normalization.
- Exponential moving average smoothing to stabilize the UI.
- Frame limiter helper to throttle redraw rate for overlays.

## Usage
```python
from visualizer import VisualizerPipeline, FrameLimiter

pipeline = VisualizerPipeline(sample_rate=48000, bands_per_octave=3, ema_alpha=0.35)
limiter = FrameLimiter(fps=60)

# Inside your audio callback or render loop
audio_block = ...  # 1-D numpy array of float samples
if limiter.should_render():
    band_centers, band_levels_db = pipeline.process(audio_block)
    # draw bars/gradients using band_centers and band_levels_db
```

## Tests
Run the unit suite with:
```bash
python -m unittest
```
