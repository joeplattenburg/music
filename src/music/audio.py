import io
from typing import Iterable, Optional

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

    def write_wav(self, path: Optional[str] = None) -> Optional[bytes]:
        """
        Write a wave file of the audio signal
        :param path: str, path to write to
        """
        import wave
        audio = np.array([self.waveform, self.waveform]).T
        # Convert to (little-endian) 16 bit integers.
        audio_norm = (audio * (2 ** 15 - 1)).astype("<h")
        if not path:
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as f:
                f.setnchannels(2)
                f.setsampwidth(2)
                f.setframerate(self.sample_rate)
                f.writeframes(audio_norm.tobytes())
                buffer.seek(0)
                return buffer.read()
        else:
            with wave.open(path, "w") as f:
                f.setnchannels(2)
                f.setsampwidth(2)
                f.setframerate(self.sample_rate)
                f.writeframes(audio_norm.tobytes())

    def __add__(self, other: 'Audio') -> 'Audio':
        assert self.sample_rate == other.sample_rate
        assert len(self.waveform) == len(other.waveform)
        new = np.array(self.waveform) + np.array(other.waveform)
        if (scale_factor := 2 * np.max(np.abs(new))) > 0:
            new /= scale_factor
        return Audio(sample_rate=self.sample_rate, waveform=new)

    @staticmethod
    def sum(audios: list['Audio']) -> 'Audio':
        assert all(audios[0].sample_rate == a.sample_rate for a in audios)
        assert all(len(audios[0].waveform) == len(a.waveform) for a in audios)
        new = np.zeros(len(audios[0].waveform))
        for a in audios:
            new += a.waveform
        if (scale_factor := 2 * np.max(np.abs(new))) > 0:
            new /= scale_factor
        return Audio(sample_rate=audios[0].sample_rate, waveform=new)

    def concat(self, other: 'Audio') -> 'Audio':
        assert self.sample_rate == other.sample_rate
        return Audio(
            sample_rate=self.sample_rate,
            waveform=self.waveform + other.waveform
        )

    def __matmul__(self, other) -> 'Audio':
        return self.concat(other)
