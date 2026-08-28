import numpy as np

from music import audio


def test_audio_add() -> None:
    t = np.linspace(0, 1, 100)
    sample_rate = 100
    x1 = audio.Audio(sample_rate=sample_rate, waveform=np.sin(t))
    x2 = audio.Audio(sample_rate=sample_rate, waveform=np.sin(2 * t))
    x3 = x1 + x2
    x4 = x1 @ x2
    assert x3.duration == 1.0
    assert x4.duration == 2.0
    assert max(x3.waveform) > max(x1.waveform)
    assert max(x4.waveform) == max(max(x1.waveform), max(x2.waveform))