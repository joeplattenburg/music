from typing import Iterable

import numpy as np


class Audio:
    """
    Class to define an audio signal. Attributes:
        sample_rate: int, sampling frequency in Hz
        duration: float, total duration [s] of audio
        waveform: the waveform of the audio signal
    """
    def __init__(self, sample_rate: int, waveform: Iterable[float]):
        self.sample_rate = sample_rate
        self.waveform = list(waveform)
        self.duration = len(self.waveform) / sample_rate

    def write_wav(self, path: str) -> None:
        """
        Write a wave file of the audio signal
        :param path: str, path to write to
        """
        import wave
        audio = np.array([self.waveform, self.waveform]).T
        # Convert to (little-endian) 16 bit integers.
        audio_norm = (audio * (2 ** 15 - 1)).astype("<h")
        with wave.open(path, "w") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(self.sample_rate)
            f.writeframes(audio_norm.tobytes())

    def __add__(self, other: 'Audio') -> 'Audio':
        assert self.sample_rate == other.sample_rate
        return Audio(
            sample_rate=self.sample_rate,
            waveform=self.waveform + other.waveform
        )
