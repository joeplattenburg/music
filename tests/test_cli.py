import os
import subprocess

import pytest

PROJ_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..')


@pytest.mark.parametrize(
    'name', ['Gmaj7', 'C#m7b11/E', 'D']
)
@pytest.mark.parametrize(
    'args',
    [
        [], ['-n 3'], ['-f 5'], ['-r'], ['-i'], ['-p'], ['-g']
    ]
)
def test_guitar_positions_name(name: str, args: list[str]) -> None:
    result = subprocess.run(
        ['music-cli', 'guitar-positions', '--name', name, *args],
        capture_output=True)
    assert result.returncode == 0


@pytest.mark.parametrize(
    'notes', ['G1,B1,D2,F2', 'G1,B3,D2,F#2']
)
@pytest.mark.parametrize(
    'args',
    [
        [], ['-n 3'], ['-f 5'], ['-r'], ['-i'], ['-p'], ['-g']
    ]
)
def test_guitar_positions_notes(notes: str, args: list[str]) -> None:
    result = subprocess.run(
        ['music-cli', 'guitar-positions', '--notes', notes, *args],
        capture_output=True)
    assert result.returncode == 0


@pytest.mark.parametrize(
    'args',
    [
        ['--chords', 'Dm7', 'G7', 'CM7'],
        ['--chords', 'Dm7', 'G7', 'CM7', '--lower', 'C2', '--upper', 'C4']
    ]
)
def test_voice_leading(args: list[str]) -> None:
    result = subprocess.run(
        ['music-cli', 'voice-leading', *args],
        capture_output=True)
    assert result.returncode == 0
