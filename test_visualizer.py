import time
import unittest
import numpy as np

from visualizer import (
    FrameLimiter,
    VisualizerPipeline,
    aggregate_bands,
    apply_window,
    compute_fft,
    ema,
    to_dbfs,
)


class TestWindowing(unittest.TestCase):
    def test_hann_window_reduces_edges(self):
        block = np.ones(8)
        windowed = apply_window(block, "hann")
        self.assertLess(windowed[0], 0.1)
        self.assertAlmostEqual(windowed[4], windowed[5])


class TestFFT(unittest.TestCase):
    def test_fft_peak_frequency(self):
        sr = 48000
        t = np.arange(sr) / sr
        signal = np.sin(2 * np.pi * 1000 * t)
        freqs, mags = compute_fft(signal, sr)
        peak_index = np.argmax(mags)
        self.assertAlmostEqual(freqs[peak_index], 1000, delta=1.0)


class TestBandAggregation(unittest.TestCase):
    def test_log_bands(self):
        sr = 48000
        freqs = np.array([20, 40, 80, 160, 320, 640, 1280])
        mags = np.linspace(1, 7, len(freqs))
        centers, levels = aggregate_bands(freqs, mags, sample_rate=sr, fmin=20, bands_per_octave=1)
        self.assertEqual(len(centers), len(levels))
        self.assertTrue(np.all(np.diff(centers) > 0))
        self.assertGreater(levels[-1], levels[0])


class TestDbfs(unittest.TestCase):
    def test_dbfs_floor(self):
        levels = np.array([0.0, 0.5, 1.0])
        db = to_dbfs(levels)
        self.assertTrue(np.isfinite(db[0]))
        self.assertLess(db[1], db[2])


class TestEMA(unittest.TestCase):
    def test_first_sample_passthrough(self):
        current = np.array([1.0, 2.0])
        result = ema(None, current, 0.5)
        np.testing.assert_array_equal(result, current)

    def test_weighting(self):
        previous = np.array([0.0, 0.0])
        current = np.array([1.0, 2.0])
        result = ema(previous, current, 0.25)
        np.testing.assert_allclose(result, np.array([0.25, 0.5]))


class TestPipeline(unittest.TestCase):
    def test_pipeline_outputs_db(self):
        pipeline = VisualizerPipeline(sample_rate=48000, bands_per_octave=1)
        noise = np.random.randn(1024)
        centers, db = pipeline.process(noise)
        self.assertEqual(len(centers), len(db))
        self.assertTrue(np.all(np.isfinite(db)))
        # Second call should smooth toward prior values
        centers2, db2 = pipeline.process(noise * 0.5)
        self.assertEqual(centers.tolist(), centers2.tolist())
        self.assertTrue(np.all(db2 <= db + 1e-6))


class TestFrameLimiter(unittest.TestCase):
    def test_respects_interval(self):
        limiter = FrameLimiter(fps=30)
        self.assertTrue(limiter.should_render())
        # Immediately calling again should be false
        self.assertFalse(limiter.should_render())
        # After the interval passes, it should allow rendering
        time.sleep(1 / 30)
        self.assertTrue(limiter.should_render())


if __name__ == "__main__":
    unittest.main()
