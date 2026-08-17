import numpy as np

from music import audio


def test_audio_add() -> None:
    t = np.linspace(0, 1, 100)
    sample_rate = 100
    x1 = audio.Audio(sample_rate=sample_rate, waveform=np.sin(t))
    x2 = audio.Audio(sample_rate=sample_rate, waveform=np.sin(2 * t))
    x3 = x1 + x2
    assert x3.duration == 2.0